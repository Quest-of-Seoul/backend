"""Recommendation Router"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
import base64
import math
import logging
from datetime import datetime, timedelta

from services.optimized_search import (
    search_similar_with_optimization,
    search_nearby_quests,
    get_quest_places_by_category
)
from services.db import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


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


def format_quest_response_with_place(
    quest: dict,
    place: Optional[dict] = None,
    user_latitude: Optional[float] = None,
    user_longitude: Optional[float] = None
) -> dict:
    """퀘스트 응답 포맷팅 (Place 정보 포함)"""
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
    
    # 거리 계산
    if user_latitude is not None and user_longitude is not None and result.get("latitude") and result.get("longitude"):
        distance_km = haversine_distance(
            user_latitude, user_longitude,
            result["latitude"], result["longitude"]
        )
        result["distance_km"] = round(distance_km, 2)
    
    return result


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
        
        # 결과 포맷팅 (Quest 정보 포함)
        formatted_recommendations = []
        db = get_db()
        
        for result in results:
            place = result.get("place", {})
            place_id = place.get("id")
            
            if not place_id:
                continue
            
            # 해당 Place에 연결된 Quest 찾기
            quest_result = db.table("quests").select("*").eq("place_id", place_id).eq("is_active", True).limit(1).execute()
            
            recommendation_item = {
                "place_id": place_id,
                "similarity": result.get("similarity", 0.0),
                "place": place
            }
            
            # Quest 정보 추가
            if quest_result.data and len(quest_result.data) > 0:
                quest = quest_result.data[0]
                recommendation_item["quest_id"] = quest.get("id")
                recommendation_item["name"] = quest.get("name") or place.get("name")
                recommendation_item["description"] = quest.get("description") or place.get("description")
                recommendation_item["category"] = quest.get("category") or place.get("category")
                recommendation_item["latitude"] = float(quest.get("latitude")) if quest.get("latitude") else None
                recommendation_item["longitude"] = float(quest.get("longitude")) if quest.get("longitude") else None
                recommendation_item["reward_point"] = quest.get("reward_point")
                
                # 거리 계산
                if request.latitude and request.longitude and recommendation_item.get("latitude") and recommendation_item.get("longitude"):
                    distance = haversine_distance(
                        request.latitude, request.longitude,
                        recommendation_item["latitude"], recommendation_item["longitude"]
                    )
                    recommendation_item["distance_km"] = round(distance, 2)
            else:
                # Quest가 없으면 Place 정보만 사용
                recommendation_item["name"] = place.get("name")
                recommendation_item["description"] = place.get("description")
                recommendation_item["category"] = place.get("category")
                recommendation_item["latitude"] = float(place.get("latitude")) if place.get("latitude") else None
                recommendation_item["longitude"] = float(place.get("longitude")) if place.get("longitude") else None
                recommendation_item["reward_point"] = None
                
                if request.latitude and request.longitude and recommendation_item.get("latitude") and recommendation_item.get("longitude"):
                    distance = haversine_distance(
                        request.latitude, request.longitude,
                        recommendation_item["latitude"], recommendation_item["longitude"]
                    )
                    recommendation_item["distance_km"] = round(distance, 2)
            
            # Place 정보에서 추가 필드
            recommendation_item["district"] = place.get("district")
            recommendation_item["place_image_url"] = place.get("image_url")
            
            formatted_recommendations.append(recommendation_item)
        
        logger.info(f"Found {len(formatted_recommendations)} recommendations")
        
        return {
            "success": True,
            "count": len(formatted_recommendations),
            "recommendations": formatted_recommendations,
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
        db = get_db()
        
        # 퀘스트와 Place 정보를 함께 조회
        quests_result = db.table("quests").select("*, places(*)").eq("is_active", True).execute()
        
        # 거리 계산 및 필터링
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
        
        # 거리순 정렬
        nearby_quests.sort(key=lambda x: x.get("distance_km", float('inf')))
        
        # Limit 적용
        nearby_quests = nearby_quests[:limit]
        
        logger.info(f"Found {len(nearby_quests)} nearby quests")
        
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


@router.get("/quests/high-reward")
async def get_high_reward_quests(
    latitude: Optional[float] = Query(None, description="사용자 현재 위도 (거리 계산용)"),
    longitude: Optional[float] = Query(None, description="사용자 현재 경도 (거리 계산용)"),
    limit: int = Query(3, description="결과 개수"),
    min_reward_point: int = Query(100, description="최소 포인트")
):
    """포인트가 높은 퀘스트 추천 (Wanna Get Some Mint? 섹션용)"""
    try:
        db = get_db()
        
        # 포인트가 높은 퀘스트 조회
        query = db.table("quests").select("*, places(*)").eq("is_active", True).gte("reward_point", min_reward_point).order("reward_point", desc=True).limit(limit * 2)  # 더 많이 조회 후 필터링
        
        quests_result = query.execute()
        
        # 포맷팅 및 거리 계산
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
        
        # reward_point 내림차순 정렬 (이미 정렬되어 있지만 확실히)
        formatted_quests.sort(key=lambda x: x.get("reward_point", 0), reverse=True)
        
        # Limit 적용
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
    latitude: Optional[float] = Query(None, description="사용자 현재 위도 (거리 계산용)"),
    longitude: Optional[float] = Query(None, description="사용자 현재 경도 (거리 계산용)"),
    limit: int = Query(3, description="결과 개수"),
    days: int = Query(30, description="최근 N일 이내")
):
    """최신 퀘스트 추천 (See What's New in Seoul 섹션용)"""
    try:
        db = get_db()
        
        # 최근 N일 이내 날짜 계산
        cutoff_date = datetime.now() - timedelta(days=days)
        cutoff_date_str = cutoff_date.isoformat()
        
        # 최신 퀘스트 조회
        query = db.table("quests").select("*, places(*)").eq("is_active", True).gte("created_at", cutoff_date_str).order("created_at", desc=True).limit(limit * 2)  # 더 많이 조회 후 필터링
        
        quests_result = query.execute()
        
        # 포맷팅 및 거리 계산
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
        
        # created_at 내림차순 정렬 (이미 정렬되어 있지만 확실히)
        formatted_quests.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        # Limit 적용
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
