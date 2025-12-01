"""Recommendation Router"""

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from typing import Optional, List
import base64
import math
import logging
import numpy as np
from datetime import datetime, timedelta

from services.optimized_search import (
    search_similar_with_optimization,
    search_nearby_quests,
    get_quest_places_by_category
)
from services.db import get_db
from services.auth_deps import get_current_user_id

logger = logging.getLogger(__name__)
router = APIRouter()


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


def format_quest_response_with_place(
    quest: dict,
    place: Optional[dict] = None,
    user_latitude: Optional[float] = None,
    user_longitude: Optional[float] = None
) -> dict:
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
        if isinstance(place, list) and len(place) > 0:
            place = place[0]
        elif isinstance(place, dict) and len(place) > 0:
            pass
        else:
            place = None
        
        if place and isinstance(place, dict):
            if place.get("district"):
                result["district"] = place["district"]
            if place.get("image_url"):
                result["place_image_url"] = place["image_url"]
    
    if user_latitude is not None and user_longitude is not None and result.get("latitude") and result.get("longitude"):
        distance_km = haversine_distance(
            user_latitude, user_longitude,
            result["latitude"], result["longitude"]
        )
        result["distance_km"] = round(distance_km, 2)
    
    return result


class RecommendRequest(BaseModel):
    image: Optional[str] = None
    images: Optional[List[str]] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    start_latitude: Optional[float] = None
    start_longitude: Optional[float] = None
    radius_km: float = 5.0
    limit: int = 3
    quest_only: bool = True


@router.post("/similar-places")
async def recommend_similar_places(request: RecommendRequest, user_id: str = Depends(get_current_user_id)):
    try:
        logger.info(f"Recommendation: user={user_id}, GPS=({request.latitude}, {request.longitude})")
        
        image_list = []
        if request.images:
            if len(request.images) > 3:
                raise HTTPException(status_code=400, detail="Maximum 3 images allowed")
            image_list = request.images
        elif request.image:
            image_list = [request.image]
        else:
            raise HTTPException(status_code=400, detail="Either 'image' or 'images' must be provided")
        
        image_bytes_list = []
        for img_str in image_list:
            try:
                image_bytes = base64.b64decode(img_str)
                image_bytes_list.append(image_bytes)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid base64 image: {str(e)}")
        
        from services.embedding import generate_image_embedding
        
        embeddings = []
        for img_bytes in image_bytes_list:
            embedding = generate_image_embedding(img_bytes)
            if embedding:
                embeddings.append(embedding)
        
        if not embeddings:
            raise HTTPException(status_code=400, detail="Failed to generate image embeddings")
        
        if len(embeddings) > 1:
            avg_embedding = np.mean(embeddings, axis=0).tolist()
            logger.info(f"Using average embedding from {len(embeddings)} images")
        else:
            avg_embedding = embeddings[0]
        
        match_threshold = 0.2
        
        from services.optimized_search import search_with_gps_filter
        results = search_with_gps_filter(
            embedding=avg_embedding,
            latitude=request.latitude,
            longitude=request.longitude,
            start_latitude=request.start_latitude,
            start_longitude=request.start_longitude,
            radius_km=request.radius_km,
            match_threshold=match_threshold,
            match_count=request.limit * 2,
            quest_only=request.quest_only
        )
        
        formatted_recommendations = []
        db = get_db()
        
        valid_place_ids = set()
        for result in results:
            place = result.get("place", {})
            place_id = place.get("id")
            
            if not place_id:
                continue
            
            place_check = db.table("places").select("id").eq("id", place_id).eq("is_active", True).limit(1).execute()
            if place_check.data and len(place_check.data) > 0:
                valid_place_ids.add(place_id)
            else:
                logger.warning(f"Place {place_id} not found in DB or inactive, skipping")
        
        logger.info(f"Valid places after DB verification: {len(valid_place_ids)}")
        
        for result in results:
            place = result.get("place", {})
            place_id = place.get("id")
            
            if not place_id or place_id not in valid_place_ids:
                continue
            
            quest_result = db.table("quests").select("*").eq("place_id", place_id).eq("is_active", True).limit(1).execute()

            logger.info(f"Place {place_id} ({place.get('name')}): Found {len(quest_result.data) if quest_result.data else 0} quests")

            recommendation_item = {
                "place_id": place_id,
                "similarity": result.get("similarity", 0.0),
                "place": place
            }

            if quest_result.data and len(quest_result.data) > 0:
                quest = quest_result.data[0]
                quest_id = quest.get("id")
                recommendation_item["quest_id"] = quest_id
                recommendation_item["name"] = quest.get("name") or place.get("name")
                recommendation_item["description"] = quest.get("description") or place.get("description")
                recommendation_item["category"] = quest.get("category") or place.get("category")
                recommendation_item["latitude"] = float(quest.get("latitude")) if quest.get("latitude") else None
                recommendation_item["longitude"] = float(quest.get("longitude")) if quest.get("longitude") else None
                recommendation_item["reward_point"] = quest.get("reward_point")

                logger.info(f"Matched: Place '{place.get('name')}' → Quest ID {quest_id} '{quest.get('name')}'")

                if quest.get("place_id") != place_id:
                    logger.warning(f"Mismatch! Quest {quest_id} has place_id={quest.get('place_id')}, but we searched for {place_id}")
                
                anchor_lat = request.start_latitude if request.start_latitude is not None else request.latitude
                anchor_lon = request.start_longitude if request.start_longitude is not None else request.longitude
                
                if anchor_lat and anchor_lon and recommendation_item.get("latitude") and recommendation_item.get("longitude"):
                    distance = haversine_distance(
                        anchor_lat, anchor_lon,
                        recommendation_item["latitude"], recommendation_item["longitude"]
                    )
                    recommendation_item["distance_km"] = round(distance, 2)
            else:
                recommendation_item["name"] = place.get("name")
                recommendation_item["description"] = place.get("description")
                recommendation_item["category"] = place.get("category")
                recommendation_item["latitude"] = float(place.get("latitude")) if place.get("latitude") else None
                recommendation_item["longitude"] = float(place.get("longitude")) if place.get("longitude") else None
                recommendation_item["reward_point"] = None
                
                anchor_lat = request.start_latitude if request.start_latitude is not None else request.latitude
                anchor_lon = request.start_longitude if request.start_longitude is not None else request.longitude
                
                if anchor_lat and anchor_lon and recommendation_item.get("latitude") and recommendation_item.get("longitude"):
                    distance = haversine_distance(
                        anchor_lat, anchor_lon,
                        recommendation_item["latitude"], recommendation_item["longitude"]
                    )
                    recommendation_item["distance_km"] = round(distance, 2)
            
            recommendation_item["district"] = place.get("district")
            recommendation_item["place_image_url"] = place.get("image_url")

            if request.quest_only and not recommendation_item.get("quest_id"):
                logger.info(f"Skipping {place.get('name')} - no quest found (quest_only=True)")
                continue

            formatted_recommendations.append(recommendation_item)
        
        logger.info(f"Found {len(formatted_recommendations)} recommendations")
        
        return {
            "success": True,
            "count": len(formatted_recommendations),
            "recommendations": formatted_recommendations,
            "filter": {
                "gps_enabled": request.latitude is not None,
                "start_location": {
                    "latitude": request.start_latitude,
                    "longitude": request.start_longitude
                } if request.start_latitude and request.start_longitude else None,
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
    try:
        logger.info(f"get_nearby_quests_route called with radius_km={radius_km}")
        db = get_db()
        
        quests_result = db.table("quests").select("*, places(*)").eq("is_active", True).execute()
        
        nearby_quests = []
        for quest_data in quests_result.data:
            quest = dict(quest_data)
            place = quest.get("places")
            
            if not quest.get("latitude") or not quest.get("longitude"):
                continue
            
            distance = haversine_distance(
                latitude, longitude,
                float(quest["latitude"]), float(quest["longitude"])
            )
            
            if distance <= radius_km:
                formatted_quest = format_quest_response_with_place(
                    quest=quest,
                    place=place,
                    user_latitude=latitude,
                    user_longitude=longitude
                )
                nearby_quests.append(formatted_quest)
        
        nearby_quests.sort(key=lambda x: x.get("distance_km", float('inf')))
        
        nearby_quests = nearby_quests[:limit]
        
        logger.info(f"Found {len(nearby_quests)} nearby quests within {radius_km}km radius")
        
        return {
            "success": True,
            "count": len(nearby_quests),
            "quests": nearby_quests
        }
    
    except Exception as e:
        logger.error(f"Nearby quests error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quests/category/{category}")
async def get_quests_by_category(
    category: str,
    limit: int = 20
):
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
async def get_quest_detail(quest_id: int):
    try:
        db = get_db()
        
        quest_result = db.table("quests").select("*").eq("id", quest_id).single().execute()
        
        if not quest_result.data:
            raise HTTPException(status_code=404, detail="Quest not found")
        
        quest = quest_result.data
        
        place = db.table("places").select("*").eq("id", quest["place_id"]).single().execute()
        quizzes_result = db.table("quest_quizzes").select("*").eq("quest_id", quest_id).execute()
        
        quizzes = []
        for quiz in quizzes_result.data:
            quiz_obj = {
                "id": quiz.get("id"),
                "question": quiz.get("question"),
                "options": quiz.get("options"),
                "correct_answer": quiz.get("correct_answer"),
                "hint": quiz.get("hint"),
                "points": 60,
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
    quest_id: int,
    quiz_id: int,
    answer: int,
    user_id: str = Depends(get_current_user_id)
):
    try:
        db = get_db()
        
        quiz = db.table("quest_quizzes").select("*").eq("id", quiz_id).single().execute()
        
        if not quiz.data:
            raise HTTPException(status_code=404, detail="Quiz not found")
        
        is_correct = quiz.data["correct_answer"] == answer
        
        existing_progress = db.table("user_quest_progress") \
            .select("*") \
            .eq("user_id", user_id) \
            .eq("quest_id", quest_id) \
            .limit(1) \
            .execute()
        
        progress_data = {
            "quiz_correct": is_correct
        }
        
        if is_correct:
            progress_data["status"] = "completed"
            progress_data["completed_at"] = datetime.now().isoformat()
        
        if existing_progress.data:
            attempts = (existing_progress.data[0].get("quiz_attempts", 0) or 0) + 1
            progress_data["quiz_attempts"] = attempts
            
            db.table("user_quest_progress") \
                .update(progress_data) \
                .eq("user_id", user_id) \
                .eq("quest_id", quest_id) \
                .execute()
        else:
            progress_data["user_id"] = user_id
            progress_data["quest_id"] = quest_id
            progress_data["quiz_attempts"] = 1
            
            db.table("user_quest_progress").insert(progress_data).execute()
        
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


@router.get("/quests/high-reward")
async def get_high_reward_quests(
    latitude: Optional[float] = Query(None, description="User's current latitude (for distance calculation)"),
    longitude: Optional[float] = Query(None, description="User's current longitude (for distance calculation)"),
    limit: int = Query(3, description="Result count"),
    min_reward_point: int = Query(100, description="Minimum reward point")
):
    try:
        db = get_db()
        
        query = db.table("quests").select("*, places(*)").eq("is_active", True).gte("reward_point", min_reward_point).order("reward_point", desc=True).limit(limit * 2)  # 더 많이 조회 후 필터링
        
        quests_result = query.execute()
        
        formatted_quests = []
        for quest_data in quests_result.data:
            quest = dict(quest_data)
            place = quest.get("places")
            
            formatted_quest = format_quest_response_with_place(
                quest=quest,
                place=place,
                user_latitude=latitude,
                user_longitude=longitude
            )
            formatted_quests.append(formatted_quest)
        
        formatted_quests.sort(key=lambda x: x.get("reward_point", 0), reverse=True)
        
        formatted_quests = formatted_quests[:limit]
        
        logger.info(f"Found {len(formatted_quests)} high reward quests")
        
        return {
            "success": True,
            "count": len(formatted_quests),
            "quests": formatted_quests
        }
    
    except Exception as e:
        logger.error(f"High reward quests error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quests/newest")
async def get_newest_quests(
    latitude: Optional[float] = Query(None, description="User's current latitude (for distance calculation)"),
    longitude: Optional[float] = Query(None, description="User's current longitude (for distance calculation)"),
    limit: int = Query(3, description="Result count"),
    days: int = Query(30, description="Recent N days")
):
    try:
        db = get_db()
        
        cutoff_date = datetime.now() - timedelta(days=days)
        cutoff_date_str = cutoff_date.isoformat()
        
        query = db.table("quests").select("*, places(*)").eq("is_active", True).gte("created_at", cutoff_date_str).order("created_at", desc=True).limit(limit * 2)  # 더 많이 조회 후 필터링
        
        quests_result = query.execute()
        
        formatted_quests = []
        for quest_data in quests_result.data:
            quest = dict(quest_data)
            place = quest.get("places")
            
            formatted_quest = format_quest_response_with_place(
                quest=quest,
                place=place,
                user_latitude=latitude,
                user_longitude=longitude
            )
            formatted_quests.append(formatted_quest)
        
        formatted_quests.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        formatted_quests = formatted_quests[:limit]
        
        logger.info(f"Found {len(formatted_quests)} newest quests")
        
        return {
            "success": True,
            "count": len(formatted_quests),
            "quests": formatted_quests
        }
    
    except Exception as e:
        logger.error(f"Newest quests error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_recommendation_stats():
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
