"""Quest Router"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
from services.db import get_db, ensure_user_exists, save_quest_quizzes
from services.auth_deps import get_current_user_id, get_current_user_id_optional
from services.ai import generate_quest_quizzes
from datetime import datetime
import math
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


def get_quest_with_place(db, quest_id: int) -> Dict[str, Any]:
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
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    start_latitude: Optional[float] = None
    start_longitude: Optional[float] = None


class QuestQuizAnswerRequest(BaseModel):
    answer: int
    is_last_quiz: bool = False


class NearbyQuestRequest(BaseModel):
    lat: float
    lon: float
    radius_km: float = 1.0
    query_text: Optional[str] = None


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


@router.get("/list")
async def get_all_quests(
    query: Optional[str] = None,
    category: Optional[str] = None,
    sort: str = "default",
    latitude: Optional[float] = None,
    longitude: Optional[float] = None
):
    try:
        db = get_db()
        
        rag_quest_ids = {}
        rag_scores = {}
        if query:
            try:
                from services.quest_rag import search_quests_by_rag_text
                from services.embedding import generate_text_embedding
                
                text_embedding = generate_text_embedding(query)
                if text_embedding:
                    rag_results = search_quests_by_rag_text(
                        text_embedding=text_embedding,
                        match_threshold=0.6,
                        match_count=100,
                        latitude=latitude,
                        longitude=longitude,
                        radius_km=None
                    )
                    
                    for rag_result in rag_results:
                        quest_id = rag_result.get("quest", {}).get("id")
                        if quest_id:
                            rag_quest_ids[quest_id] = True
                            rag_scores[quest_id] = rag_result.get("similarity", 0.0)
                    
                    logger.info(f"RAG search found {len(rag_quest_ids)} matching quests")
            except Exception as e:
                logger.warning(f"RAG search failed: {e}")
        
        query_builder = db.table("quests").select("*, places(category, district, name, address, image_url, images)")
        
        if category:
            query_builder = query_builder.eq("category", category)
        
        if query and rag_quest_ids:
            query_builder = query_builder.in_("id", list(rag_quest_ids.keys()))
        elif query and not rag_quest_ids:
            return {"quests": [], "count": 0}
        
        query_builder = query_builder.eq("is_active", True)
        result = query_builder.execute()

        quests = []
        for quest in result.data:
            quest_data = dict(quest)
            place = quest.get("places")
            
            if place:
                if isinstance(place, list) and len(place) > 0:
                    place = place[0]  # Take first place if array
                elif isinstance(place, dict) and len(place) > 0:
                    pass  # Already a dict
                else:
                    place = None
            
            if place and isinstance(place, dict):
                if not quest_data.get("category") and place.get("category"):
                    quest_data["category"] = place["category"]
                if not quest_data.get("district") and place.get("district"):
                    quest_data["district"] = place["district"]
                if place.get("address"):
                    quest_data["address"] = place["address"]
                if place.get("image_url"):
                    quest_data["place_image_url"] = place["image_url"]
                if place.get("images"):
                    quest_data["place_images"] = place["images"]
            
            quest_data.pop("places", None)
            
            if quest.get("id") in rag_scores:
                quest_data['rag_score'] = rag_scores[quest.get("id")]
            
            if latitude and longitude and quest.get("latitude") and quest.get("longitude"):
                distance = haversine_distance(
                    latitude, longitude,
                    quest['latitude'], quest['longitude']
                )
                quest_data['distance_km'] = round(distance, 2)
            
            quests.append(quest_data)
        
        if sort == "popularity":
            quests.sort(key=lambda x: x.get("completion_count", 0), reverse=True)
        elif sort == "distance" and latitude and longitude:
            quests.sort(key=lambda x: x.get("distance_km", float('inf')))
        elif query and rag_scores:
            quests.sort(key=lambda x: rag_scores.get(x.get("id"), 0.0), reverse=True)

        logger.info(f"Retrieved {len(quests)} quests")
        return {"quests": quests, "count": len(quests)}

    except Exception as e:
        logger.error(f"Error fetching quests: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching quests: {str(e)}")


@router.post("/nearby")
async def get_nearby_quests(request: NearbyQuestRequest):
    try:
        db = get_db()
        all_quests = db.table("quests").select("*, places(category, district, name, image_url, images)").execute()

        rag_quest_ids = {}
        rag_scores = {}
        if request.query_text:
            try:
                from services.quest_rag import search_quests_by_rag_text
                from services.embedding import generate_text_embedding
                
                text_embedding = generate_text_embedding(request.query_text)
                if text_embedding:
                    rag_results = search_quests_by_rag_text(
                        text_embedding=text_embedding,
                        match_threshold=0.6,
                        match_count=50,
                        latitude=request.lat,
                        longitude=request.lon,
                        radius_km=request.radius_km * 2
                    )
                    
                    for rag_result in rag_results:
                        quest_id = rag_result.get("quest", {}).get("id")
                        if quest_id:
                            rag_quest_ids[quest_id] = True
                            rag_scores[quest_id] = rag_result.get("similarity", 0.0)
                    
                    logger.info(f"RAG search found {len(rag_quest_ids)} matching quests")
            except Exception as e:
                logger.warning(f"RAG search failed: {e}")

        nearby = []
        for quest in all_quests.data:
            distance = haversine_distance(
                request.lat, request.lon,
                quest['latitude'], quest['longitude']
            )
            
            if request.query_text and quest['id'] not in rag_quest_ids:
                continue
            
            if distance <= request.radius_km:
                quest_obj = dict(quest)
                
                place = quest_obj.get("places")
                if place:
                    if isinstance(place, list) and len(place) > 0:
                        place = place[0]
                    elif isinstance(place, dict) and len(place) > 0:
                        pass
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
                quest_obj['quest_id'] = quest['id']
                quest_obj['title'] = quest['name']
                quest_obj['distance_km'] = round(distance, 2)
                
                if quest['id'] in rag_scores:
                    quest_obj['rag_score'] = rag_scores[quest['id']]
                    quest_obj['rag_match'] = True
                else:
                    quest_obj['rag_score'] = 0.0
                    quest_obj['rag_match'] = False
                
                nearby.append(quest_obj)

        if request.query_text:
            nearby.sort(key=lambda x: (
                x.get('rag_score', 0.0) * 0.6 +
                (1.0 / (x['distance_km'] + 0.1)) * 0.4
            ), reverse=True)
        else:
            nearby.sort(key=lambda x: x['distance_km'])

        return {
            "quests": nearby,
            "count": len(nearby)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error finding nearby quests: {str(e)}")


@router.post("/start")
async def start_quest(request: QuestStartRequest, user_id: str = Depends(get_current_user_id)):
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

        existing_progress = db.table("user_quest_progress") \
            .select("*") \
            .eq("user_id", user_id) \
            .eq("quest_id", request.quest_id) \
            .execute()
        
        if existing_progress.data:
            db.table("user_quest_progress") \
                .update({"status": status}) \
                .eq("user_id", user_id) \
                .eq("quest_id", request.quest_id) \
                .execute()
        else:
            db.table("user_quest_progress").insert({
                "user_id": user_id,
                "quest_id": request.quest_id,
                "status": status
            }).execute()

        if request.latitude and request.longitude:
            from services.location_tracking import log_location_data
            log_location_data(
                user_id=user_id,
                quest_id=request.quest_id,
                place_id=quest.get("place_id"),
                user_latitude=request.latitude,
                user_longitude=request.longitude,
                start_latitude=request.start_latitude,
                start_longitude=request.start_longitude,
                interest_type="quest_start",
                treasure_hunt_count=0
            )

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
    try:
        db = get_db()

        quest = db.table("quests").select("*").eq("id", request.quest_id).execute()
        if not quest.data:
            raise HTTPException(status_code=404, detail="Quest not found")

        existing = db.table("user_quests") \
            .select("*") \
            .eq("user_id", user_id) \
            .eq("quest_id", request.quest_id) \
            .execute()

        if existing.data:
            update_data = {"status": request.status}
            if request.status == "completed":
                update_data["completed_at"] = datetime.now().isoformat()

            db.table("user_quests") \
                .update(update_data) \
                .eq("user_id", user_id) \
                .eq("quest_id", request.quest_id) \
                .execute()
        else:
            insert_data = {
                "user_id": user_id,
                "quest_id": request.quest_id,
                "status": request.status
            }
            if request.status == "completed":
                insert_data["completed_at"] = datetime.now().isoformat()

            db.table("user_quests").insert(insert_data).execute()

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
    try:
        db = get_db()
        quest = get_quest_with_place(db, quest_id)

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

        if len(quizzes) == 0:
            logger.info(f"No quizzes found for quest {quest_id}, generating with AI...")
            
            place = quest.get("place", {})
            place_name = quest.get("name") or place.get("name", "")
            place_description = quest.get("description") or place.get("description")
            place_category = quest.get("category") or place.get("category")
            
            generated_quizzes = generate_quest_quizzes(
                place_name=place_name,
                place_description=place_description,
                place_category=place_category,
                language="en",
                count=5
            )
            
            if generated_quizzes:
                quiz_ids = save_quest_quizzes(quest_id, generated_quizzes)
                
                if quiz_ids:
                    saved_quizzes_result = db.table("quest_quizzes") \
                        .select("*") \
                        .eq("quest_id", quest_id) \
                        .order("id") \
                        .execute()
                    
                    quizzes = []
                    for quiz in saved_quizzes_result.data or []:
                        quizzes.append({
                            "id": quiz.get("id"),
                            "question": quiz.get("question"),
                            "options": quiz.get("options"),
                            "hint": quiz.get("hint"),
                            "explanation": quiz.get("explanation"),
                            "difficulty": quiz.get("difficulty", "easy")
                        })
                    
                    logger.info(f"Generated and saved {len(quizzes)} quizzes for quest {quest_id}")
                else:
                    logger.warning(f"Failed to save generated quizzes for quest {quest_id}")
            else:
                logger.warning(f"Failed to generate quizzes for quest {quest_id}")

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

        progress_result = db.table("user_quest_progress") \
            .select("*") \
            .eq("user_id", user_id) \
            .eq("quest_id", quest_id) \
            .limit(1) \
            .execute()

        current_score = 0
        quiz_attempts = 0
        correct_count = 0
        used_hint = False
        
        if progress_result.data:
            progress = progress_result.data[0]
            current_score = progress.get("score", 0) or 0
            quiz_attempts = progress.get("quiz_attempts", 0) or 0
            correct_count = progress.get("correct_count", 0) or 0
            used_hint = progress.get("used_hint", False) or False

        earned = 0
        retry_allowed = False
        
        if is_correct:
            if quiz_attempts == 0:
                earned = 20
            else:
                earned = 10
            correct_count += 1
        else:
            if quiz_attempts == 0:
                retry_allowed = True
                used_hint = True

        quiz_attempts += 1
        new_score = current_score + earned

        update_data = {
            "quiz_attempts": quiz_attempts,
            "quiz_correct": is_correct,
            "score": new_score,
            "correct_count": correct_count,
            "used_hint": used_hint,
        }

        quest_completed = request.is_last_quiz
        
        if quest_completed:
            update_data["status"] = "completed"
            update_data["completed_at"] = datetime.now().isoformat()
        else:
            update_data["status"] = "in_progress"

        if progress_result.data:
            db.table("user_quest_progress") \
                .update(update_data) \
                .eq("user_id", user_id) \
                .eq("quest_id", quest_id) \
                .execute()
        else:
            update_data["user_id"] = user_id
            update_data["quest_id"] = quest_id
            db.table("user_quest_progress").insert(update_data).execute()

        points_awarded = 0
        new_balance = None
        already_completed = False

        if quest_completed:
            quest_result = db.table("quests").select("reward_point, name").eq("id", quest_id).single().execute()
            quest_data = quest_result.data

            user_quest = db.table("user_quests") \
                .select("status") \
                .eq("user_id", user_id) \
                .eq("quest_id", quest_id) \
                .limit(1) \
                .execute()
            
            already_completed = bool(user_quest.data and user_quest.data[0].get("status") == "completed")

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

            points_awarded = new_score
            if points_awarded > 0:
                db.table("points").insert({
                    "user_id": user_id,
                    "value": points_awarded,
                    "reason": f"Quest completed: {quest_data.get('name', '')} ({points_awarded} points)"
                }).execute()

            balance_result = db.rpc("get_user_points", {"user_uuid": user_id}).execute()
            new_balance = balance_result.data if balance_result.data is not None else 0

        return {
            "success": True,
            "is_correct": is_correct,
            "earned": earned,
            "total_score": new_score,
            "retry_allowed": retry_allowed,
            "hint": quiz.get("hint") if retry_allowed else None,
            "completed": quest_completed,
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
