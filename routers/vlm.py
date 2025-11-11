"""VLM Router"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
import base64
import time
import logging

from services.vlm import analyze_place_image
from services.embedding import generate_image_embedding, hash_image
from services.pinecone_store import search_similar_pinecone, upsert_pinecone
from services.tts import text_to_speech

logger = logging.getLogger(__name__)
router = APIRouter()


class VLMAnalyzeRequest(BaseModel):
    image: str
    language: str = "ko"


class VLMAnalyzeResponse(BaseModel):
    vlm_response: str
    image_hash: str
    vector_matches: List[Dict]
    confidence_score: float
    processing_time_ms: int


class SimilarImageRequest(BaseModel):
    image: str
    top_k: int = 5
    threshold: float = 0.7


class EmbeddingRequest(BaseModel):
    image: str
    place_id: str
    metadata: Optional[Dict] = {}


class TTSRequest(BaseModel):
    text: str
    language_code: str = "ko-KR"


@router.post("/analyze", response_model=VLMAnalyzeResponse)
async def analyze_image(request: VLMAnalyzeRequest):
    """Image analysis using GPT-4V and Pinecone"""
    start_time = time.time()
    
    try:
        logger.info("VLM analysis request received")
        
        image_bytes = base64.b64decode(request.image)
        logger.info(f"Image decoded: {len(image_bytes)} bytes")
        
        image_hash = hash_image(image_bytes)
        logger.info(f"Image hash: {image_hash[:16]}...")
        
        vlm_response = analyze_place_image(
            image_bytes=image_bytes,
            language=request.language
        )
        
        if not vlm_response:
            raise HTTPException(status_code=503, detail="VLM service unavailable")
        
        logger.info("GPT-4V analysis complete")
        
        embedding = generate_image_embedding(image_bytes)
        if not embedding:
            logger.warning("Embedding generation failed")
            vector_matches = []
        else:
            vector_matches = search_similar_pinecone(
                embedding=embedding,
                match_threshold=0.6,
                match_count=5
            )
            logger.info(f"Found {len(vector_matches)} similar images")
        
        confidence_score = 0.0
        if vector_matches:
            confidence_score = vector_matches[0].get("similarity", 0.0)
        
        processing_time_ms = int((time.time() - start_time) * 1000)
        logger.info(f"Processing time: {processing_time_ms}ms")
        
        return VLMAnalyzeResponse(
            vlm_response=vlm_response,
            image_hash=image_hash,
            vector_matches=vector_matches,
            confidence_score=confidence_score,
            processing_time_ms=processing_time_ms
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/similar")
async def search_similar(request: SimilarImageRequest):
    """Similar image search"""
    try:
        logger.info(f"Similar search request (top_k: {request.top_k})")
        
        image_bytes = base64.b64decode(request.image)
        
        embedding = generate_image_embedding(image_bytes)
        if not embedding:
            raise HTTPException(status_code=503, detail="Embedding service unavailable")
        
        similar_images = search_similar_pinecone(
            embedding=embedding,
            match_threshold=request.threshold,
            match_count=request.top_k
        )
        
        logger.info(f"Found {len(similar_images)} similar images")
        
        return {
            "success": True,
            "count": len(similar_images),
            "matches": similar_images
        }
    
    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/embed")
async def create_embedding(request: EmbeddingRequest):
    """Create and save image embedding"""
    try:
        import uuid
        
        logger.info(f"Creating embedding for place: {request.place_id}")
        
        image_bytes = base64.b64decode(request.image)
        img_hash = hash_image(image_bytes)
        
        embedding = generate_image_embedding(image_bytes)
        if not embedding:
            raise HTTPException(status_code=503, detail="Embedding generation failed")
        
        vector_id = str(uuid.uuid4())
        
        metadata = {
            "place_id": request.place_id,
            "image_hash": img_hash,
            **request.metadata
        }
        
        success = upsert_pinecone(
            vector_id=vector_id,
            embedding=embedding,
            metadata=metadata
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save to Pinecone")
        
        logger.info(f"Embedding saved: {vector_id}")
        
        return {
            "success": True,
            "vector_id": vector_id,
            "place_id": request.place_id,
            "image_hash": img_hash,
            "dimension": len(embedding)
        }
    
    except Exception as e:
        logger.error(f"Embedding error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed: {str(e)}")


@router.post("/tts")
async def generate_tts(request: TTSRequest):
    """Generate TTS audio"""
    try:
        logger.info(f"TTS request: {len(request.text)} chars")
        
        audio_bytes = text_to_speech(
            text=request.text,
            language_code=request.language_code
        )
        
        if not audio_bytes:
            raise HTTPException(status_code=503, detail="TTS service unavailable")
        
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        
        logger.info(f"TTS generated: {len(audio_bytes)} bytes")
        
        return {
            "success": True,
            "audio": audio_base64,
            "format": "mp3",
            "size_bytes": len(audio_bytes)
        }
    
    except Exception as e:
        logger.error(f"TTS error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"TTS failed: {str(e)}")


@router.get("/health")
async def health_check():
    """Service health check"""
    from services.vlm import OPENAI_AVAILABLE
    from services.embedding import CLIP_AVAILABLE
    from services.pinecone_store import get_index_stats
    
    pinecone_available = False
    pinecone_stats = {}
    
    try:
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
