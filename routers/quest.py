"""Quest Router"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
from services.db import get_db, ensure_user_exists
from services.auth_deps import get_current_user_id, get_current_user_id_optional
from datetime import datetime
import math
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


def get_quest_with_place(db, quest_id: int) -> Dict[str, Any]:
    """Fetch quest and related place info."""
    quest_result = db.table("quests").select("*, places(*)").eq("id", quest_id).single().execute()
    if not quest_result.data:
        raise HTTPException(status_code=404, detail="Quest not found")

    quest = dict(quest_result.data)
    place = quest.pop("places", None)
    if isinstance(place, list) and place:
        place = place[0]

    if place:
        quest["place"] = place
    return quest


class QuestProgressRequest(BaseModel):
    quest_id: int
    status: str  # 'in_progress', 'completed', 'failed'


class QuestStartRequest(BaseModel):
    quest_id: int


class QuestQuizAnswerRequest(BaseModel):
    answer: int


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
        result = db.table("quests").select("*, places(category, district, name, address, image_url, images)").execute()

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
                # Add place address if available
                if place.get("address"):
                    quest_data["address"] = place["address"]
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


@router.post("/start")
async def start_quest(request: QuestStartRequest, user_id: str = Depends(get_current_user_id)):
    """
    Start or resume a quest for a user. Returns quest/place metadata for downstream quiz/chat usage.
    """
    try:
        db = get_db()
        quest = get_quest_with_place(db, request.quest_id)
        ensure_user_exists(user_id)

        existing = db.table("user_quests") \
            .select("*") \
            .eq("user_id", user_id) \
            .eq("quest_id", request.quest_id) \
            .execute()

        if existing.data:
            user_quest = existing.data[0]
            status = user_quest.get("status", "in_progress")
        else:
            insert_result = db.table("user_quests").insert({
                "user_id": user_id,
                "quest_id": request.quest_id,
                "status": "in_progress",
                "started_at": datetime.now().isoformat()
            }).execute()
            user_quest = insert_result.data[0] if insert_result.data else {
                "status": "in_progress"
            }
            status = "in_progress"

        # Mirror progress row for quiz tracking
        db.table("user_quest_progress").upsert({
            "user_id": user_id,
            "quest_id": request.quest_id,
            "status": status
        }).execute()

        place = quest.get("place")
        response = {
            "quest": quest,
            "place": place,
            "status": status,
            "place_id": quest.get("place_id"),
            "message": "Quest resumed" if existing.data else "Quest started"
        }
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting quest: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error starting quest: {str(e)}")


@router.post("/progress")
async def update_quest_progress(request: QuestProgressRequest, user_id: str = Depends(get_current_user_id)):
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
            .eq("user_id", user_id) \
            .eq("quest_id", request.quest_id) \
            .execute()

        if existing.data:
            # Update existing record
            update_data = {"status": request.status}
            if request.status == "completed":
                update_data["completed_at"] = datetime.now().isoformat()

            db.table("user_quests") \
                .update(update_data) \
                .eq("user_id", user_id) \
                .eq("quest_id", request.quest_id) \
                .execute()
        else:
            # Create new record
            insert_data = {
                "user_id": user_id,
                "quest_id": request.quest_id,
                "status": request.status
            }
            if request.status == "completed":
                insert_data["completed_at"] = datetime.now().isoformat()

            db.table("user_quests").insert(insert_data).execute()

        # If completed, award points (only once per quest)
        if request.status == "completed":
            already_completed = existing.data and existing.data[0].get("status") == "completed"
            if already_completed:
                return {
                    "status": "success",
                    "message": "Quest already completed"
                }
            reward_points = quest.data[0]['reward_point']
            db.table("points").insert({
                "user_id": user_id,
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


@router.get("/user")
async def get_user_quests(status: Optional[str] = None, user_id: str = Depends(get_current_user_id)):
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
async def get_quest_detail(quest_id: int, user_id: Optional[str] = Depends(get_current_user_id_optional)):
    """
    Get detailed information about a specific quest
    """
    try:
        db = get_db()
        quest = get_quest_with_place(db, quest_id)

        # place_id가 있으면 이미지 정보는 이미 포함되어 있음(get_quest_with_place)
        response = {"quest": quest}

        if user_id:
            user_quest = db.table("user_quests") \
                .select("status, started_at, completed_at") \
                .eq("user_id", user_id) \
                .eq("quest_id", quest_id) \
                .limit(1) \
                .execute()

            user_points = db.rpc("get_user_points", {"user_uuid": user_id}).execute()

            response["user_status"] = user_quest.data[0] if user_quest.data else None
            response["user_points"] = user_points.data if user_points.data is not None else 0

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching quest: {str(e)}")


@router.get("/{quest_id}/quizzes")
async def get_quest_quizzes(quest_id: int):
    """
    Retrieve quizzes tied to a quest/place so that the frontend can start testing immediately after quest start.
    """
    try:
        db = get_db()
        quest = get_quest_with_place(db, quest_id)

        quizzes_result = db.table("quest_quizzes") \
            .select("*") \
            .eq("quest_id", quest_id) \
            .order("id") \
            .execute()

        quizzes = []
        for quiz in quizzes_result.data or []:
            quizzes.append({
                "id": quiz.get("id"),
                "question": quiz.get("question"),
                "options": quiz.get("options"),
                "hint": quiz.get("hint"),
                "explanation": quiz.get("explanation"),
                "difficulty": quiz.get("difficulty", "easy")
            })

        return {
            "quest": quest,
            "quizzes": quizzes,
            "count": len(quizzes)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching quest quizzes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching quizzes: {str(e)}")


@router.post("/{quest_id}/quizzes/{quiz_id}/submit")
async def submit_quest_quiz(quest_id: int, quiz_id: int, request: QuestQuizAnswerRequest, user_id: str = Depends(get_current_user_id)):
    """
    Submit quiz answer, update user quest status, and award points when the quiz tied to the quest is cleared.
    """
    try:
        db = get_db()
        ensure_user_exists(user_id)

        quiz_result = db.table("quest_quizzes") \
            .select("*") \
            .eq("id", quiz_id) \
            .eq("quest_id", quest_id) \
            .single() \
            .execute()

        if not quiz_result.data:
            raise HTTPException(status_code=404, detail="Quiz not found")

        quiz = quiz_result.data
        is_correct = quiz["correct_answer"] == request.answer

        # Update progress attempts
        progress_result = db.table("user_quest_progress") \
            .select("*") \
            .eq("user_id", user_id) \
            .eq("quest_id", quest_id) \
            .limit(1) \
            .execute()

        attempts = 1
        if progress_result.data:
            attempts = (progress_result.data[0].get("quiz_attempts", 0) or 0) + 1

        db.table("user_quest_progress").upsert({
            "user_id": user_id,
            "quest_id": quest_id,
            "quiz_attempts": attempts,
            "quiz_correct": is_correct,
            "status": "completed" if is_correct else "in_progress",
            "completed_at": datetime.now().isoformat() if is_correct else None
        }).execute()

        points_awarded = 0
        already_completed = False
        new_balance = None

        if is_correct:
            quest_result = db.table("quests").select("reward_point, name").eq("id", quest_id).single().execute()
            quest_data = quest_result.data

            user_quest = db.table("user_quests") \
                .select("status") \
                .eq("user_id", user_id) \
                .eq("quest_id", quest_id) \
                .limit(1) \
                .execute()

            already_completed = bool(user_quest.data and user_quest.data[0].get("status") == "completed")

            if already_completed:
                logger.info(f"User {user_id} already completed quest {quest_id}, skipping award.")
            else:
                timestamp = datetime.now().isoformat()
                if user_quest.data:
                    db.table("user_quests").update({
                        "status": "completed",
                        "completed_at": timestamp
                    }).eq("user_id", user_id).eq("quest_id", quest_id).execute()
                else:
                    db.table("user_quests").insert({
                        "user_id": user_id,
                        "quest_id": quest_id,
                        "status": "completed",
                        "started_at": timestamp,
                        "completed_at": timestamp
                    }).execute()

                points_awarded = quest_data.get("reward_point", 0) if quest_data else 0
                if points_awarded:
                    db.table("points").insert({
                        "user_id": user_id,
                        "value": points_awarded,
                        "reason": f"퀘스트 완료: {quest_data.get('name', '')}"
                    }).execute()

            balance_result = db.rpc("get_user_points", {"user_uuid": user_id}).execute()
            new_balance = balance_result.data if balance_result.data is not None else 0

        return {
            "success": True,
            "is_correct": is_correct,
            "points_awarded": points_awarded,
            "already_completed": already_completed,
            "new_balance": new_balance,
            "explanation": quiz.get("explanation") if is_correct else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting quiz: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error submitting quiz: {str(e)}")
