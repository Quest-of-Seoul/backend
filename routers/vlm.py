"""
VLM Router - AR 카메라 이미지 분석 API
이미지 업로드 → VLM 분석 → 장소 식별 → TTS 생성
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, List
import base64
import time
from io import BytesIO

# Services
from services.vlm import (
    analyze_place_image,
    extract_place_info_from_vlm_response,
    calculate_confidence_score
)
from services.embedding import (
    generate_image_embedding,
    hash_image
)
from services.db import (
    search_places_by_radius,
    get_place_by_name,
    save_vlm_log,
    get_cached_vlm_result,
    increment_place_view_count
)
# Pinecone vector store (벡터 검색)
from services.pinecone_store import (
    search_similar_pinecone,
    upsert_pinecone
)
from services.ai import generate_docent_message
from services.tts import text_to_speech_url, text_to_speech
from services.storage import upload_audio_to_storage, compress_and_upload_image
import os

router = APIRouter()


# ============================================================
# Request/Response Models
# ============================================================

class VLMAnalyzeRequest(BaseModel):
    """이미지 분석 요청 (base64 방식 - Expo Go)"""
    user_id: str
    image: str  # base64 encoded
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    language: str = "ko"
    prefer_url: bool = True  # True: URL 반환, False: base64 반환
    enable_tts: bool = True
    use_cache: bool = True  # 캐싱 사용 여부


class SimilarImageRequest(BaseModel):
    """유사 이미지 검색 요청"""
    image: str  # base64 encoded
    limit: int = 3
    threshold: float = 0.7


# ============================================================
# Endpoints
# ============================================================

@router.post("/analyze")
async def analyze_image(request: VLMAnalyzeRequest):
    """
    AR 카메라 이미지 분석 (base64 방식)
    
    처리 흐름:
    1. 이미지 수신 (base64)
    2. 이미지 해시 생성 → 캐싱 체크
    3. GPS 기반 주변 장소 검색
    4. 이미지 임베딩 생성 → 벡터 유사도 검색
    5. GPT-4V API 호출 (이미지 분석)
    6. Gemini로 최종 설명 보강
    7. TTS 생성 (옵션)
    8. 로그 저장
    """
    start_time = time.time()
    
    try:
        print(f"\n[VLM API] 🎯 New analysis request from user: {request.user_id}")
        print(f"[VLM API] 📍 GPS: ({request.latitude}, {request.longitude})")
        print(f"[VLM API] 🌐 Language: {request.language}, Provider: GPT-4V")
        
        # 1. Base64 디코딩
        try:
            image_bytes = base64.b64decode(request.image)
            print(f"[VLM API] 📸 Image decoded: {len(image_bytes)} bytes")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid base64 image: {str(e)}")
        
        # 2. 이미지 해시 생성
        image_hash = hash_image(image_bytes)
        print(f"[VLM API] 🔑 Image hash: {image_hash[:16]}...")
        
        # 3. 캐싱 체크 (선택적)
        if request.use_cache:
            cached_result = get_cached_vlm_result(image_hash, max_age_hours=24)
            if cached_result:
                print("[VLM API] ⚡ Using cached result")
                return {
                    "cached": True,
                    "description": cached_result.get("final_description"),
                    "vlm_analysis": cached_result.get("vlm_response"),
                    "confidence_score": cached_result.get("confidence_score"),
                    "matched_place": cached_result.get("matched_place_id")
                }
        
        # 4. GPS 기반 주변 장소 검색
        nearby_places = []
        if request.latitude and request.longitude:
            nearby_places = search_places_by_radius(
                latitude=request.latitude,
                longitude=request.longitude,
                radius_km=1.0,
                limit_count=10
            )
            print(f"[VLM API] 📍 Found {len(nearby_places)} nearby places")
        
        # 5. 이미지 임베딩 생성 (병렬 처리 가능)
        embedding = generate_image_embedding(image_bytes)
        if not embedding:
            print("[VLM API] ⚠️ Embedding generation failed")
        
        # 6. 벡터 유사도 검색 (Pinecone)
        similar_images = []
        best_similarity = 0.0
        if embedding:
            similar_images = search_similar_pinecone(
                embedding=embedding,
                match_threshold=0.6,
                match_count=3
            )
            if similar_images:
                best_similarity = similar_images[0].get("similarity", 0.0)
                print(f"[VLM API] 🔍 Found {len(similar_images)} similar images (best: {best_similarity:.2f})")
        
        # 7. GPT-4V API 호출 (이미지 분석)
        vlm_response = analyze_place_image(
            image_bytes=image_bytes,
            nearby_places=nearby_places,
            language=request.language
        )
        
        if not vlm_response:
            raise HTTPException(status_code=503, detail="VLM service unavailable")
        
        print(f"[VLM API] 🤖 GPT-4V analysis complete: {len(vlm_response)} chars")
        
        # 8. VLM 응답에서 장소 정보 추출
        place_info = extract_place_info_from_vlm_response(vlm_response)
        print(f"[VLM API] 📝 Extracted place: {place_info.get('place_name', 'Unknown')}")
        
        # 9. 장소 매칭 (DB 검색)
        matched_place = None
        matched_place_id = None
        
        if place_info.get("place_name"):
            # 이름으로 검색
            matched_place = get_place_by_name(place_info["place_name"], fuzzy=True)
            
            # 유사 이미지에서 매칭
            if not matched_place and similar_images:
                matched_place = similar_images[0].get("place")
            
            if matched_place:
                matched_place_id = matched_place.get("id")
                print(f"[VLM API] ✅ Matched place: {matched_place.get('name')}")
                
                # 조회수 증가
                increment_place_view_count(matched_place_id)
        
        # 10. GPS 거리 계산
        gps_distance = None
        if matched_place and request.latitude and request.longitude:
            for nearby in nearby_places:
                if nearby.get("id") == matched_place_id:
                    gps_distance = nearby.get("distance_km")
                    break
        
        # 11. 신뢰도 점수 계산
        confidence_score = calculate_confidence_score(
            vlm_info=place_info,
            vector_similarity=best_similarity if similar_images else None,
            gps_distance_km=gps_distance
        )
        print(f"[VLM API] 📊 Confidence score: {confidence_score}")
        
        # 12. Gemini로 최종 설명 보강
        final_description = vlm_response
        
        if matched_place:
            # DB 메타데이터와 VLM 분석 결합
            enhancement_prompt = f"""
VLM 분석 결과:
{vlm_response}

장소 정보:
- 이름: {matched_place.get('name')}
- 카테고리: {matched_place.get('category')}
- 설명: {matched_place.get('description')}
- 주소: {matched_place.get('address')}

위 정보를 바탕으로 AR 도슨트처럼 친근하고 흥미롭게 3-4문장으로 이 장소를 소개해주세요.
"""
            try:
                final_description = generate_docent_message(
                    landmark=matched_place.get('name', '이 장소'),
                    user_message=enhancement_prompt if request.language == "ko" else None,
                    language=request.language
                )
                print("[VLM API] ✅ Description enhanced by Gemini")
            except Exception as e:
                print(f"[VLM API] ⚠️ Gemini enhancement failed: {e}")
        
        # 13. TTS 생성 (옵션)
        audio_url = None
        audio_base64 = None
        
        if request.enable_tts:
            try:
                language_code = f"{request.language}-KR" if request.language == "ko" else "en-US"
                
                if request.prefer_url:
                    # URL 방식 (Expo Go)
                    audio_url, audio_base64 = text_to_speech_url(
                        text=final_description,
                        language_code=language_code,
                        upload_to_storage=True
                    )
                    print(f"[VLM API] 🔊 TTS generated (URL)")
                else:
                    # Base64 방식 (Standalone)
                    audio_base64 = text_to_speech(
                        text=final_description,
                        language_code=language_code
                    )
                    print(f"[VLM API] 🔊 TTS generated (base64)")
            
            except Exception as tts_error:
                print(f"[VLM API] ⚠️ TTS generation failed: {tts_error}")
        
        # 14. 처리 시간 계산
        processing_time_ms = int((time.time() - start_time) * 1000)
        print(f"[VLM API] ⏱️ Processing time: {processing_time_ms}ms")
        
        # 15. 로그 저장 (이미지를 Storage에 업로드)
        try:
            # 이미지를 Supabase Storage에 업로드
            uploaded_image_url = compress_and_upload_image(
                image_bytes=image_bytes,
                max_size=1920,
                quality=85
            )
            
            save_vlm_log(
                user_id=request.user_id,
                image_url=uploaded_image_url,  # ✅ Storage URL
                latitude=request.latitude,
                longitude=request.longitude,
                vlm_provider="gpt4v",
                vlm_response=vlm_response,
                final_description=final_description,
                matched_place_id=matched_place_id,
                similar_places=[{"place_id": img.get("place", {}).get("id"), "similarity": img.get("similarity")} 
                               for img in similar_images],
                confidence_score=confidence_score,
                processing_time_ms=processing_time_ms,
                image_hash=image_hash
            )
        except Exception as log_error:
            print(f"[VLM API] ⚠️ Failed to save log: {log_error}")
        
        # 16. 응답 생성
        response_data = {
            "success": True,
            "description": final_description,
            "place": matched_place,
            "vlm_analysis": vlm_response,
            "similar_places": similar_images,
            "confidence_score": confidence_score,
            "processing_time_ms": processing_time_ms,
            "vlm_provider": "gpt4v"
        }
        
        # TTS 데이터 추가
        if request.prefer_url and audio_url:
            response_data["audio_url"] = audio_url
        elif audio_base64:
            response_data["audio"] = audio_base64
        
        print(f"[VLM API] ✅ Analysis complete!\n")
        return response_data
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[VLM API] ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/analyze-multipart")
async def analyze_image_multipart(
    user_id: str = Form(...),
    image: UploadFile = File(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    language: str = Form("ko"),
    prefer_url: bool = Form(False),
    enable_tts: bool = Form(True)
):
    """
    AR 카메라 이미지 분석 (multipart/form-data 방식 - Standalone)
    
    대용량 이미지 업로드에 적합
    """
    try:
        # 이미지 읽기
        image_bytes = await image.read()
        
        # base64로 변환하여 기존 함수 재사용
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        request = VLMAnalyzeRequest(
            user_id=user_id,
            image=image_base64,
            latitude=latitude,
            longitude=longitude,
            language=language,
            prefer_url=prefer_url,
            enable_tts=enable_tts
        )
        
        return await analyze_image(request)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Multipart upload failed: {str(e)}")


@router.post("/similar")
async def search_similar(request: SimilarImageRequest):
    """
    유사 이미지 검색 (벡터 검색)
    
    촬영한 사진과 비슷한 장소 이미지를 DB에서 검색
    """
    try:
        print(f"[VLM API] 🔍 Similar image search (limit: {request.limit})")
        
        # Base64 디코딩
        image_bytes = base64.b64decode(request.image)
        
        # 임베딩 생성
        embedding = generate_image_embedding(image_bytes)
        if not embedding:
            raise HTTPException(status_code=503, detail="Embedding service unavailable")
        
        # 유사도 검색 (Pinecone)
        similar_images = search_similar_pinecone(
            embedding=embedding,
            match_threshold=request.threshold,
            match_count=request.limit
        )
        
        print(f"[VLM API] ✅ Found {len(similar_images)} similar images")
        
        return {
            "success": True,
            "count": len(similar_images),
            "similar_images": similar_images
        }
    
    except Exception as e:
        print(f"[VLM API] ❌ Error: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/embed")
async def create_embedding(
    place_id: str = Form(...),
    image: UploadFile = File(...)
):
    """
    이미지 임베딩 생성 및 저장 (관리자용)
    
    장소 이미지를 업로드하고 Pinecone에 저장
    """
    try:
        import uuid
        
        print(f"[VLM API] 📤 Creating embedding for place: {place_id}")
        
        # 이미지 읽기
        image_bytes = await image.read()
        
        # 이미지 해시
        img_hash = hash_image(image_bytes)
        
        # Supabase Storage에 이미지 업로드
        image_url = compress_and_upload_image(
            image_bytes=image_bytes,
            max_size=1920,
            quality=85
        )
        
        if not image_url:
            raise HTTPException(status_code=500, detail="Image upload failed")
        
        print(f"[VLM API] ✅ Image uploaded: {image_url}")
        
        # 임베딩 생성
        embedding = generate_image_embedding(image_bytes)
        if not embedding:
            raise HTTPException(status_code=503, detail="Embedding generation failed")
        
        # Pinecone에 저장
        vector_id = str(uuid.uuid4())
        success = upsert_pinecone(
            vector_id=vector_id,
            embedding=embedding,
            metadata={
                "place_id": place_id,
                "image_url": image_url,
                "image_hash": img_hash,
                "source": "admin_upload",
                "filename": image.filename
            }
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save embedding")
        
        print(f"[VLM API] ✅ Embedding saved to Pinecone: {vector_id}")
        
        return {
            "success": True,
            "vector_id": vector_id,
            "place_id": place_id,
            "image_url": image_url,
            "embedding_dimension": len(embedding)
        }
    
    except Exception as e:
        print(f"[VLM API] ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Embedding creation failed: {str(e)}")


@router.get("/places/nearby")
async def get_nearby_places(
    latitude: float,
    longitude: float,
    radius_km: float = 1.0,
    limit: int = 10
):
    """
    GPS 기반 주변 장소 조회
    """
    try:
        places = search_places_by_radius(
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            limit_count=limit
        )
        
        return {
            "success": True,
            "count": len(places),
            "places": places
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/health")
async def health_check():
    """
    VLM 서비스 상태 체크
    """
    from services.vlm import OPENAI_AVAILABLE
    from services.embedding import CLIP_AVAILABLE
    
    # Pinecone 연결 테스트
    pinecone_available = False
    pinecone_stats = {}
    try:
        from services.pinecone_store import get_index_stats
        pinecone_stats = get_index_stats()
        pinecone_available = True
    except:
        pass
    
    return {
        "status": "healthy",
        "services": {
            "gpt4v": OPENAI_AVAILABLE,
            "clip": CLIP_AVAILABLE,
            "pinecone": pinecone_available
        },
        "pinecone_stats": pinecone_stats if pinecone_available else None
    }
