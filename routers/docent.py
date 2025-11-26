"""Docent Router"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends
from pydantic import BaseModel
from typing import Optional
import asyncio
import json
import logging
from services.ai import generate_docent_message, generate_quiz
from services.tts import text_to_speech, text_to_speech_url, text_to_speech_bytes
from services.db import get_db
from services.auth_deps import get_current_user_id

logger = logging.getLogger(__name__)
router = APIRouter()


class DocentRequest(BaseModel):
    landmark: str
    user_message: Optional[str] = None
    language: str = "ko"
    prefer_url: bool = False
    enable_tts: bool = True


class TTSRequest(BaseModel):
    text: str
    language_code: str = "ko-KR"
    prefer_url: bool = False


@router.post("/chat")
async def chat_with_docent(request: DocentRequest, user_id: str = Depends(get_current_user_id)):
    """AI docent chat with TTS support"""
    try:
        logger.info(f"Docent chat: {request.landmark} (TTS: {request.enable_tts})")

        ai_response = generate_docent_message(
            landmark=request.landmark,
            user_message=request.user_message,
            language=request.language
        )

        audio_url = None
        audio_base64 = None

        if request.enable_tts:
            try:
                language_code = f"{request.language}-KR" if request.language == "ko" else "en-US"

                if request.prefer_url:
                    audio_url, audio_base64 = text_to_speech_url(
                        text=ai_response,
                        language_code=language_code,
                        upload_to_storage=True
                    )
                else:
                    audio_base64 = text_to_speech(
                        text=ai_response,
                        language_code=language_code
                    )

            except Exception as tts_error:
                logger.warning(f"TTS generation failed: {tts_error}")

        try:
            db = get_db()
            db.table("chat_logs").insert({
                "user_id": user_id,
                "landmark": request.landmark,
                "user_message": request.user_message or "",
                "ai_response": ai_response
            }).execute()
        except Exception as db_error:
            logger.warning(f"Failed to save chat log: {db_error}")

        response = {
            "message": ai_response,
            "landmark": request.landmark
        }

        if request.prefer_url and audio_url:
            response["audio_url"] = audio_url
        elif audio_base64:
            response["audio"] = audio_base64

        return response

    except Exception as e:
        logger.error(f"Docent error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")


@router.post("/quiz")
async def get_quiz(landmark: str, language: str = "ko"):
    """Generate quiz question about landmark"""
    try:
        logger.info(f"Quiz generation: {landmark}")
        quiz = generate_quiz(landmark, language)
        return quiz
    except Exception as e:
        logger.error(f"Quiz error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating quiz: {str(e)}")


@router.post("/tts")
async def generate_tts(request: TTSRequest):
    """Convert text to speech"""
    try:
        logger.info(f"TTS request: {len(request.text)} chars")

        audio_url = None
        audio_base64 = None

        if request.prefer_url:
            audio_url, audio_base64 = text_to_speech_url(
                text=request.text,
                language_code=request.language_code,
                upload_to_storage=True
            )

            if not audio_url:
                raise HTTPException(status_code=503, detail="TTS service unavailable")

            return {
                "audio_url": audio_url,
                "audio": audio_base64,
                "text": request.text
            }
        else:
            audio_base64 = text_to_speech(
                text=request.text,
                language_code=request.language_code
            )

            if not audio_base64:
                raise HTTPException(status_code=503, detail="TTS service unavailable")

            return {
                "audio": audio_base64,
                "text": request.text
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TTS error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating TTS: {str(e)}")


@router.get("/history")
async def get_chat_history(limit: int = 10, user_id: str = Depends(get_current_user_id)):
    """Get user's chat history"""
    try:
        db = get_db()
        result = db.table("chat_logs") \
            .select("*") \
            .eq("user_id", user_id) \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()

        logger.info(f"Retrieved {len(result.data)} chat logs")
        return {"history": result.data}

    except Exception as e:
        logger.error(f"History error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching history: {str(e)}")


@router.websocket("/ws/tts")
async def websocket_tts(websocket: WebSocket):
    """WebSocket endpoint for TTS streaming"""
    await websocket.accept()
    logger.info("WebSocket TTS client connected")

    try:
        data = await websocket.receive_text()
        request_data = json.loads(data)

        text = request_data.get("text", "")
        language_code = request_data.get("language_code", "ko-KR")

        logger.info(f"TTS WS request: {len(text)} chars")

        if not text:
            await websocket.send_text(json.dumps({"error": "No text provided"}))
            await websocket.close()
            return

        audio_bytes = text_to_speech_bytes(
            text=text,
            language_code=language_code
        )

        if not audio_bytes:
            await websocket.send_text(json.dumps({"error": "TTS generation failed"}))
            await websocket.close()
            return

        logger.info(f"Generated {len(audio_bytes)} bytes of audio")

        chunk_size = 4096
        total_chunks = (len(audio_bytes) + chunk_size - 1) // chunk_size

        for i in range(0, len(audio_bytes), chunk_size):
            chunk = audio_bytes[i:i + chunk_size]
            await websocket.send_bytes(chunk)
            await asyncio.sleep(0.01)

            if (i // chunk_size) % 10 == 0:
                progress = (i // chunk_size + 1) / total_chunks * 100
                logger.debug(f"Streaming progress: {progress:.1f}%")

        await websocket.send_text("DONE")
        logger.info("Streaming complete")

        await websocket.close()

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        try:
            await websocket.send_text(json.dumps({"error": str(e)}))
            await websocket.close()
        except:
            pass


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for AI chat with TTS streaming"""
    await websocket.accept()
    logger.info("WebSocket chat client connected")

    try:
        data = await websocket.receive_text()
        request_data = json.loads(data)

        user_id = request_data.get("user_id", "")
        landmark = request_data.get("landmark", "")
        user_message = request_data.get("user_message")
        language = request_data.get("language", "ko")
        enable_tts = request_data.get("enable_tts", True)

        logger.info(f"Chat WS: {landmark} (TTS: {enable_tts})")

        ai_response = generate_docent_message(
            landmark=landmark,
            user_message=user_message,
            language=language
        )

        logger.info(f"AI response: {len(ai_response)} chars")

        await websocket.send_text(json.dumps({
            "type": "text",
            "message": ai_response,
            "landmark": landmark
        }))

        try:
            db = get_db()
            db.table("chat_logs").insert({
                "user_id": user_id,
                "landmark": landmark,
                "user_message": user_message or "",
                "ai_response": ai_response
            }).execute()
        except Exception as db_error:
            logger.warning(f"Failed to save chat log: {db_error}")

        if enable_tts:
            language_code = f"{language}-KR" if language == "ko" else "en-US"
            audio_bytes = text_to_speech_bytes(
                text=ai_response,
                language_code=language_code
            )

            if audio_bytes:
                chunk_size = 4096
                for i in range(0, len(audio_bytes), chunk_size):
                    chunk = audio_bytes[i:i + chunk_size]
                    await websocket.send_bytes(chunk)
                    await asyncio.sleep(0.01)

                logger.info(f"Streamed {len(audio_bytes)} bytes of audio")
        else:
            logger.info("TTS disabled")

        await websocket.send_text("DONE")
        logger.info("Chat complete")

        await websocket.close()

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        try:
            await websocket.send_text(json.dumps({"error": str(e)}))
            await websocket.close()
        except:
            pass
