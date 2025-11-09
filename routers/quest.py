"""
Quest router - Quest management endpoints
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from services.db import get_db
from datetime import datetime
import math

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
    """
    Calculate distance between two points using Haversine formula

    Returns distance in kilometers
    """
    R = 6371  # Earth's radius in km

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
    """
    Get all available quests
    """
    try:
        db = get_db()
        result = db.table("quests").select("*").execute()

        return {
            "quests": result.data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching quests: {str(e)}")


@router.post("/nearby")
async def get_nearby_quests(request: NearbyQuestRequest):
    """
    Get quests near user's current location
    """
    try:
        db = get_db()
        all_quests = db.table("quests").select("*").execute()

        # Filter quests within radius
        nearby = []
        for quest in all_quests.data:
            distance = haversine_distance(
                request.lat, request.lon,
                quest['lat'], quest['lon']
            )
            if distance <= request.radius_km:
                quest['distance_km'] = round(distance, 2)
                nearby.append(quest)

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

        return result.data[0]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching quest: {str(e)}")
