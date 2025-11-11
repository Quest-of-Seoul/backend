"""Docent Router"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging
import base64

from services.ai import generate_docent_message, generate_quiz
from services.tts import text_to_speech

logger = logging.getLogger(__name__)
router = APIRouter()


class DocentRequest(BaseModel):
    landmark: str
    user_message: Optional[str] = None
    language: str = "ko"


class QuizRequest(BaseModel):
    landmark: str
    language: str = "ko"


class TTSRequest(BaseModel):
    text: str
    language_code: str = "ko-KR"


@router.post("/chat")
async def chat_with_docent(request: DocentRequest):
    """AI docent chat"""
    try:
        logger.info(f"Docent chat: {request.landmark}")
        
        ai_response = generate_docent_message(
            landmark=request.landmark,
            user_message=request.user_message,
            language=request.language
        )
        
        logger.info(f"AI response generated: {len(ai_response)} chars")
        
        return {
            "message": ai_response,
            "landmark": request.landmark,
            "language": request.language
        }
    
    except Exception as e:
        logger.error(f"Docent error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/quiz")
async def get_quiz(request: QuizRequest):
    """Generate quiz"""
    try:
        logger.info(f"Quiz generation: {request.landmark}")
        
        quiz = generate_quiz(request.landmark, request.language)
        
        return quiz
    
    except Exception as e:
        logger.error(f"Quiz error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


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
            "audio": audio_base64,
            "format": "mp3",
            "size_bytes": len(audio_bytes)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TTS error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/health")
async def health_check():
    """Service health check"""
    from services.ai import GEMINI_AVAILABLE
    
    return {
        "status": "healthy",
        "services": {
            "gemini": GEMINI_AVAILABLE,
            "tts": True
        }
    }
