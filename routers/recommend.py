"""Recommendation Router - AI Place Recommendation API"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
import base64
import time
import logging

from services.recommendation import recommend_places, recommend_similar_to_place

logger = logging.getLogger(__name__)
router = APIRouter()


class GPSLocation(BaseModel):
    latitude: float = Field(..., ge=-90, le=90, description="Latitude (-90 to 90)")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude (-180 to 180)")


class RecommendRequest(BaseModel):
    image: str = Field(..., description="Base64 encoded image (required)")
    category: str = Field(..., description="Category filter (required)")
    place_id: Optional[str] = Field(None, description="Place ID to exclude (for detail page)")
    gps: Optional[GPSLocation] = Field(None, description="User GPS location (optional)")
    top_k: int = Field(5, ge=1, le=10, description="Number of recommendations (1-10)")
    threshold: float = Field(0.7, ge=0.0, le=1.0, description="Minimum confidence score (0.0-1.0)")
    context: str = Field("search", description="Entry context: chat|search|detail|banner")
    
    class Config:
        json_schema_extra = {
            "example": {
                "image": "base64_encoded_image_string...",
                "category": "역사유적",
                "top_k": 5,
                "threshold": 0.7,
                "context": "search"
            }
        }


class SimilarPlaceRequest(BaseModel):
    place_id: str = Field(..., description="Place ID to find similar places")
    top_k: int = Field(3, ge=1, le=10, description="Number of recommendations")
    threshold: float = Field(0.7, ge=0.0, le=1.0, description="Minimum similarity score")
    
    class Config:
        json_schema_extra = {
            "example": {
                "place_id": "place-001-gyeongbokgung",
                "top_k": 3,
                "threshold": 0.7
            }
        }


@router.post("/recommend")
async def recommend(request: RecommendRequest):
    """
    AI 기반 장소 추천
    
    이미지와 카테고리를 기반으로 유사한 장소를 추천합니다.
    
    **진입 경로 (context):**
    - `chat`: 채팅 중 추천
    - `search`: 검색/필터바
    - `detail`: 장소 상세 페이지
    - `banner`: 퀘스트 탭 배너
    
    **추천 로직:**
    - 이미지 유사도 × 카테고리 매칭 = 최종 점수
    - threshold 이상의 장소만 반환
    - 최종 점수 기준 내림차순 정렬
    
    **응답:**
    - 추천 장소 리스트 (최대 top_k개)
    - 각 장소별 유사도 점수
    - GPS 제공 시 거리 정보 포함
    """
    start_time = time.time()
    
    try:
        logger.info(f"Recommendation request - category: {request.category}, context: {request.context}")
        
        # Validate and decode image
        try:
            image_bytes = base64.b64decode(request.image)
            logger.info(f"Image decoded: {len(image_bytes)} bytes")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid base64 image: {str(e)}")
        
        # Validate image size (max 20MB)
        if len(image_bytes) > 20 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Image too large (max 20MB)")
        
        # Convert GPS to dict if provided
        gps_dict = None
        if request.gps:
            gps_dict = {
                "latitude": request.gps.latitude,
                "longitude": request.gps.longitude
            }
            logger.info(f"GPS location: {gps_dict}")
        
        # Get recommendations
        result = recommend_places(
            image_bytes=image_bytes,
            category=request.category,
            top_k=request.top_k,
            threshold=request.threshold,
            place_id=request.place_id,
            gps=gps_dict,
            context=request.context
        )
        
        if not result["success"]:
            error_msg = result.get("error", "Recommendation failed")
            logger.error(f"Recommendation failed: {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)
        
        processing_time_ms = int((time.time() - start_time) * 1000)
        result["processing_time_ms"] = processing_time_ms
        
        logger.info(f"Recommendation completed: {result['count']} places, {processing_time_ms}ms")
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Recommendation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post("/similar")
async def get_similar_places(request: SimilarPlaceRequest):
    """
    특정 장소와 유사한 장소 추천 (장소 상세 페이지용)
    
    장소 ID를 기반으로 같은 카테고리의 유사한 장소를 추천합니다.
    이미지 업로드 없이 Pinecone에 저장된 벡터를 활용합니다.
    
    **사용 사례:**
    - 장소 상세 페이지 "비슷한 장소 추천" 기능
    - 자동으로 해당 장소의 이미지와 카테고리 사용
    
    **응답:**
    - 소스 장소 정보
    - 유사한 장소 리스트
    - 각 장소별 유사도 점수
    """
    start_time = time.time()
    
    try:
        logger.info(f"Similar place request: {request.place_id}")
        
        result = recommend_similar_to_place(
            place_id=request.place_id,
            top_k=request.top_k,
            threshold=request.threshold
        )
        
        if not result["success"]:
            error_msg = result.get("error", "Failed to find similar places")
            
            if "not found" in error_msg.lower():
                raise HTTPException(status_code=404, detail=error_msg)
            else:
                raise HTTPException(status_code=500, detail=error_msg)
        
        processing_time_ms = int((time.time() - start_time) * 1000)
        result["processing_time_ms"] = processing_time_ms
        
        logger.info(f"Similar places found: {result['count']} places, {processing_time_ms}ms")
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Similar place error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/categories")
async def get_categories():
    """
    사용 가능한 카테고리 목록 조회
    
    추천 시스템에서 사용 가능한 카테고리 목록을 반환합니다.
    """
    categories = [
        {
            "id": "역사유적",
            "name": "역사유적",
            "name_en": "Historical Sites",
            "similar_to": ["문화재", "궁궐", "유적지"]
        },
        {
            "id": "관광지",
            "name": "관광지",
            "name_en": "Tourist Attractions",
            "similar_to": ["명소", "전망대"]
        },
        {
            "id": "문화마을",
            "name": "문화마을",
            "name_en": "Cultural Villages",
            "similar_to": ["한옥마을", "전통마을"]
        },
        {
            "id": "종교시설",
            "name": "종교시설",
            "name_en": "Religious Sites",
            "similar_to": ["사찰", "성당", "교회"]
        },
        {
            "id": "광장",
            "name": "광장",
            "name_en": "Squares & Parks",
            "similar_to": ["공원", "야외공간"]
        }
    ]
    
    return {
        "categories": categories,
        "count": len(categories)
    }


@router.get("/health")
async def health_check():
    """추천 서비스 상태 확인"""
    from services.embedding import CLIP_AVAILABLE
    from services.pinecone_store import get_index_stats
    
    pinecone_available = False
    pinecone_stats = {}
    
    try:
        pinecone_stats = get_index_stats()
        pinecone_available = True
    except Exception as e:
        logger.warning(f"Pinecone health check failed: {e}")
    
    status = "healthy" if (CLIP_AVAILABLE and pinecone_available) else "degraded"
    
    return {
        "status": status,
        "services": {
            "clip_embedding": CLIP_AVAILABLE,
            "pinecone": pinecone_available
        },
        "pinecone_stats": pinecone_stats if pinecone_available else None
    }
