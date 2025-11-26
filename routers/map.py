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


# 카테고리 매핑 (프론트엔드 → DB)
# DB에 저장되는 카테고리는 영문 카테고리명 그대로 사용 (Attractions, History, Culture 등)
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
    """Calculate distance between two points using Haversine formula (returns km)"""
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
    """프론트엔드 카테고리를 DB 카테고리로 매핑"""
    db_categories = []
    for frontend_cat in frontend_categories:
        if frontend_cat in CATEGORY_MAPPING:
            db_categories.extend(CATEGORY_MAPPING[frontend_cat])
        else:
            # 매핑이 없으면 그대로 사용 (직접 매칭 시도)
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
    """퀘스트 응답 포맷팅"""
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
    
    # Place 정보 병합
    if place:
        if place.get("district"):
            result["district"] = place["district"]
        if place.get("image_url"):
            result["place_image_url"] = place["image_url"]
    
    # 거리 정보 추가
    if distance_km is not None:
        result["distance_km"] = round(distance_km, 2)
    
    return result


@router.post("/search")
async def map_search(request: MapSearchRequest):
    """
    장소명으로 퀘스트/장소 검색
    
    - query: 검색어 (장소명)
    - latitude, longitude: 사용자 현재 위치 (거리 계산용)
    - radius_km: 검색 반경 (기본: 50.0)
    - limit: 결과 개수 (기본: 20)
    """
    try:
        db = get_db()
        
        # 기본 쿼리: is_active = TRUE인 퀘스트만
        query = db.table("quests").select("*, places(*)").eq("is_active", True)
        
        # 검색어로 필터링 (quests.name, places.name, places.metadata->>'rag_text')
        # Supabase는 OR 조건이 제한적이므로, 여러 쿼리를 실행하거나 Python에서 필터링
        # 일단 모든 활성 퀘스트를 가져온 후 Python에서 필터링
        
        all_quests_result = query.execute()
        
        # 검색어로 필터링
        search_query_lower = request.query.lower()
        filtered_quests = []
        
        for quest_data in all_quests_result.data:
            quest = dict(quest_data)
            place = quest.get("places")
            
            # Place 데이터 정규화
            if place:
                if isinstance(place, list) and len(place) > 0:
                    place = place[0]
                elif isinstance(place, dict) and len(place) > 0:
                    pass
                else:
                    place = None
            
            # 검색어 매칭 확인
            matched = False
            
            # quests.name 검색
            if quest.get("name") and search_query_lower in quest.get("name", "").lower():
                matched = True
            
            # places.name 검색
            if not matched and place and place.get("name"):
                if search_query_lower in place.get("name", "").lower():
                    matched = True
            
            # places.metadata->>'rag_text' 검색
            if not matched and place and place.get("metadata"):
                metadata = place.get("metadata")
                if isinstance(metadata, dict):
                    rag_text = metadata.get("rag_text", "")
                else:
                    # JSONB가 dict가 아닌 경우 (문자열 등)
                    rag_text = str(metadata) if metadata else ""
                if rag_text and search_query_lower in rag_text.lower():
                    matched = True
            
            if matched:
                # 거리 계산
                distance_km = None
                if request.latitude and request.longitude and quest.get("latitude") and quest.get("longitude"):
                    distance_km = haversine_distance(
                        request.latitude, request.longitude,
                        float(quest["latitude"]), float(quest["longitude"])
                    )
                    
                    # 반경 필터링
                    if distance_km > request.radius_km:
                        continue
                
                filtered_quests.append({
                    "quest": quest,
                    "place": place,
                    "distance_km": distance_km
                })
        
        # 정렬: 거리 오름차순 (위도/경도 제공 시), 그 외는 reward_point 내림차순
        if request.latitude and request.longitude:
            filtered_quests.sort(key=lambda x: x["distance_km"] if x["distance_km"] is not None else float('inf'))
        else:
            filtered_quests.sort(key=lambda x: x["quest"].get("reward_point", 0), reverse=True)
        
        # Limit 적용
        filtered_quests = filtered_quests[:request.limit]
        
        # 응답 포맷팅
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
    """
    필터 조건으로 퀘스트/장소 검색
    
    - categories: 카테고리 필터 (빈 배열이면 전체)
    - districts: 자치구 필터 (빈 배열이면 전체)
    - sort_by: 정렬 기준 ("nearest", "rewarded", "newest")
    - latitude, longitude: 사용자 현재 위치
    - radius_km: 검색 반경 (기본: 50.0)
    - limit: 결과 개수 (기본: 20)
    """
    try:
        db = get_db()
        
        # 기본 쿼리: is_active = TRUE인 퀘스트만
        query = db.table("quests").select("*, places(*)").eq("is_active", True)
        
        # 프론트엔드 카테고리를 DB 카테고리로 매핑 (한 번만 실행)
        db_categories = None
        if request.categories and len(request.categories) > 0:
            db_categories = map_frontend_categories(request.categories)
        
        # 모든 활성 퀘스트 가져오기
        all_quests_result = query.execute()
        
        filtered_quests = []
        
        for quest_data in all_quests_result.data:
            quest = dict(quest_data)
            place = quest.get("places")
            
            # Place 데이터 정규화
            if place:
                if isinstance(place, list) and len(place) > 0:
                    place = place[0]
                elif isinstance(place, dict) and len(place) > 0:
                    pass
                else:
                    place = None
            
            # 카테고리 필터링
            if db_categories:
                quest_category = quest.get("category") or (place.get("category") if place else None)
                
                if not quest_category or quest_category not in db_categories:
                    # 카테고리 매핑에서 부분 매칭 시도
                    matched = False
                    for db_cat in db_categories:
                        if db_cat.lower() in (quest_category or "").lower() or (quest_category or "").lower() in db_cat.lower():
                            matched = True
                            break
                    if not matched:
                        continue
            
            # 자치구 필터링
            if request.districts and len(request.districts) > 0:
                place_district = place.get("district") if place else None
                if not place_district or place_district not in request.districts:
                    continue
            
            # 거리 계산 및 반경 필터링
            distance_km = None
            if request.latitude and request.longitude and quest.get("latitude") and quest.get("longitude"):
                distance_km = haversine_distance(
                    request.latitude, request.longitude,
                    float(quest["latitude"]), float(quest["longitude"])
                )
                
                # 반경 필터링
                if distance_km > request.radius_km:
                    continue
            
            filtered_quests.append({
                "quest": quest,
                "place": place,
                "distance_km": distance_km
            })
        
        # 정렬
        if request.sort_by == "nearest":
            if request.latitude and request.longitude:
                filtered_quests.sort(key=lambda x: x["distance_km"] if x["distance_km"] is not None else float('inf'))
            else:
                # 위치 정보가 없으면 reward_point 내림차순으로 대체
                filtered_quests.sort(key=lambda x: x["quest"].get("reward_point", 0), reverse=True)
        elif request.sort_by == "rewarded":
            filtered_quests.sort(key=lambda x: x["quest"].get("reward_point", 0), reverse=True)
        elif request.sort_by == "newest":
            filtered_quests.sort(key=lambda x: x["quest"].get("created_at", ""), reverse=True)
        else:
            # 기본값: reward_point 내림차순
            filtered_quests.sort(key=lambda x: x["quest"].get("reward_point", 0), reverse=True)
        
        # Limit 적용
        filtered_quests = filtered_quests[:request.limit]
        
        # 응답 포맷팅
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
    """
    선택한 퀘스트 루트의 총 거리 계산
    
    Args:
        quest_ids: 퀘스트 ID 목록 (순서대로)
        user_latitude: 사용자 현재 위도 (선택)
        user_longitude: 사용자 현재 경도 (선택)
    
    Returns:
        {
            "total_distance_km": float,
            "route": [
                {
                    "from": {"type": str, ...},
                    "to": {"type": str, ...},
                    "distance_km": float
                },
                ...
            ]
        }
    """
    try:
        db = get_db()
        
        # 퀘스트가 없으면 0 반환
        if not quest_ids or len(quest_ids) == 0:
            return {
                "total_distance_km": 0.0,
                "route": []
            }
        
        # 퀘스트 정보 조회 (순서대로)
        quests_result = db.table("quests").select("id, name, latitude, longitude").in_("id", quest_ids).execute()
        
        if not quests_result.data:
            return {
                "total_distance_km": 0.0,
                "route": []
            }
        
        # quest_ids 순서대로 정렬
        quest_dict = {quest["id"]: quest for quest in quests_result.data}
        ordered_quests = [quest_dict[qid] for qid in quest_ids if qid in quest_dict]
        
        if not ordered_quests:
            return {
                "total_distance_km": 0.0,
                "route": []
            }
        
        route = []
        total_distance = 0.0
        
        # 사용자 위치 → 첫 번째 퀘스트
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
        
        # 퀘스트 간 거리 계산
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
    quest_ids: Optional[List[int]] = Query(None, description="선택한 퀘스트 ID 목록 (walk 거리 계산용)"),
    user_latitude: Optional[float] = Query(None, description="사용자 현재 위도 (walk 거리 계산용)"),
    user_longitude: Optional[float] = Query(None, description="사용자 현재 경도 (walk 거리 계산용)"),
    user_id: str = Depends(get_current_user_id)
):
    """
    맵 헤더에 표시할 사용자 통계 조회
    
    - walk_distance_km: 선택한 퀘스트 루트의 총 거리
    - mint_points: 사용자 총 포인트
    """
    try:
        db = get_db()
        
        # 사용자 존재 확인
        user_check = db.table("users").select("id").eq("id", user_id).execute()
        if not user_check.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        # mint_points 계산 (기존 get_user_points RPC 사용)
        points_result = db.rpc("get_user_points", {"user_uuid": user_id}).execute()
        mint_points = points_result.data if points_result.data else 0
        
        # walk_distance 계산
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
    """
    선택한 퀘스트 루트의 총 거리 계산 (walk 거리만)
    """
    try:
        # 입력 검증
        if not request.quest_ids or len(request.quest_ids) == 0:
            raise HTTPException(status_code=400, detail="quest_ids cannot be empty")
        
        if request.user_latitude is None or request.user_longitude is None:
            raise HTTPException(status_code=400, detail="user_latitude and user_longitude are required")
        
        # 거리 계산
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
