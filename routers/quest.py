"""Quest Router"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from services.db import get_db
from datetime import datetime
import math
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


class QuestProgressRequest(BaseModel):
    user_id: str
    quest_id: int
    status: str  # 'in_progress', 'completed', 'failed'


class NearbyQuestRequest(BaseModel):
    lat: float
    lon: float
    radius_km: float = 1.0  # Default 1km radius


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


@router.get("/list")
async def get_all_quests():
    """Get all available quests with place information"""
    try:
        db = get_db()
        # Join with places table to get category and other place info
        result = db.table("quests").select("*, places(category, district, name, image_url, images)").execute()

        # Post-process to merge place data into quest data
        quests = []
        for quest in result.data:
            quest_data = dict(quest)
            place = quest.get("places")
            
            # Handle different Supabase JOIN response formats
            # Could be: None, empty dict {}, dict with data, or array
            if place:
                if isinstance(place, list) and len(place) > 0:
                    place = place[0]  # Take first place if array
                elif isinstance(place, dict) and len(place) > 0:
                    pass  # Already a dict
                else:
                    place = None
            
            # If place exists, merge place data into quest
            if place and isinstance(place, dict):
                # Merge place category and district if quest doesn't have them
                if not quest_data.get("category") and place.get("category"):
                    quest_data["category"] = place["category"]
                if not quest_data.get("district") and place.get("district"):
                    quest_data["district"] = place["district"]
                # Add place image info if available
                if place.get("image_url"):
                    quest_data["place_image_url"] = place["image_url"]
                if place.get("images"):
                    quest_data["place_images"] = place["images"]
            
            # Remove the nested places object
            quest_data.pop("places", None)
            quests.append(quest_data)

        logger.info(f"Retrieved {len(quests)} quests")
        return {"quests": quests}

    except Exception as e:
        logger.error(f"Error fetching quests: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching quests: {str(e)}")


@router.post("/nearby")
async def get_nearby_quests(request: NearbyQuestRequest):
    """
    Get quests near user's current location
    """
    try:
        db = get_db()
        # Join with places table to get category and other place info
        all_quests = db.table("quests").select("*, places(category, district, name, image_url, images)").execute()

        # Filter quests within radius
        nearby = []
        for quest in all_quests.data:
            distance = haversine_distance(
                request.lat, request.lon,
                quest['latitude'], quest['longitude']
            )
            if distance <= request.radius_km:
                # Add distance and rename fields for nearby endpoint
                quest_obj = dict(quest)
                
                # Merge place data if available
                place = quest_obj.get("places")
                # Handle different Supabase JOIN response formats
                if place:
                    if isinstance(place, list) and len(place) > 0:
                        place = place[0]  # Take first place if array
                    elif isinstance(place, dict) and len(place) > 0:
                        pass  # Already a dict
                    else:
                        place = None
                
                if place and isinstance(place, dict):
                    if not quest_obj.get("category") and place.get("category"):
                        quest_obj["category"] = place["category"]
                    if not quest_obj.get("district") and place.get("district"):
                        quest_obj["district"] = place["district"]
                    if place.get("image_url"):
                        quest_obj["place_image_url"] = place["image_url"]
                    if place.get("images"):
                        quest_obj["place_images"] = place["images"]
                
                quest_obj.pop("places", None)
                quest_obj['quest_id'] = quest['id']  # Frontend expects quest_id for nearby
                quest_obj['title'] = quest['name']   # Frontend expects title for nearby
                quest_obj['distance_km'] = round(distance, 2)
                nearby.append(quest_obj)

        # Sort by distance
        nearby.sort(key=lambda x: x['distance_km'])

        return {
            "quests": nearby,
            "count": len(nearby)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error finding nearby quests: {str(e)}")


@router.post("/progress")
async def update_quest_progress(request: QuestProgressRequest):
    """
    Update user's quest progress
    """
    try:
        db = get_db()

        # Check if quest exists
        quest = db.table("quests").select("*").eq("id", request.quest_id).execute()
        if not quest.data:
            raise HTTPException(status_code=404, detail="Quest not found")

        # Check if user_quest record exists
        existing = db.table("user_quests") \
            .select("*") \
            .eq("user_id", request.user_id) \
            .eq("quest_id", request.quest_id) \
            .execute()

        if existing.data:
            # Update existing record
            update_data = {"status": request.status}
            if request.status == "completed":
                update_data["completed_at"] = datetime.now().isoformat()

            db.table("user_quests") \
                .update(update_data) \
                .eq("user_id", request.user_id) \
                .eq("quest_id", request.quest_id) \
                .execute()
        else:
            # Create new record
            insert_data = {
                "user_id": request.user_id,
                "quest_id": request.quest_id,
                "status": request.status
            }
            if request.status == "completed":
                insert_data["completed_at"] = datetime.now().isoformat()

            db.table("user_quests").insert(insert_data).execute()

        # If completed, award points
        if request.status == "completed":
            reward_points = quest.data[0]['reward_point']
            db.table("points").insert({
                "user_id": request.user_id,
                "value": reward_points,
                "reason": f"Completed quest: {quest.data[0]['name']}"
            }).execute()

            return {
                "status": "success",
                "message": "Quest completed!",
                "points_earned": reward_points
            }

        return {
            "status": "success",
            "message": f"Quest status updated to {request.status}"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating quest progress: {str(e)}")


@router.get("/user/{user_id}")
async def get_user_quests(user_id: str, status: Optional[str] = None):
    """
    Get user's quests, optionally filtered by status
    """
    try:
        db = get_db()

        query = db.table("user_quests") \
            .select("*, quests(*)") \
            .eq("user_id", user_id)

        if status:
            query = query.eq("status", status)

        result = query.execute()

        return {
            "quests": result.data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching user quests: {str(e)}")


@router.get("/{quest_id}")
async def get_quest_detail(quest_id: int):
    """
    Get detailed information about a specific quest
    """
    try:
        db = get_db()
        result = db.table("quests").select("*").eq("id", quest_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Quest not found")

        quest = result.data[0]
        
        # place_id가 있으면 해당 place의 이미지 정보 조회
        if quest.get("place_id"):
            place_result = db.table("places").select("image_url, images").eq("id", quest["place_id"]).execute()
            if place_result.data:
                place = place_result.data[0]
                quest["image_url"] = place.get("image_url")
                quest["images"] = place.get("images")

        return quest

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching quest: {str(e)}")
