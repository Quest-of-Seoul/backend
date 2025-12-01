"""VLM Router"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from pydantic import BaseModel
from typing import Optional, List
import base64
import time
import logging
from io import BytesIO

from services.vlm import (
    analyze_place_image,
    extract_place_info_from_vlm_response,
    calculate_confidence_score
)
from services.embedding import generate_image_embedding, hash_image
from services.db import (
    search_places_by_radius,
    get_place_by_name,
    save_vlm_log,
    get_cached_vlm_result,
    increment_place_view_count
)
from services.pinecone_store import search_similar_pinecone, upsert_pinecone
from services.ai import generate_docent_message
from services.tts import text_to_speech_url, text_to_speech
from services.storage import upload_audio_to_storage, compress_and_upload_image
from services.auth_deps import get_current_user_id

logger = logging.getLogger(__name__)
router = APIRouter()


class VLMAnalyzeRequest(BaseModel):
    image: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    language: str = "en"
    prefer_url: bool = True
    enable_tts: bool = True
    use_cache: bool = True
    quest_id: Optional[int] = None


class SimilarImageRequest(BaseModel):
    image: str
    limit: int = 3
    threshold: float = 0.7


@router.post("/analyze")
async def analyze_image(request: VLMAnalyzeRequest, user_id: str = Depends(get_current_user_id)):
    start_time = time.time()
    
    try:
        logger.info(f"VLM analysis: user={user_id}, GPS=({request.latitude}, {request.longitude})")
        
        try:
            image_bytes = base64.b64decode(request.image)
            logger.info(f"Image decoded: {len(image_bytes)} bytes")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid base64 image: {str(e)}")
        
        image_hash = hash_image(image_bytes)
        logger.info(f"Image hash: {image_hash[:16]}...")
        
        if request.use_cache:
            cached_result = get_cached_vlm_result(image_hash, max_age_hours=24)
            if cached_result:
                logger.info("Using cached result")
                return {
                    "cached": True,
                    "description": cached_result.get("final_description"),
                    "vlm_analysis": cached_result.get("vlm_response"),
                    "confidence_score": cached_result.get("confidence_score"),
                    "matched_place": cached_result.get("matched_place_id")
                }
        
        nearby_places = []
        if request.latitude and request.longitude:
            nearby_places = search_places_by_radius(
                latitude=request.latitude,
                longitude=request.longitude,
                radius_km=1.0,
                limit_count=10
            )
            logger.info(f"Found {len(nearby_places)} nearby places")
        
        embedding = generate_image_embedding(image_bytes)
        if not embedding:
            logger.warning("Embedding generation failed")
        
        similar_images = []
        best_similarity = 0.0
        matched_place_from_vector = None
        
        if embedding:
            from services.optimized_search import search_with_gps_filter
            
            similar_images = search_with_gps_filter(
                embedding=embedding,
                latitude=request.latitude,
                longitude=request.longitude,
                radius_km=5.0,
                match_threshold=0.6,
                match_count=5,
                quest_only=False
            )
            
            if similar_images:
                best_similarity = similar_images[0].get("similarity", 0.0)
                matched_place_from_vector = similar_images[0].get("place")
                logger.info(f"Found {len(similar_images)} similar images (best: {best_similarity:.2f})")
        
        enhanced_nearby_places = []
        
        if matched_place_from_vector:
            enhanced_nearby_places.append({
                "id": matched_place_from_vector.get("id"),
                "name": matched_place_from_vector.get("name"),
                "category": matched_place_from_vector.get("category"),
                "distance_km": 0.0,
                "source": "vector_search"
            })
        
        for np in nearby_places:
            if not any(ep.get("id") == np.get("id") for ep in enhanced_nearby_places):
                enhanced_nearby_places.append(np)
        
        quest_context = None
        if request.quest_id:
            try:
                from routers.ai_station import fetch_quest_context
                quest_context = fetch_quest_context(request.quest_id)
                logger.info(f"Quest context loaded: quest_id={request.quest_id}")
            except Exception as e:
                logger.warning(f"Failed to load quest context: {e}")
        
        vlm_response = analyze_place_image(
            image_bytes=image_bytes,
            nearby_places=enhanced_nearby_places,
            language="en",
            quest_context=quest_context
        )
        
        if not vlm_response:
            raise HTTPException(status_code=503, detail="VLM service unavailable")
        
        logger.info(f"GPT-4V analysis complete: {len(vlm_response)} chars")
        
        place_info = extract_place_info_from_vlm_response(vlm_response)
        logger.info(f"Extracted place: {place_info.get('place_name', 'Unknown')}")
        
        matched_place = None
        matched_place_id = None
        
        if matched_place_from_vector:
            matched_place = matched_place_from_vector
            matched_place_id = matched_place.get("id")
            logger.info(f"Matched place from vector search: {matched_place.get('name')}")
        
        elif place_info.get("place_name"):
            matched_place = get_place_by_name(place_info["place_name"], fuzzy=True)
            if matched_place:
                matched_place_id = matched_place.get("id")
                logger.info(f"Matched place from VLM: {matched_place.get('name')}")
        
        if not matched_place and similar_images:
            matched_place = similar_images[0].get("place")
            if matched_place:
                matched_place_id = matched_place.get("id")
                logger.info(f"Matched place from vector fallback: {matched_place.get('name')}")
        
        if not matched_place and nearby_places:
            matched_place = nearby_places[0]
            matched_place_id = matched_place.get("id")
            logger.info(f"Matched place from GPS: {matched_place.get('name')}")
        
        if matched_place and matched_place_id:
            increment_place_view_count(matched_place_id)
        
        gps_distance = None
        if matched_place and request.latitude and request.longitude:
            for nearby in nearby_places:
                if nearby.get("id") == matched_place_id:
                    gps_distance = nearby.get("distance_km")
                    break
        
        confidence_score = calculate_confidence_score(
            vlm_info=place_info,
            vector_similarity=best_similarity if similar_images else None,
            gps_distance_km=gps_distance
        )
        logger.info(f"Confidence score: {confidence_score}")
        
        final_description = vlm_response
        
        if matched_place:
            enhancement_prompt = f"""
VLM Analysis Result:
{vlm_response}

Place Information:
- Name: {matched_place.get('name')}
- Category: {matched_place.get('category')}
- Description: {matched_place.get('description')}
- Address: {matched_place.get('address')}

Based on the above information, please introduce this place in a friendly and engaging way in 3-4 sentences, like an AR docent.
"""
            try:
                final_description = generate_docent_message(
                    landmark=matched_place.get('name', 'This place'),
                    user_message=enhancement_prompt,
                    language="en"
                )
                logger.info("Description enhanced by Gemini")
            except Exception as e:
                logger.warning(f"Gemini enhancement failed: {e}")
        
        audio_url = None
        audio_base64 = None
        
        if request.enable_tts:
            try:
                language_code = "en-US"
                
                if request.prefer_url:
                    audio_url, audio_base64 = text_to_speech_url(
                        text=final_description,
                        language_code=language_code,
                        upload_to_storage=True
                    )
                    logger.info("TTS generated (URL)")
                else:
                    audio_base64 = text_to_speech(
                        text=final_description,
                        language_code=language_code
                    )
                    logger.info("TTS generated (base64)")
            
            except Exception as tts_error:
                logger.warning(f"TTS generation failed: {tts_error}")
        
        processing_time_ms = int((time.time() - start_time) * 1000)
        logger.info(f"Processing time: {processing_time_ms}ms")
        
        try:
            uploaded_image_url = compress_and_upload_image(
                image_bytes=image_bytes,
                max_size=1920,
                quality=85
            )
            
            save_vlm_log(
                user_id=user_id,
                image_url=uploaded_image_url,
                latitude=request.latitude,
                longitude=request.longitude,
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
            logger.warning(f"Failed to save log: {log_error}")
        
        recommended_quests = []
        try:
            from services.quest_rag import search_quests_by_rag_text
            from services.embedding import generate_text_embedding
            
            query_text_parts = []
            if place_info.get("place_name"):
                query_text_parts.append(place_info["place_name"])
            if place_info.get("category"):
                query_text_parts.append(place_info["category"])
            if place_info.get("features"):
                query_text_parts.append(place_info["features"][:100])
            
            if query_text_parts:
                query_text = " ".join(query_text_parts)
                text_embedding = generate_text_embedding(query_text)
                
                if text_embedding:
                    rag_quests = search_quests_by_rag_text(
                        text_embedding=text_embedding,
                        match_threshold=0.6,
                        match_count=5,
                        latitude=request.latitude,
                        longitude=request.longitude,
                        radius_km=10.0
                    )
                    
                    for rag_result in rag_quests:
                        quest = rag_result.get("quest", {})
                        recommended_quests.append({
                            "id": quest.get("id"),
                            "name": quest.get("name"),
                            "category": quest.get("category"),
                            "description": quest.get("description", "")[:200],
                            "similarity": rag_result.get("similarity", 0.0),
                            "distance_km": quest.get("distance_km"),
                            "reward_point": quest.get("reward_point")
                        })
                    
                    logger.info(f"Found {len(recommended_quests)} recommended quests via RAG")
        except Exception as e:
            logger.warning(f"Failed to get recommended quests: {e}")
        
        response_data = {
            "success": True,
            "description": final_description,
            "place": matched_place,
            "vlm_analysis": vlm_response,
            "similar_places": similar_images,
            "confidence_score": confidence_score,
            "processing_time_ms": processing_time_ms
        }
        
        if recommended_quests:
            response_data["recommended_quests"] = recommended_quests
        
        if request.prefer_url and audio_url:
            response_data["audio_url"] = audio_url
        elif audio_base64:
            response_data["audio"] = audio_base64
        
        logger.info("Analysis complete")
        return response_data
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/analyze-multipart")
async def analyze_image_multipart(
    image: UploadFile = File(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    language: str = Form("en"),
    prefer_url: bool = Form(False),
    enable_tts: bool = Form(True),
    user_id: str = Depends(get_current_user_id)
):
    try:
        image_bytes = await image.read()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        request = VLMAnalyzeRequest(
            image=image_base64,
            latitude=latitude,
            longitude=longitude,
            language=language,
            prefer_url=prefer_url,
            enable_tts=enable_tts
        )
        
        return await analyze_image(request, user_id=user_id)
    
    except Exception as e:
        logger.error(f"Multipart upload error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Multipart upload failed: {str(e)}")


@router.post("/similar")
async def search_similar(request: SimilarImageRequest):
    try:
        logger.info(f"Similar image search (limit: {request.limit})")
        
        image_bytes = base64.b64decode(request.image)
        
        embedding = generate_image_embedding(image_bytes)
        if not embedding:
            raise HTTPException(status_code=503, detail="Embedding service unavailable")
        
        similar_images = search_similar_pinecone(
            embedding=embedding,
            match_threshold=request.threshold,
            match_count=request.limit
        )
        
        logger.info(f"Found {len(similar_images)} similar images")
        
        return {
            "success": True,
            "count": len(similar_images),
            "similar_images": similar_images
        }
    
    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/embed")
async def create_embedding(
    place_id: str = Form(...),
    image: UploadFile = File(...)
):
    try:
        import uuid
        
        logger.info(f"Creating embedding for place: {place_id}")
        
        image_bytes = await image.read()
        img_hash = hash_image(image_bytes)
        
        image_url = compress_and_upload_image(
            image_bytes=image_bytes,
            max_size=1920,
            quality=85
        )
        
        if not image_url:
            raise HTTPException(status_code=500, detail="Image upload failed")
        
        logger.info(f"Image uploaded: {image_url}")
        
        embedding = generate_image_embedding(image_bytes)
        if not embedding:
            raise HTTPException(status_code=503, detail="Embedding generation failed")
        
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
        
        logger.info(f"Embedding saved to Pinecone: {vector_id}")
        
        return {
            "success": True,
            "vector_id": vector_id,
            "place_id": place_id,
            "image_url": image_url,
            "embedding_dimension": len(embedding)
        }
    
    except Exception as e:
        logger.error(f"Embedding error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Embedding creation failed: {str(e)}")


@router.get("/places/nearby")
async def get_nearby_places(
    latitude: float,
    longitude: float,
    radius_km: float = 1.0,
    limit: int = 10
):
    try:
        places = search_places_by_radius(
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            limit_count=limit
        )
        
        logger.info(f"Found {len(places)} places")
        
        return {
            "success": True,
            "count": len(places),
            "places": places
        }
    
    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/health")
async def health_check():
    from services.vlm import OPENAI_AVAILABLE
    from services.embedding import CLIP_AVAILABLE
    
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
