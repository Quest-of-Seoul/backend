"""Map Search & Filter Router"""

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from typing import Optional, List
from services.db import get_db
from services.auth_deps import get_current_user_id
import math
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


CATEGORY_MAPPING = {
    "Attractions": ["Attractions"],
    "History": ["History"],
    "Culture": ["Culture"],
    "Nature": ["Nature"],
    "Food": ["Food"],
    "Drinks": ["Drinks"],
    "Shopping": ["Shopping"],
    "Activities": ["Activities"],
    "Events": ["Events"],
}


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def map_frontend_categories(frontend_categories: List[str]) -> List[str]:
    db_categories = []
    for frontend_cat in frontend_categories:
        if frontend_cat in CATEGORY_MAPPING:
            db_categories.extend(CATEGORY_MAPPING[frontend_cat])
        else:
            db_categories.append(frontend_cat)
    return db_categories


class MapSearchRequest(BaseModel):
    query: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius_km: float = 50.0
    limit: int = 20


class MapFilterRequest(BaseModel):
    categories: Optional[List[str]] = None
    districts: Optional[List[str]] = None
    sort_by: str = "nearest"  # "nearest", "rewarded", "newest"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius_km: float = 50.0
    limit: int = 20


class WalkDistanceRequest(BaseModel):
    quest_ids: List[int]
    user_latitude: float
    user_longitude: float


def format_quest_response(quest: dict, place: Optional[dict] = None, distance_km: Optional[float] = None) -> dict:
    result = {
        "id": quest.get("id"),
        "place_id": quest.get("place_id"),
        "name": quest.get("name"),
        "title": quest.get("title"),
        "description": quest.get("description"),
        "category": quest.get("category"),
        "latitude": float(quest.get("latitude")) if quest.get("latitude") else None,
        "longitude": float(quest.get("longitude")) if quest.get("longitude") else None,
        "reward_point": quest.get("reward_point"),
        "points": quest.get("points"),
        "difficulty": quest.get("difficulty"),
        "is_active": quest.get("is_active"),
        "completion_count": quest.get("completion_count"),
        "created_at": quest.get("created_at"),
    }
    
    if place:
        if place.get("district"):
            result["district"] = place["district"]
        if place.get("image_url"):
            result["place_image_url"] = place["image_url"]
    
    if distance_km is not None:
        result["distance_km"] = round(distance_km, 2)
    
    return result


@router.post("/search")
async def map_search(request: MapSearchRequest):
    try:
        db = get_db()
        
        query = db.table("quests").select("*, places(*)").eq("is_active", True)
        
        all_quests_result = query.execute()
        
        search_query_lower = request.query.lower()
        filtered_quests = []
        
        for quest_data in all_quests_result.data:
            quest = dict(quest_data)
            place = quest.get("places")
            
            if place:
                if isinstance(place, list) and len(place) > 0:
                    place = place[0]
                elif isinstance(place, dict) and len(place) > 0:
                    pass
                else:
                    place = None
            
            matched = False
            
            if quest.get("name") and search_query_lower in quest.get("name", "").lower():
                matched = True
            
            if not matched and place and place.get("name"):
                if search_query_lower in place.get("name", "").lower():
                    matched = True
            
            if not matched and place and place.get("metadata"):
                metadata = place.get("metadata")
                if isinstance(metadata, dict):
                    rag_text = metadata.get("rag_text", "")
                else:
                    rag_text = str(metadata) if metadata else ""
                if rag_text and search_query_lower in rag_text.lower():
                    matched = True
            
            if matched:
                distance_km = None
                if request.latitude and request.longitude and quest.get("latitude") and quest.get("longitude"):
                    distance_km = haversine_distance(
                        request.latitude, request.longitude,
                        float(quest["latitude"]), float(quest["longitude"])
                    )
                    
                    if distance_km > request.radius_km:
                        continue
                
                filtered_quests.append({
                    "quest": quest,
                    "place": place,
                    "distance_km": distance_km
                })
        
        if request.latitude and request.longitude:
            filtered_quests.sort(key=lambda x: x["distance_km"] if x["distance_km"] is not None else float('inf'))
        else:
            filtered_quests.sort(key=lambda x: x["quest"].get("reward_point", 0), reverse=True)
        
        filtered_quests = filtered_quests[:request.limit]
        
        quests = [
            format_quest_response(item["quest"], item["place"], item["distance_km"])
            for item in filtered_quests
        ]
        
        logger.info(f"Map search: query='{request.query}', found {len(quests)} quests")
        
        return {
            "success": True,
            "count": len(quests),
            "quests": quests
        }
        
    except Exception as e:
        logger.error(f"Error in map search: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error searching quests: {str(e)}")


@router.post("/filter")
async def map_filter(request: MapFilterRequest):
    try:
        db = get_db()
        
        query = db.table("quests").select("*, places(*)").eq("is_active", True)
        
        db_categories = None
        if request.categories and len(request.categories) > 0:
            db_categories = map_frontend_categories(request.categories)
        
        all_quests_result = query.execute()
        
        filtered_quests = []
        
        for quest_data in all_quests_result.data:
            quest = dict(quest_data)
            place = quest.get("places")
            
            if place:
                if isinstance(place, list) and len(place) > 0:
                    place = place[0]
                elif isinstance(place, dict) and len(place) > 0:
                    pass
                else:
                    place = None
            
            if db_categories:
                quest_category = quest.get("category") or (place.get("category") if place else None)
                
                if not quest_category or quest_category not in db_categories:
                    matched = False
                    for db_cat in db_categories:
                        if db_cat.lower() in (quest_category or "").lower() or (quest_category or "").lower() in db_cat.lower():
                            matched = True
                            break
                    if not matched:
                        continue
            
            if request.districts and len(request.districts) > 0:
                place_district = place.get("district") if place else None
                if not place_district or place_district not in request.districts:
                    continue
            
            distance_km = None
            if request.latitude and request.longitude and quest.get("latitude") and quest.get("longitude"):
                distance_km = haversine_distance(
                    request.latitude, request.longitude,
                    float(quest["latitude"]), float(quest["longitude"])
                )
                
                if distance_km > request.radius_km:
                    continue
            
            filtered_quests.append({
                "quest": quest,
                "place": place,
                "distance_km": distance_km
            })
        
        if request.sort_by == "nearest":
            if request.latitude and request.longitude:
                filtered_quests.sort(key=lambda x: x["distance_km"] if x["distance_km"] is not None else float('inf'))
            else:
                filtered_quests.sort(key=lambda x: x["quest"].get("reward_point", 0), reverse=True)
        elif request.sort_by == "rewarded":
            filtered_quests.sort(key=lambda x: x["quest"].get("reward_point", 0), reverse=True)
        elif request.sort_by == "newest":
            filtered_quests.sort(key=lambda x: x["quest"].get("created_at", ""), reverse=True)
        else:
            filtered_quests.sort(key=lambda x: x["quest"].get("reward_point", 0), reverse=True)
        
        filtered_quests = filtered_quests[:request.limit]
        
        quests = [
            format_quest_response(item["quest"], item["place"], item["distance_km"])
            for item in filtered_quests
        ]
        
        logger.info(f"Map filter: categories={request.categories}, districts={request.districts}, sort_by={request.sort_by}, found {len(quests)} quests")
        
        return {
            "success": True,
            "count": len(quests),
            "quests": quests,
            "filters_applied": {
                "categories": request.categories or [],
                "districts": request.districts or [],
                "sort_by": request.sort_by
            }
        }
        
    except Exception as e:
        logger.error(f"Error in map filter: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error filtering quests: {str(e)}")


def calculate_quest_route_distance(
    quest_ids: List[int],
    user_latitude: Optional[float] = None,
    user_longitude: Optional[float] = None
) -> dict:
    try:
        db = get_db()
        
        if not quest_ids or len(quest_ids) == 0:
            return {
                "total_distance_km": 0.0,
                "route": []
            }
        
        quests_result = db.table("quests").select("id, name, latitude, longitude").in_("id", quest_ids).execute()
        
        if not quests_result.data:
            return {
                "total_distance_km": 0.0,
                "route": []
            }
        
        quest_dict = {quest["id"]: quest for quest in quests_result.data}
        ordered_quests = [quest_dict[qid] for qid in quest_ids if qid in quest_dict]
        
        if not ordered_quests:
            return {
                "total_distance_km": 0.0,
                "route": []
            }
        
        route = []
        total_distance = 0.0
        
        if user_latitude is not None and user_longitude is not None:
            first_quest = ordered_quests[0]
            first_lat = float(first_quest["latitude"])
            first_lon = float(first_quest["longitude"])
            
            distance = haversine_distance(user_latitude, user_longitude, first_lat, first_lon)
            total_distance += distance
            
            route.append({
                "from": {
                    "type": "user_location",
                    "latitude": user_latitude,
                    "longitude": user_longitude
                },
                "to": {
                    "type": "quest",
                    "quest_id": first_quest["id"],
                    "name": first_quest["name"],
                    "latitude": first_lat,
                    "longitude": first_lon
                },
                "distance_km": round(distance, 2)
            })
        
        for i in range(len(ordered_quests) - 1):
            current_quest = ordered_quests[i]
            next_quest = ordered_quests[i + 1]
            
            current_lat = float(current_quest["latitude"])
            current_lon = float(current_quest["longitude"])
            next_lat = float(next_quest["latitude"])
            next_lon = float(next_quest["longitude"])
            
            distance = haversine_distance(current_lat, current_lon, next_lat, next_lon)
            total_distance += distance
            
            route.append({
                "from": {
                    "type": "quest",
                    "quest_id": current_quest["id"],
                    "name": current_quest["name"],
                    "latitude": current_lat,
                    "longitude": current_lon
                },
                "to": {
                    "type": "quest",
                    "quest_id": next_quest["id"],
                    "name": next_quest["name"],
                    "latitude": next_lat,
                    "longitude": next_lon
                },
                "distance_km": round(distance, 2)
            })
        
        return {
            "total_distance_km": round(total_distance, 2),
            "route": route
        }
    
    except Exception as e:
        logger.error(f"Error calculating quest route distance: {e}", exc_info=True)
        return {
            "total_distance_km": 0.0,
            "route": []
        }


@router.get("/stats")
async def get_map_stats(
    quest_ids: Optional[List[int]] = Query(None, description="Selected quest IDs for walk distance calculation"),
    user_latitude: Optional[float] = Query(None, description="User's current latitude (for walk distance calculation)"),
    user_longitude: Optional[float] = Query(None, description="User's current longitude (for walk distance calculation)"),
    user_id: str = Depends(get_current_user_id)
):
    try:
        db = get_db()
        
        user_check = db.table("users").select("id").eq("id", user_id).execute()
        if not user_check.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        points_result = db.rpc("get_user_points", {"user_uuid": user_id}).execute()
        mint_points = points_result.data if points_result.data else 0
        
        walk_distance_km = 0.0
        walk_calculation = None
        
        if quest_ids and len(quest_ids) > 0:
            route_result = calculate_quest_route_distance(
                quest_ids=quest_ids,
                user_latitude=user_latitude,
                user_longitude=user_longitude
            )
            walk_distance_km = route_result["total_distance_km"]
            
            walk_calculation = {
                "type": "selected_quests_route",
                "total_distance_km": walk_distance_km,
                "route": [
                    {
                        "from": "user_location" if route_item["from"]["type"] == "user_location" else f"quest_{route_item['from'].get('quest_id')}",
                        "to": f"quest_{route_item['to']['quest_id']}",
                        "distance_km": route_item["distance_km"]
                    }
                    for route_item in route_result["route"]
                ]
            }
        
        logger.info(f"Map stats for user {user_id}: walk={walk_distance_km}km, mint={mint_points}")
        
        response = {
            "success": True,
            "walk_distance_km": round(walk_distance_km, 1),
            "mint_points": mint_points
        }
        
        if walk_calculation:
            response["walk_calculation"] = walk_calculation
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting map stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching map stats: {str(e)}")


@router.post("/stats/walk-distance")
async def calculate_walk_distance(request: WalkDistanceRequest, user_id: str = Depends(get_current_user_id)):
    try:
        if not request.quest_ids or len(request.quest_ids) == 0:
            raise HTTPException(status_code=400, detail="quest_ids cannot be empty")
        
        if request.user_latitude is None or request.user_longitude is None:
            raise HTTPException(status_code=400, detail="user_latitude and user_longitude are required")
        
        route_result = calculate_quest_route_distance(
            quest_ids=request.quest_ids,
            user_latitude=request.user_latitude,
            user_longitude=request.user_longitude
        )
        
        logger.info(f"Walk distance calculated: {route_result['total_distance_km']}km for {len(request.quest_ids)} quests")
        
        return {
            "success": True,
            "total_distance_km": route_result["total_distance_km"],
            "route": route_result["route"]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating walk distance: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error calculating walk distance: {str(e)}")
