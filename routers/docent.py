"""
Docent router - AI conversation endpoints
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Optional
import asyncio
import json
from services.ai import generate_docent_message, generate_quiz
from services.tts import text_to_speech, text_to_speech_url, text_to_speech_bytes
from services.db import get_db

router = APIRouter()


class DocentRequest(BaseModel):
    user_id: str
    landmark: str
    user_message: Optional[str] = None
    language: str = "ko"
    prefer_url: bool = False  # True for Expo Go, False for standalone
    enable_tts: bool = True  # False to skip TTS generation (text only)


class TTSRequest(BaseModel):
    text: str
    language_code: str = "ko-KR"
    prefer_url: bool = False  # True for Expo Go, False for standalone


@router.post("/chat")
async def chat_with_docent(request: DocentRequest):
    """
    Get AI docent response about a landmark

    Returns text and audio (TTS)
    - If prefer_url=True (Expo Go): Returns audio_url from Supabase Storage
    - If prefer_url=False (Standalone): Returns base64 audio for WebSocket
    """
    try:
        print(f"[Docent] 🎯 Generating message for {request.landmark} (prefer_url={request.prefer_url})")

        # Generate AI response using Gemini
        ai_response = generate_docent_message(
            landmark=request.landmark,
            user_message=request.user_message,
            language=request.language
        )

        print(f"[Docent] ✅ AI response: {ai_response[:100]}...")

        # Generate TTS audio (only if enabled)
        audio_url = None
        audio_base64 = None

        if request.enable_tts:
            try:
                language_code = f"{request.language}-KR" if request.language == "ko" else "en-US"

                if request.prefer_url:
                    # Expo Go: Upload to Supabase and return URL
                    audio_url, audio_base64 = text_to_speech_url(
                        text=ai_response,
                        language_code=language_code,
                        upload_to_storage=True
                    )
                    if audio_url:
                        print(f"[Docent] ✅ TTS uploaded to Supabase: {audio_url}")
                    else:
                        print(f"[Docent] ⚠️  TTS upload to Supabase FAILED - using base64 fallback")
                else:
                    # Standalone: Return base64 (will use WebSocket for streaming)
                    audio_base64 = text_to_speech(
                        text=ai_response,
                        language_code=language_code
                    )
                    print(f"[Docent] ✅ TTS generated (base64)")

            except Exception as tts_error:
                print(f"[Docent] ⚠️  TTS generation failed: {tts_error}")
        else:
            print(f"[Docent] 🔇 TTS disabled - text only mode")

        # Log conversation to database (optional - don't fail if it errors)
        try:
            db = get_db()
            db.table("chat_logs").insert({
                "user_id": request.user_id,
                "landmark": request.landmark,
                "user_message": request.user_message or "",
                "ai_response": ai_response
            }).execute()
            print("[Docent] ✅ Chat log saved")
        except Exception as db_error:
            print(f"[Docent] ⚠️  Failed to save chat log: {db_error}")

        # Return response based on client preference
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
        print(f"[Docent] ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")


@router.post("/quiz")
async def get_quiz(landmark: str, language: str = "ko"):
    """
    Generate a quiz question about the landmark
    """
    try:
        quiz = generate_quiz(landmark, language)
        return quiz
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating quiz: {str(e)}")


@router.post("/tts")
async def generate_tts(request: TTSRequest):
    """
    Convert text to speech
    - If prefer_url=True (Expo Go): Returns audio_url from Supabase Storage
    - If prefer_url=False (Standalone): Returns base64 audio
    """
    try:
        audio_url = None
        audio_base64 = None

        if request.prefer_url:
            # Expo Go: Upload to Supabase and return URL
            audio_url, audio_base64 = text_to_speech_url(
                text=request.text,
                language_code=request.language_code,
                upload_to_storage=True
            )

            if not audio_url:
                raise HTTPException(status_code=503, detail="TTS service unavailable")

            return {
                "audio_url": audio_url,
                "audio": audio_base64,  # Fallback
                "text": request.text
            }
        else:
            # Standalone: Return base64
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
        raise HTTPException(status_code=500, detail=f"Error generating TTS: {str(e)}")


@router.get("/history/{user_id}")
async def get_chat_history(user_id: str, limit: int = 10):
    """
    Get user's chat history with the docent
    """
    try:
        db = get_db()
        result = db.table("chat_logs") \
            .select("*") \
            .eq("user_id", user_id) \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()

        return {
            "history": result.data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching history: {str(e)}")


# ===== WebSocket Endpoints =====

@router.websocket("/ws/tts")
async def websocket_tts(websocket: WebSocket):
    """
    WebSocket endpoint for TTS streaming
    Receives text, sends audio chunks in real-time

    Client sends: JSON with {"text": "...", "language_code": "ko-KR"}
    Server sends: Binary audio chunks followed by "DONE" message
    """
    await websocket.accept()
    print("[WebSocket] 🔌 Client connected to /ws/tts")

    try:
        # Receive text from client
        data = await websocket.receive_text()
        request_data = json.loads(data)

        text = request_data.get("text", "")
        language_code = request_data.get("language_code", "ko-KR")

        print(f"[WebSocket] 📨 Received: {text[:50]}... (lang: {language_code})")

        if not text:
            await websocket.send_text(json.dumps({"error": "No text provided"}))
            await websocket.close()
            return

        # Generate TTS audio
        audio_bytes = text_to_speech_bytes(
            text=text,
            language_code=language_code
        )

        if not audio_bytes:
            await websocket.send_text(json.dumps({"error": "TTS generation failed"}))
            await websocket.close()
            return

        print(f"[WebSocket] 🎵 Generated {len(audio_bytes)} bytes of audio")

        # Send audio in chunks for smooth streaming
        chunk_size = 4096
        total_chunks = (len(audio_bytes) + chunk_size - 1) // chunk_size

        for i in range(0, len(audio_bytes), chunk_size):
            chunk = audio_bytes[i:i + chunk_size]
            await websocket.send_bytes(chunk)
            await asyncio.sleep(0.01)  # Small delay for smooth streaming

            if (i // chunk_size) % 10 == 0:  # Log progress every 10 chunks
                progress = (i // chunk_size + 1) / total_chunks * 100
                print(f"[WebSocket] 📤 Streaming progress: {progress:.1f}%")

        # Send completion signal
        await websocket.send_text("DONE")
        print("[WebSocket] ✅ Streaming complete")

        await websocket.close()

    except WebSocketDisconnect:
        print("[WebSocket] 🔌 Client disconnected")
    except Exception as e:
        print(f"[WebSocket] ❌ Error: {e}")
        try:
            await websocket.send_text(json.dumps({"error": str(e)}))
            await websocket.close()
        except:
            pass


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket endpoint for AI chat with TTS streaming
    Receives user message, sends AI response text + audio chunks

    Client sends: JSON with {"user_id": "...", "landmark": "...", "user_message": "...", "language": "ko", "enable_tts": true}
    Server sends:
    1. Text message with AI response
    2. Binary audio chunks (only if enable_tts=true)
    3. "DONE" message
    """
    await websocket.accept()
    print("[WebSocket] 🔌 Client connected to /ws/chat")

    try:
        # Receive request from client
        data = await websocket.receive_text()
        request_data = json.loads(data)

        user_id = request_data.get("user_id", "")
        landmark = request_data.get("landmark", "")
        user_message = request_data.get("user_message")
        language = request_data.get("language", "ko")
        enable_tts = request_data.get("enable_tts", True)

        print(f"[WebSocket Chat] 📨 User: {user_id}, Landmark: {landmark}, TTS: {enable_tts}")

        # Generate AI response using Gemini
        ai_response = generate_docent_message(
            landmark=landmark,
            user_message=user_message,
            language=language
        )

        print(f"[WebSocket Chat] 🤖 AI: {ai_response[:100]}...")

        # Send AI text response first
        await websocket.send_text(json.dumps({
            "type": "text",
            "message": ai_response,
            "landmark": landmark
        }))

        # Log to database
        try:
            db = get_db()
            db.table("chat_logs").insert({
                "user_id": user_id,
                "landmark": landmark,
                "user_message": user_message or "",
                "ai_response": ai_response
            }).execute()
        except Exception as db_error:
            print(f"[WebSocket Chat] ⚠️  DB log failed: {db_error}")

        # Generate and stream TTS audio (only if enabled)
        if enable_tts:
            language_code = f"{language}-KR" if language == "ko" else "en-US"
            audio_bytes = text_to_speech_bytes(
                text=ai_response,
                language_code=language_code
            )

            if audio_bytes:
                # Send audio chunks
                chunk_size = 4096
                for i in range(0, len(audio_bytes), chunk_size):
                    chunk = audio_bytes[i:i + chunk_size]
                    await websocket.send_bytes(chunk)
                    await asyncio.sleep(0.01)

                print(f"[WebSocket Chat] 🎵 Streamed {len(audio_bytes)} bytes of audio")
        else:
            print(f"[WebSocket Chat] 🔇 TTS disabled - text only mode")

        # Send completion signal
        await websocket.send_text("DONE")
        print("[WebSocket Chat] ✅ Complete")

        await websocket.close()

    except WebSocketDisconnect:
        print("[WebSocket Chat] 🔌 Client disconnected")
    except Exception as e:
        print(f"[WebSocket Chat] ❌ Error: {e}")
        try:
            await websocket.send_text(json.dumps({"error": str(e)}))
            await websocket.close()
        except:
            pass
