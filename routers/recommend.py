"""Recommendation Router"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import base64
import logging

from services.optimized_search import (
    search_similar_with_optimization,
    search_nearby_quests,
    get_quest_places_by_category
)
from services.db import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


class RecommendRequest(BaseModel):
    user_id: str
    image: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius_km: float = 5.0
    limit: int = 5
    quest_only: bool = True


@router.post("/similar-places")
async def recommend_similar_places(request: RecommendRequest):
    """Image-based place recommendation with GPS filtering"""
    try:
        logger.info(f"Recommendation: user={request.user_id}, GPS=({request.latitude}, {request.longitude})")
        
        try:
            image_bytes = base64.b64decode(request.image)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid base64: {str(e)}")
        
        results = search_similar_with_optimization(
            image_bytes=image_bytes,
            latitude=request.latitude,
            longitude=request.longitude,
            radius_km=request.radius_km,
            match_threshold=0.65,
            match_count=request.limit,
            quest_only=request.quest_only
        )
        
        logger.info(f"Found {len(results)} recommendations")
        
        return {
            "success": True,
            "count": len(results),
            "recommendations": results,
            "filter": {
                "gps_enabled": request.latitude is not None,
                "radius_km": request.radius_km,
                "quest_only": request.quest_only
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Recommendation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/nearby-quests")
async def get_nearby_quests_route(
    latitude: float,
    longitude: float,
    radius_km: float = 5.0,
    limit: int = 10
):
    """Get nearby quests based on GPS"""
    try:
        quests = search_nearby_quests(
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            limit=limit
        )
        
        logger.info(f"Found {len(quests)} nearby quests")
        
        return {
            "success": True,
            "count": len(quests),
            "quests": quests
        }
    
    except Exception as e:
        logger.error(f"Nearby quests error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quests/category/{category}")
async def get_quests_by_category(
    category: str,
    limit: int = 20
):
    """Get quests by category"""
    try:
        places = get_quest_places_by_category(category, limit)
        
        logger.info(f"Found {len(places)} places in category: {category}")
        
        return {
            "success": True,
            "category": category,
            "count": len(places),
            "places": places
        }
    
    except Exception as e:
        logger.error(f"Category quests error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quests/{quest_id}")
async def get_quest_detail(quest_id: str):
    """Get quest detail with quizzes"""
    try:
        db = get_db()
        
        quest_result = db.table("quests").select("*").eq("id", quest_id).single().execute()
        
        if not quest_result.data:
            raise HTTPException(status_code=404, detail="Quest not found")
        
        quest = quest_result.data
        
        place = db.table("places").select("*").eq("id", quest["place_id"]).single().execute()
        quizzes_result = db.table("quest_quizzes").select("*").eq("quest_id", quest_id).execute()
        
        # Format quizzes to match frontend expectations
        quizzes = []
        for quiz in quizzes_result.data:
            quiz_obj = {
                "id": quiz.get("id"),
                "question": quiz.get("question"),
                "options": quiz.get("options"),  # Already JSONB array
                "correct_answer": quiz.get("correct_answer"),  # Already integer (0-3)
                "hint": quiz.get("hint"),
                "points": 60,  # Default points value expected by frontend
                "explanation": quiz.get("explanation", "")
            }
            quizzes.append(quiz_obj)
        
        logger.info(f"Retrieved quest detail: {quest_id} with {len(quizzes)} quizzes")
        
        return {
            "success": True,
            "quest": quest,
            "place": place.data if place.data else None,
            "quizzes": quizzes
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Quest detail error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quests/{quest_id}/submit")
async def submit_quiz_answer(
    quest_id: str,
    user_id: str,
    quiz_id: str,
    answer: int
):
    """Submit quiz answer"""
    try:
        db = get_db()
        
        quiz = db.table("quest_quizzes").select("*").eq("id", quiz_id).single().execute()
        
        if not quiz.data:
            raise HTTPException(status_code=404, detail="Quiz not found")
        
        is_correct = quiz.data["correct_answer"] == answer
        
        progress_data = {
            "user_id": user_id,
            "quest_id": quest_id,
            "quiz_attempts": 1,
            "quiz_correct": is_correct
        }
        
        if is_correct:
            progress_data["status"] = "completed"
            progress_data["completed_at"] = "NOW()"
        
        db.table("user_quest_progress").upsert(progress_data).execute()
        
        if is_correct:
            quest = db.table("quests").select("completion_count").eq("id", quest_id).single().execute()
            current_count = quest.data.get("completion_count", 0)
            db.table("quests").update({"completion_count": current_count + 1}).eq("id", quest_id).execute()
        
        logger.info(f"Quiz submitted: correct={is_correct}")
        
        return {
            "success": True,
            "is_correct": is_correct,
            "explanation": quiz.data.get("explanation", "") if is_correct else None
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Quiz submit error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_recommendation_stats():
    """Get recommendation system statistics"""
    try:
        from services.pinecone_store import get_index_stats
        db = get_db()
        
        places_result = db.table("places").select("count", count="exact").execute()
        quests_result = db.table("quests").select("count", count="exact").execute()
        
        pinecone_stats = get_index_stats()
        
        logger.info("Retrieved recommendation stats")
        
        return {
            "total_places": places_result.count,
            "total_quests": quests_result.count,
            "total_vectors": pinecone_stats.get("total_vectors", 0),
            "vector_dimension": pinecone_stats.get("dimension", 512),
            "index_fullness": pinecone_stats.get("index_fullness", 0.0)
        }
    
    except Exception as e:
        logger.error(f"Stats error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
