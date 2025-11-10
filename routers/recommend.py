"""
장소 추천 API
GPS + 벡터 검색 기반 최적화된 추천
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import base64

from services.optimized_search import (
    search_similar_with_optimization,
    search_nearby_quests,
    get_quest_places_by_category
)
from services.db import get_db

router = APIRouter()


class RecommendRequest(BaseModel):
    """장소 추천 요청"""
    user_id: str
    image: str  # base64
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius_km: float = 5.0
    limit: int = 5
    quest_only: bool = True  # 퀘스트 등록 장소만


@router.post("/similar-places")
async def recommend_similar_places(request: RecommendRequest):
    """
    이미지 기반 유사 장소 추천 (GPS 필터링 최적화)
    
    처리 흐름:
    1. GPS 반경 내 장소 필터링
    2. 퀘스트 등록 장소만 필터링 (선택)
    3. 벡터 유사도 검색
    """
    try:
        print(f"\n[Recommend] 🎯 Request from {request.user_id}")
        print(f"[Recommend] 📍 GPS: ({request.latitude}, {request.longitude})")
        print(f"[Recommend] 🔍 Radius: {request.radius_km}km, Quest only: {request.quest_only}")
        
        # Base64 디코딩
        try:
            image_bytes = base64.b64decode(request.image)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid base64: {str(e)}")
        
        # 최적화된 검색
        results = search_similar_with_optimization(
            image_bytes=image_bytes,
            latitude=request.latitude,
            longitude=request.longitude,
            radius_km=request.radius_km,
            match_threshold=0.65,
            match_count=request.limit,
            quest_only=request.quest_only
        )
        
        print(f"[Recommend] ✅ Found {len(results)} recommendations")
        
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
        print(f"[Recommend] ❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/nearby-quests")
async def get_nearby_quests(
    latitude: float,
    longitude: float,
    radius_km: float = 5.0,
    limit: int = 10
):
    """
    주변 퀘스트 조회
    
    GPS 기반으로 반경 내 퀘스트를 검색
    """
    try:
        quests = search_nearby_quests(
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            limit=limit
        )
        
        return {
            "success": True,
            "count": len(quests),
            "quests": quests
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quests/category/{category}")
async def get_quests_by_category(
    category: str,
    limit: int = 20
):
    """
    카테고리별 퀘스트 조회
    """
    try:
        places = get_quest_places_by_category(category, limit)
        
        return {
            "success": True,
            "category": category,
            "count": len(places),
            "places": places
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quests/{quest_id}")
async def get_quest_detail(quest_id: str):
    """
    퀘스트 상세 정보 (퀴즈 포함)
    """
    try:
        db = get_db()
        
        # 퀘스트 조회
        quest_result = db.table("quests").select("*").eq("id", quest_id).single().execute()
        
        if not quest_result.data:
            raise HTTPException(status_code=404, detail="Quest not found")
        
        quest = quest_result.data
        
        # 장소 정보 조회
        place = db.table("places").select("*").eq("id", quest["place_id"]).single().execute()
        
        # 퀴즈 조회
        quizzes = db.table("quest_quizzes").select("*").eq("quest_id", quest_id).execute()
        
        return {
            "success": True,
            "quest": quest,
            "place": place.data if place.data else None,
            "quizzes": quizzes.data if quizzes.data else []
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quests/{quest_id}/submit")
async def submit_quiz_answer(
    quest_id: str,
    user_id: str,
    quiz_id: str,
    answer: int
):
    """
    퀴즈 정답 제출
    
    Args:
        quest_id: 퀘스트 ID
        user_id: 사용자 ID
        quiz_id: 퀴즈 ID
        answer: 선택한 답 (0-3)
    """
    try:
        db = get_db()
        
        # 퀴즈 조회
        quiz = db.table("quest_quizzes").select("*").eq("id", quiz_id).single().execute()
        
        if not quiz.data:
            raise HTTPException(status_code=404, detail="Quiz not found")
        
        is_correct = quiz.data["correct_answer"] == answer
        
        # 사용자 진행상황 업데이트
        progress_data = {
            "user_id": user_id,
            "quest_id": quest_id,
            "quiz_attempts": 1,
            "quiz_correct": is_correct
        }
        
        if is_correct:
            progress_data["status"] = "completed"
            progress_data["completed_at"] = "NOW()"
        
        # Upsert
        db.table("user_quest_progress").upsert(progress_data).execute()
        
        # 퀘스트 완료 횟수 증가
        if is_correct:
            quest = db.table("quests").select("completion_count").eq("id", quest_id).single().execute()
            current_count = quest.data.get("completion_count", 0)
            db.table("quests").update({"completion_count": current_count + 1}).eq("id", quest_id).execute()
        
        return {
            "success": True,
            "is_correct": is_correct,
            "explanation": quiz.data.get("explanation", "") if is_correct else None
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_recommendation_stats():
    """
    추천 시스템 통계
    """
    try:
        from services.pinecone_store import get_index_stats
        db = get_db()
        
        # 장소 통계
        places_result = db.table("places").select("count", count="exact").execute()
        
        # 퀘스트 통계
        quests_result = db.table("quests").select("count", count="exact").execute()
        
        # Pinecone 통계
        pinecone_stats = get_index_stats()
        
        return {
            "total_places": places_result.count,
            "total_quests": quests_result.count,
            "total_vectors": pinecone_stats.get("total_vectors", 0),
            "vector_dimension": pinecone_stats.get("dimension", 512),
            "index_fullness": pinecone_stats.get("index_fullness", 0.0)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

