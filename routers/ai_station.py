"""AI Station Router"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import base64
import uuid
import os
import logging
from datetime import datetime

from services.ai import generate_docent_message
from services.db import get_db, ensure_user_exists
from services.embedding import generate_text_embedding
from services.pinecone_store import search_similar_pinecone
from services.stt import speech_to_text_from_base64, speech_to_text
from services.tts import text_to_speech_url, text_to_speech
from services.storage import compress_and_upload_image
from services.auth_deps import get_current_user_id

logger = logging.getLogger(__name__)
router = APIRouter()


class ExploreRAGChatRequest(BaseModel):
    user_message: str
    language: str = "en"
    prefer_url: bool = False
    enable_tts: bool = True
    chat_session_id: Optional[str] = None


class QuestRAGChatRequest(BaseModel):
    quest_id: int
    user_message: str
    landmark: Optional[str] = None
    language: str = "en"
    prefer_url: bool = False
    enable_tts: bool = True
    chat_session_id: Optional[str] = None


class QuestVLMChatRequest(BaseModel):
    quest_id: int
    image: str
    user_message: Optional[str] = None
    language: str = "en"
    prefer_url: bool = False
    enable_tts: bool = True
    chat_session_id: Optional[str] = None


class STTTTSRequest(BaseModel):
    audio: str
    language_code: str = "en-US"
    prefer_url: bool = False


class RouteRecommendRequest(BaseModel):
    preferences: dict
    must_visit_place_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    start_latitude: Optional[float] = None
    start_longitude: Optional[float] = None
    radius_km: Optional[float] = None
    image: Optional[str] = None


def format_time_ago(created_at_str: str) -> str:
    try:
        from datetime import datetime, timezone, timedelta
        
        if isinstance(created_at_str, str):
            if 'T' in created_at_str:
                dt_str = created_at_str.replace('Z', '+00:00')
                if '+' in dt_str or dt_str.endswith('+00:00'):
                    dt = datetime.fromisoformat(dt_str)
                else:
                    dt = datetime.fromisoformat(dt_str)
                    dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = datetime.fromisoformat(created_at_str)
                dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = created_at_str
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        
        kst_offset = timedelta(hours=9)
        dt_kst = dt.astimezone(timezone(kst_offset))
        
        now = datetime.now(timezone(kst_offset))
        diff = now - dt_kst
        
        if diff.total_seconds() < 3600:
            minutes = int(diff.total_seconds() / 60)
            if minutes < 1:
                return "Just now"
            return f"{minutes} minutes ago"
        
        if diff.total_seconds() < 86400:
            hours = int(diff.total_seconds() / 3600)
            return f"{hours} hours ago"
        
        return dt_kst.strftime("%m/%d")
    
    except Exception as e:
        logger.warning(f"Time formatting error: {e}")
        return ""


def fetch_quest_context(quest_id: int, db=None) -> Dict[str, Any]:
    db = db or get_db()
    quest_result = db.table("quests").select("*, places(*)").eq("id", quest_id).single().execute()
    if not quest_result.data:
        raise HTTPException(status_code=404, detail="Quest not found")

    quest = dict(quest_result.data)
    place = quest.pop("places", None)
    if isinstance(place, list) and place:
        place = place[0]
    if place:
        quest["place"] = place
    return quest


def build_quest_context_block(quest: Dict[str, Any]) -> str:
    place = quest.get("place") or {}
    lines = [
        f"Quest Place: {quest.get('name') or place.get('name', '')}",
    ]
    if place.get("address"):
        lines.append(f"Address: {place['address']}")
    if place.get("district"):
        lines.append(f"District: {place['district']}")
    if place.get("category") or quest.get("category"):
        lines.append(f"Category: {quest.get('category') or place.get('category')}")
    if quest.get("reward_point"):
        lines.append(f"Reward Points: {quest['reward_point']} points")
    if quest.get("description"):
        lines.append(f"Place Description: {quest['description']}")
    elif place.get("description"):
        lines.append(f"Place Description: {place['description']}")
    return "\n".join(lines)


@router.get("/chat-list")
async def get_chat_list(
    limit: int = Query(20),
    mode: Optional[str] = Query(None),
    function_type: Optional[str] = Query(None),
    user_id: str = Depends(get_current_user_id)
):
    try:
        db = get_db()

        query = db.table("chat_logs").select("*").eq("user_id", user_id)

        if mode and function_type:
            query = query.eq("mode", mode).eq("function_type", function_type)

        elif mode:
            query = query.eq("mode", mode)

            if mode == "quest":
                query = query.in_("function_type", ["rag_chat", "vlm_chat"])
            elif mode == "explore":
                query = query.in_("function_type", ["rag_chat", "route_recommend"])

        elif function_type:
            query = query.eq("function_type", function_type)

            if function_type == "route_recommend":
                query = query.eq("mode", "explore")

        else:
            query = query.eq("mode", "explore").eq("function_type", "rag_chat")

        result = query.order("created_at", desc=True).limit(limit * 10).execute()

        sessions = {}
        vlm_count = 0
        rag_count = 0
        route_count = 0

        for chat in result.data:
            ft = chat.get("function_type")
            if ft == "vlm_chat": vlm_count += 1
            elif ft == "route_recommend": route_count += 1
            else: rag_count += 1

            session_id = chat.get("chat_session_id")
            if not session_id:
                continue

            if session_id not in sessions:
                title = chat.get("title") or (chat.get("user_message") or "")[:50]

                sessions[session_id] = {
                    "session_id": session_id,
                    "function_type": ft,
                    "mode": chat.get("mode"),
                    "title": title,
                    "is_read_only": chat.get("is_read_only", False),
                    "created_at": chat.get("created_at"),
                    "updated_at": chat.get("created_at"),
                    "time_ago": format_time_ago(chat.get("created_at")),
                    "chats": []
                }

            sessions[session_id]["chats"].append({
                "id": chat.get("id"),
                "user_message": chat.get("user_message"),
                "ai_response": chat.get("ai_response"),
                "image_url": chat.get("image_url"),
                "quest_step": chat.get("quest_step"),
                "options": chat.get("options"),
                "selected_districts": chat.get("selected_districts"),
                "selected_theme": chat.get("selected_theme"),
                "include_cart": chat.get("include_cart"),
                "prompt_step_text": chat.get("prompt_step_text"),
                "created_at": chat.get("created_at"),
            })

            if chat.get("created_at") > sessions[session_id]["updated_at"]:
                sessions[session_id]["updated_at"] = chat.get("created_at")
                sessions[session_id]["time_ago"] = format_time_ago(chat.get("created_at"))

        session_list = sorted(
            sessions.values(),
            key=lambda x: x["updated_at"],
            reverse=True
        )[:limit]

        return {
            "success": True,
            "sessions": session_list,
            "count": len(session_list)
        }

    except Exception as e:
        logger.error(f"Chat list error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching chat list: {str(e)}")


@router.get("/chat-session/{session_id}")
async def get_chat_session(session_id: str, user_id: str = Depends(get_current_user_id)):
    try:
        db = get_db()
        
        result = db.table("chat_logs").select("*").eq("chat_session_id", session_id).eq("user_id", user_id).order("created_at", asc=True).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        first_chat = result.data[0]
        session_info = {
            "session_id": session_id,
            "function_type": first_chat.get("function_type", "rag_chat"),
            "mode": first_chat.get("mode", "explore"),
            "title": first_chat.get("title", ""),
            "is_read_only": first_chat.get("is_read_only", False),
            "created_at": first_chat.get("created_at")
        }
        
        chats = []
        for chat in result.data:
            chat_data = {
                "id": chat.get("id"),
                "user_message": chat.get("user_message"),
                "ai_response": chat.get("ai_response"),
                "image_url": chat.get("image_url"),
                "created_at": chat.get("created_at")
            }
            
            if chat.get("function_type") == "route_recommend":
                chat_data.update({
                    "title": chat.get("title"),
                    "selected_theme": chat.get("selected_theme"),
                    "selected_districts": chat.get("selected_districts"),
                    "include_cart": chat.get("include_cart"),
                    "quest_step": chat.get("quest_step"),
                    "prompt_step_text": chat.get("prompt_step_text"),
                    "options": chat.get("options")
                })
            
            chats.append(chat_data)
        
        logger.info(f"Retrieved {len(chats)} chats for session: {session_id}")
        
        return {
            "success": True,
            "session": session_info,
            "chats": chats,
            "count": len(chats)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat session error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/explore/rag-chat")
async def explore_rag_chat(request: ExploreRAGChatRequest, user_id: str = Depends(get_current_user_id)):
    try:
        logger.info(f"Explore RAG chat: {user_id}")
        
        session_id = request.chat_session_id
        if not session_id:
            session_id = str(uuid.uuid4())
        
        text_embedding = generate_text_embedding(request.user_message)
        
        if not text_embedding:
            logger.warning("Failed to generate text embedding, falling back to DB search")
            db = get_db()
            places_result = db.rpc(
                "search_places_by_rag_text",
                {
                    "search_query": request.user_message,
                    "limit_count": 3
                }
            ).execute()
            
            context = ""
            detected_place_name = None
            if places_result.data:
                place_names = [p.get("name", "") for p in places_result.data[:3]]
                if place_names:
                    detected_place_name = place_names[0]
                context = f"관련 장소: {', '.join(place_names)}\n\n"
        else:
            from services.pinecone_store import search_text_embeddings
            
            similar_places = search_text_embeddings(
                text_embedding=text_embedding,
                match_threshold=0.65,
                match_count=5
            )
            
            context_parts = []
            detected_place_name = None
            if similar_places:
                context_parts.append("Related Places Information (RAG Search Results):")
                for idx, sp in enumerate(similar_places[:3], 1):
                    place = sp.get("place")
                    rag_text = sp.get("rag_text", "")
                    similarity = sp.get("similarity", 0.0)
                    
                    if place:
                        if idx == 1 and place.get("name"):
                            detected_place_name = place['name']
                        
                        place_info = []
                        if place.get("name"):
                            place_info.append(f"Name: {place['name']}")
                        if place.get("category"):
                            place_info.append(f"Category: {place['category']}")
                        if place.get("address"):
                            place_info.append(f"Address: {place['address']}")
                        if place.get("description"):
                            desc = place['description'][:200] + "..." if len(place['description']) > 200 else place['description']
                            place_info.append(f"Description: {desc}")
                        
                        if rag_text:
                            rag_preview = rag_text[:300] + "..." if len(rag_text) > 300 else rag_text
                            place_info.append(f"Details: {rag_preview}")
                        
                        context_parts.append(f"\n{idx}. {' | '.join(place_info)}")
                        if similarity > 0:
                            context_parts.append(f"   (Relevance: {similarity:.2f})")
                
                context_parts.append("")
                context = "\n".join(context_parts)
            else:
                db = get_db()
                places_result = db.rpc(
                    "search_places_by_rag_text",
                    {
                        "search_query": request.user_message,
                        "limit_count": 3
                    }
                ).execute()
                
                if places_result.data:
                    place_names = [p.get("name", "") for p in places_result.data[:3]]
                    if place_names:
                        detected_place_name = place_names[0]
                    context = f"Related Places: {', '.join(place_names)}\n\n"
                else:
                    context = ""
        
        chat_history = ""
        if session_id:
            try:
                db = get_db()
                history_result = db.table("chat_logs") \
                    .select("user_message, ai_response") \
                    .eq("chat_session_id", session_id) \
                    .eq("user_id", user_id) \
                    .order("created_at", desc=True) \
                    .limit(3) \
                    .execute()
                
                if history_result.data and len(history_result.data) > 0:
                    history_parts = ["Previous Conversation:"]
                    for chat in reversed(history_result.data):
                        if chat.get("user_message"):
                            history_parts.append(f"User: {chat['user_message']}")
                        if chat.get("ai_response"):
                            history_parts.append(f"AI: {chat['ai_response'][:150]}...")
                    history_parts.append("")
                    chat_history = "\n".join(history_parts)
            except Exception as hist_error:
                logger.warning(f"Failed to load chat history: {hist_error}")
        
        landmark_name = detected_place_name if detected_place_name else "Seoul Travel"
        
        full_prompt = f"""{context}{chat_history}Question: {request.user_message}

Please provide a friendly and helpful response based on the above information."""
        
        ai_response = generate_docent_message(
            landmark=landmark_name,
            user_message=full_prompt,
            language="en"
        )
        
        audio_url = None
        audio_base64 = None
        
        if request.enable_tts:
            try:
                language_code = "en-US"
                
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
            existing_session = db.table("chat_logs").select("id").eq("chat_session_id", session_id).limit(1).execute()
            is_first_message = not existing_session.data or len(existing_session.data) == 0
            
            title = None
            if is_first_message:
                title = request.user_message[:50]
            
            db.table("chat_logs").insert({
                "user_id": user_id,
                "user_message": request.user_message,
                "ai_response": ai_response,
                "mode": "explore",
                "function_type": "rag_chat",
                "chat_session_id": session_id,
                "title": title,
                "is_read_only": False
            }).execute()
        except Exception as db_error:
            logger.warning(f"Failed to save chat log: {db_error}")
        
        response = {
            "success": True,
            "message": ai_response,
            "session_id": session_id
        }
        
        if request.prefer_url and audio_url:
            response["audio_url"] = audio_url
        elif audio_base64:
            response["audio"] = audio_base64
        
        return response
    
    except Exception as e:
        logger.error(f"Explore RAG chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/quest/rag-chat")
async def quest_rag_chat(request: QuestRAGChatRequest, user_id: str = Depends(get_current_user_id)):
    try:
        if not request.quest_id:
            raise HTTPException(status_code=400, detail="quest_id is required for quest chat")

        logger.info(f"Quest RAG chat: user={user_id}, quest={request.quest_id}")
        db = get_db()
        ensure_user_exists(user_id)
        quest = fetch_quest_context(request.quest_id, db=db)

        session_id = request.chat_session_id or str(uuid.uuid4())

        landmark = quest.get("name") or quest.get("title") or request.landmark or "Quest Place"
        context_block = build_quest_context_block(quest)
        
        user_prompt = f"""The following is information about the quest place the user is currently working on:
{context_block}

Please answer the following question based on the above information.
Question: {request.user_message}"""
        
        ai_response = generate_docent_message(
            landmark=landmark,
            user_message=user_prompt,
            language="en"
        )
        
        audio_url = None
        audio_base64 = None
        
        if request.enable_tts:
            try:
                language_code = "en-US"
                
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
            existing_session = db.table("chat_logs").select("id").eq("chat_session_id", session_id).limit(1).execute()
            is_first_message = not existing_session.data
            title_value = quest.get("name") or quest.get("title") or landmark
            
            db.table("chat_logs").insert({
                "user_id": user_id,
                "user_message": request.user_message,
                "ai_response": ai_response,
                "mode": "quest",
                "function_type": "rag_chat",
                "chat_session_id": session_id,
                "title": title_value if is_first_message else None,
                "landmark": landmark,
                "is_read_only": True
            }).execute()
        except Exception as db_error:
            logger.warning(f"Failed to save quest chat log: {db_error}")
        
        response = {
            "success": True,
            "message": ai_response,
            "landmark": landmark,
            "session_id": session_id,
            "quest_id": request.quest_id
        }
        
        if request.prefer_url and audio_url:
            response["audio_url"] = audio_url
        elif audio_base64:
            response["audio"] = audio_base64
        
        return response
    
    except Exception as e:
        logger.error(f"Quest RAG chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/quest/vlm-chat")
async def quest_vlm_chat(request: QuestVLMChatRequest, user_id: str = Depends(get_current_user_id)):
    try:
        if not request.quest_id:
            raise HTTPException(status_code=400, detail="quest_id is required for quest VLM chat")

        logger.info(f"Quest VLM chat: user={user_id}, quest={request.quest_id}")
        db = get_db()
        ensure_user_exists(user_id)
        
        session_id = request.chat_session_id or str(uuid.uuid4())
        quest = fetch_quest_context(request.quest_id, db=db)
        
        try:
            image_bytes = base64.b64decode(request.image)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid base64 image: {str(e)}")
        
        image_url = compress_and_upload_image(
            image_bytes=image_bytes,
            max_size=1920,
            quality=85
        )
        
        from services.vlm import analyze_place_image, extract_place_info_from_vlm_response, calculate_confidence_score
        from services.db import search_places_by_radius, get_place_by_name, save_vlm_log
        from services.embedding import generate_image_embedding, hash_image
        from services.optimized_search import search_with_gps_filter
        
        nearby_places = []
        
        vlm_response = analyze_place_image(
            image_bytes=image_bytes,
            nearby_places=nearby_places,
            language="en",
            quest_context=quest
        )
        
        if not vlm_response:
            raise HTTPException(status_code=503, detail="VLM service unavailable")
        
        place_info = extract_place_info_from_vlm_response(vlm_response)
        matched_place = None
        
        quest_place = quest.get("place") or {}
        quest_place_id = quest.get("place_id") or (quest_place.get("id") if quest_place else None)
        
        if place_info.get("place_name"):
            candidate_place = get_place_by_name(place_info["place_name"], fuzzy=True)
            
            if candidate_place:
                candidate_place_id = candidate_place.get("id")
                if quest_place_id and candidate_place_id == quest_place_id:
                    matched_place = candidate_place
                    logger.info(f"Matched place verified: {candidate_place.get('name')} (quest place_id: {quest_place_id})")
                else:
                    logger.warning(f"Matched place {candidate_place.get('name')} (id: {candidate_place_id}) does not match quest place_id: {quest_place_id}")
                    if quest_place_id:
                        from services.db import get_place_by_id
                        matched_place = get_place_by_id(quest_place_id)
                        if matched_place:
                            logger.info(f"Using quest's actual place: {matched_place.get('name')}")
        
        if not matched_place and quest_place_id:
            from services.db import get_place_by_id
            matched_place = get_place_by_id(quest_place_id)
            if matched_place:
                logger.info(f"Using quest's actual place (no VLM match): {matched_place.get('name')}")
        
        final_description = vlm_response
        if matched_place:
            from services.ai import generate_docent_message
            enhancement_prompt = f"""
VLM Analysis Result:
{vlm_response}

Place Information:
- Name: {matched_place.get('name')}
- Category: {matched_place.get('category')}
- Description: {matched_place.get('description')}

Based on the above information, please introduce this place in a friendly and engaging way in 3-4 sentences, like an AR docent.
"""
            try:
                final_description = generate_docent_message(
                    landmark=matched_place.get('name', 'This place'),
                    user_message=enhancement_prompt,
                    language="en"
                )
            except Exception as e:
                logger.warning(f"Description enhancement failed: {e}")
        
        ai_response = final_description
        quest_context = build_quest_context_block(quest)
        ai_response = f"""{ai_response}

Current Quest Reference Information:
{quest_context}"""
        
        audio_url = None
        audio_base64 = None
        
        if request.enable_tts:
            try:
                language_code = "en-US"
                
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
            logger.info("Saving VLM log to vlm_logs...")
            image_hash = hash_image(image_bytes)
            save_vlm_log(
                user_id=user_id,
                image_url=image_url,
                latitude=None,
                longitude=None,
                vlm_response=vlm_response,
                final_description=final_description,
                matched_place_id=matched_place.get("id") if matched_place else None,
                image_hash=image_hash
            )
            logger.info("VLM log saved to vlm_logs")
        except Exception as vlm_log_error:
            logger.error(f"Failed to save VLM log: {vlm_log_error}", exc_info=True)
        
        try:
            logger.info(f"Saving VLM chat to chat_logs (session: {session_id})...")
            
            if not image_url:
                logger.error("Image URL is empty - upload may have failed!")
                raise HTTPException(status_code=500, detail="Image upload failed: url is empty")
            
            logger.info(f"Image URL: {image_url}")
            
            existing_session = db.table("chat_logs").select("id").eq("chat_session_id", session_id).limit(1).execute()
            is_first_message = not existing_session.data
            title_value = quest.get("name") or quest.get("title")
            
            chat_data = {
                "user_id": user_id,
                "user_message": request.user_message or "이미지 기반 질문",
                "ai_response": ai_response,
                "mode": "quest",
                "function_type": "vlm_chat",
                "chat_session_id": session_id,
                "title": title_value if is_first_message else None,
                "landmark": title_value,
                "image_url": image_url,
                "is_read_only": True
            }
            logger.info(f"Chat data to save: mode={chat_data['mode']}, function_type={chat_data['function_type']}, session={session_id}, has_image={bool(image_url)}")
            
            result = db.table("chat_logs").insert(chat_data).execute()
            logger.info(f"VLM chat saved to chat_logs (id: {result.data[0]['id'] if result.data else 'unknown'})")
        except Exception as db_error:
            logger.error(f"Failed to save quest VLM chat log: {db_error}", exc_info=True)
            raise
        
        response = {
            "success": True,
            "message": ai_response,
            "place": matched_place,
            "image_url": image_url,
            "session_id": session_id,
            "quest_id": request.quest_id
        }
        
        if request.prefer_url and audio_url:
            response["audio_url"] = audio_url
        elif audio_base64:
            response["audio"] = audio_base64
        
        return response
    
    except Exception as e:
        logger.error(f"Quest VLM chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/stt-tts")
async def stt_and_tts(request: STTTTSRequest, user_id: str = Depends(get_current_user_id)):
    try:
        logger.info(f"STT+TTS request: {user_id}")
        
        transcribed_text = speech_to_text_from_base64(
            audio_base64=request.audio,
            language_code=request.language_code
        )
        
        if not transcribed_text:
            raise HTTPException(status_code=400, detail="STT transcription failed")
        
        audio_url = None
        audio_base64 = None
        
        if request.prefer_url:
            audio_url, audio_base64 = text_to_speech_url(
                text=transcribed_text,
                language_code=request.language_code,
                upload_to_storage=True
            )
        else:
            audio_base64 = text_to_speech(
                text=transcribed_text,
                language_code=request.language_code
            )
        
        if not audio_base64:
            raise HTTPException(status_code=500, detail="TTS generation failed")
        
        return {
            "success": True,
            "transcribed_text": transcribed_text,
            "audio_url": audio_url,
            "audio": audio_base64
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"STT+TTS error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/route-recommend")
async def recommend_route(request: RouteRecommendRequest, user_id: str = Depends(get_current_user_id)):
    try:
        logger.info(f"Route recommend: {user_id}, radius_km={request.radius_km}")
        
        db = get_db()
        
        must_visit_quest = None
        if request.must_visit_place_id:
            place_result = db.table("places").select("*, quests(*)").eq("id", request.must_visit_place_id).execute()
            if place_result.data and len(place_result.data) > 0:
                place = place_result.data[0]
                quests = place.get("quests", [])
                if quests and len(quests) > 0:
                    must_visit_quest = dict(quests[0])
                    must_visit_quest["district"] = place.get("district")
                    must_visit_quest["place_image_url"] = place.get("image_url")
        
        import math
        
        preferences = request.preferences or {}
        preferred_categories = []
        
        if preferences.get("category"):
            category = preferences["category"]
            if isinstance(category, dict):
                cat_name = category.get("name")
                if cat_name:
                    preferred_categories.append(cat_name)
            elif isinstance(category, str):
                preferred_categories.append(category)
        
        if preferences.get("theme"):
            theme = preferences["theme"]
            if isinstance(theme, list):
                for t in theme:
                    if isinstance(t, dict):
                        preferred_categories.append(t.get("name"))
                    elif isinstance(t, str):
                        preferred_categories.append(t)
            elif isinstance(theme, dict):
                cat_name = theme.get("name")
                if cat_name:
                    preferred_categories.append(cat_name)
            elif isinstance(theme, str):
                preferred_categories.append(theme)
        
        preferred_categories = list(set(preferred_categories))
        
        completed_quests_result = db.table("user_quests").select("quest_id, quests(category)").eq("user_id", user_id).eq("status", "completed").execute()
        completed_categories = set()
        completed_quest_ids = set()
        
        def normalize_category(category: str) -> str:
            if not category:
                return ""
            
            category_lower = category.lower().strip()
            
            category_map = {
                # History 관련
                "역사": "history",
                "역사유적": "history",
                "문화재": "history",
                "궁궐": "history",
                "유적지": "history",
                "historical": "history",
                # Attractions 관련
                "관광지": "attractions",
                "명소": "attractions",
                "전망대": "attractions",
                "landmark": "attractions",
                "tourist": "attractions",
                # Culture 관련
                "문화": "culture",
                "문화마을": "culture",
                "한옥마을": "culture",
                "전통마을": "culture",
                "traditional": "culture",
                # Religion 관련
                "종교": "religion",
                "종교시설": "religion",
                "사찰": "religion",
                "성당": "religion",
                "교회": "religion",
                "temple": "religion",
                # Park 관련
                "공원": "park",
                "광장": "park",
                "야외공간": "park",
                "square": "park",
                "outdoor": "park",
            }
            
            if category_lower in category_map:
                return category_map[category_lower]
            
            return category_lower
        
        if completed_quests_result.data:
            for uq in completed_quests_result.data:
                completed_quest_ids.add(uq.get("quest_id"))
                quest_data = uq.get("quests")
                if quest_data:
                    if isinstance(quest_data, list) and len(quest_data) > 0:
                        category = quest_data[0].get("category")
                    elif isinstance(quest_data, dict):
                        category = quest_data.get("category")
                    else:
                        category = None
                    if category:
                        normalized = normalize_category(category)
                        if normalized:
                            completed_categories.add(normalized)
        
        if request.radius_km is not None:
            search_radius = float(request.radius_km)
        else:
            search_radius = 15.0
        
        logger.info(f"Using search_radius: {search_radius}km (request.radius_km={request.radius_km})")
        
        if request.latitude and request.longitude:
            from routers.recommend import get_nearby_quests_route
            nearby_result = await get_nearby_quests_route(
                latitude=request.latitude,
                longitude=request.longitude,
                radius_km=search_radius,
                limit=50
            )
            candidate_quests = nearby_result.get("quests", [])
        else:
            quests_result = db.table("quests").select("*, places(*)").eq("is_active", True).limit(50).execute()
            candidate_quests = []
            for q in quests_result.data:
                quest = dict(q)
                place = quest.get("places")
                if place:
                    if isinstance(place, list) and len(place) > 0:
                        place = place[0]
                    quest["district"] = place.get("district") if isinstance(place, dict) else None
                    quest["place_image_url"] = place.get("image_url") if isinstance(place, dict) else None
                candidate_quests.append(quest)
        
        def calculate_distance_score(lat1: float, lon1: float, lat2: float, lon2: float, max_radius: float = None) -> float:
            if not (lat1 and lon1 and lat2 and lon2):
                return 0.5
            
            radius_limit = max_radius if max_radius is not None else search_radius
            
            R = 6371
            lat1_rad = math.radians(lat1)
            lat2_rad = math.radians(lat2)
            delta_lat = math.radians(lat2 - lat1)
            delta_lon = math.radians(lon2 - lon1)
            
            a = (math.sin(delta_lat / 2) ** 2 + 
                 math.cos(lat1_rad) * math.cos(lat2_rad) * 
                 math.sin(delta_lon / 2) ** 2)
            c = 2 * math.asin(math.sqrt(a))
            distance_km = R * c
            
            if distance_km <= radius_limit:
                normalized_distance = distance_km / radius_limit
                return max(0.2, 1.0 - math.sqrt(normalized_distance))
            else:
                return 0.1
        
        def calculate_single_category_score(quest_category: str, preferred: str) -> float:
            if not preferred or not quest_category:
                return 0.0
            
            quest_cat_normalized = normalize_category(quest_category)
            preferred_cat_normalized = normalize_category(preferred)
            
            if not quest_cat_normalized or not preferred_cat_normalized:
                return 0.0
            
            if quest_cat_normalized.lower() == preferred_cat_normalized.lower():
                return 1.0
            
            similar_groups = [
                {"history", "historical"},
                {"attractions", "landmark", "tourist"},
                {"culture", "traditional"},
                {"religion", "temple"},
                {"park", "square", "outdoor"},
            ]
            
            for group in similar_groups:
                if quest_cat_normalized.lower() in group and \
                   preferred_cat_normalized.lower() in group:
                    return 0.7
            
            return 0.3
        
        def calculate_category_score(quest_category: str, preferred_categories: List[str]) -> float:
            if not preferred_categories or not quest_category:
                return 0.5
            
            max_score = 0.0
            for preferred in preferred_categories:
                score = calculate_single_category_score(quest_category, preferred)
                max_score = max(max_score, score)
            
            return max_score if max_score > 0 else 0.5
        
        def calculate_popularity_score(completion_count: int) -> float:
            return min(1.0, completion_count / 100.0)
        
        def calculate_diversity_score(quest_category: str, completed_categories: set) -> float:
            if not completed_categories:
                return 1.0
            
            quest_cat_normalized = normalize_category(quest_category)
            if not quest_cat_normalized:
                return 0.5
            
            if quest_cat_normalized.lower() in {cat.lower() for cat in completed_categories}:
                return 0.3
            else:
                return 1.0
        
        def calculate_reward_score(reward_point: int) -> float:
            return min(1.0, reward_point / 200.0)
        
        image_quest_scores = {}
        if request.image:
            try:
                import base64
                from services.vlm import analyze_place_image, extract_place_info_from_vlm_response
                from services.quest_rag import search_quests_by_rag_text
                from services.embedding import generate_text_embedding
                
                image_bytes = base64.b64decode(request.image)
                
                vlm_response = analyze_place_image(
                    image_bytes=image_bytes,
                    nearby_places=[],
                    language="en",
                    quest_context=None
                )
                
                if vlm_response:
                    place_info = extract_place_info_from_vlm_response(vlm_response)
                    
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
                            related_quests = search_quests_by_rag_text(
                                text_embedding=text_embedding,
                                match_threshold=0.6,
                                match_count=20,
                                latitude=request.latitude,
                                longitude=request.longitude,
                                radius_km=request.radius_km or 15.0
                            )
                            
                            for rag_result in related_quests:
                                quest_id = rag_result.get("quest", {}).get("id")
                                if quest_id:
                                    image_quest_scores[quest_id] = rag_result.get("similarity", 0.0) * 0.3
                            
                            logger.info(f"Image-based recommendation found {len(image_quest_scores)} quests")
            except Exception as e:
                logger.warning(f"Image-based recommendation failed: {e}")
        
        rag_preference_scores = {}
        if preferences.get("text_query"):
            try:
                from services.quest_rag import search_quests_by_rag_text
                from services.embedding import generate_text_embedding
                
                text_query = preferences["text_query"]
                text_embedding = generate_text_embedding(text_query)
                
                if text_embedding:
                    rag_quests = search_quests_by_rag_text(
                        text_embedding=text_embedding,
                        match_threshold=0.6,
                        match_count=20,
                        latitude=request.latitude,
                        longitude=request.longitude,
                        radius_km=request.radius_km or 15.0
                    )
                    
                    for rag_result in rag_quests:
                        quest_id = rag_result.get("quest", {}).get("id")
                        if quest_id:
                            rag_preference_scores[quest_id] = rag_result.get("similarity", 0.0) * 0.2
                    
                    logger.info(f"RAG preference extraction found {len(rag_preference_scores)} quests")
            except Exception as e:
                logger.warning(f"RAG preference extraction failed: {e}")
        
        scored_quests = []
        for quest in candidate_quests:
            quest_id = quest.get("id")

            if quest_id in completed_quest_ids:
                continue

            if must_visit_quest and quest_id == must_visit_quest.get("id"):
                continue

            quest_category = quest.get("category", "")
            quest_lat = quest.get("latitude")
            quest_lon = quest.get("longitude")
            completion_count = quest.get("completion_count", 0)
            reward_point = quest.get("reward_point", 100)
            
            category_score = calculate_category_score(quest_category, preferred_categories)
            distance_score = calculate_distance_score(
                request.latitude or 37.5665, 
                request.longitude or 126.9780,
                float(quest_lat) if quest_lat else None,
                float(quest_lon) if quest_lon else None,
                max_radius=search_radius
            ) if request.latitude and request.longitude else 0.5
            popularity_score = calculate_popularity_score(completion_count)
            diversity_score = calculate_diversity_score(quest_category, completed_categories)
            reward_score = calculate_reward_score(reward_point)
            
            weights = {
                "category": 0.35,
                "distance": 0.15,
                "diversity": 0.25,
                "popularity": 0.15,
                "reward": 0.1
            }
            
            final_score = (
                category_score * weights["category"] +
                distance_score * weights["distance"] +
                diversity_score * weights["diversity"] +
                popularity_score * weights["popularity"] +
                reward_score * weights["reward"]
            )
            
            image_score = image_quest_scores.get(quest_id, 0.0)
            rag_score = rag_preference_scores.get(quest_id, 0.0)
            
            final_score_with_extras = final_score + image_score + rag_score
            
            quest["recommendation_score"] = round(final_score_with_extras, 3)
            quest["score_breakdown"] = {
                "category": round(category_score, 3),
                "distance": round(distance_score, 3),
                "diversity": round(diversity_score, 3),
                "popularity": round(popularity_score, 3),
                "reward": round(reward_score, 3),
                "image_match": round(image_score, 3) if image_score > 0 else None,
                "rag_match": round(rag_score, 3) if rag_score > 0 else None
            }
            
            scored_quests.append(quest)
        
        start_lat = request.start_latitude or request.latitude
        start_lon = request.start_longitude or request.longitude
        
        def is_night_view_place(quest: dict) -> bool:
            place = quest.get("places")
            if isinstance(place, list) and len(place) > 0:
                place = place[0]
            
            if not isinstance(place, dict):
                return False
            
            metadata = place.get("metadata", {})
            if isinstance(metadata, dict):
                metadata_str = str(metadata).lower()
                if any(keyword in metadata_str for keyword in ["night_view", "night_scene", "night_viewing", "야경", "야경명소"]):
                    return True
            
            description = (quest.get("description") or place.get("description") or "").lower()
            if any(keyword in description for keyword in ["night view", "night scene", "야경", "야경명소", "야경 포인트"]):
                return True
            
            name = (quest.get("name") or place.get("name") or "").lower()
            if any(keyword in name for keyword in ["night view", "야경"]):
                return True
            
            return False
        
        night_view_quests = [q for q in scored_quests if is_night_view_place(q)]
        regular_quests = [q for q in scored_quests if not is_night_view_place(q)]
        
        if must_visit_quest:
            must_visit_quest_id = must_visit_quest.get("id")
            must_visit_in_scored = False
            for quest in regular_quests:
                if quest.get("id") == must_visit_quest_id:
                    must_visit_in_scored = True
                    break
            
            if not must_visit_in_scored:
                must_visit_quest["recommendation_score"] = 1.0
                regular_quests.append(must_visit_quest)
        
        if start_lat and start_lon:
            def calculate_distance_from_start(quest: dict) -> float:
                quest_lat = quest.get("latitude")
                quest_lon = quest.get("longitude")
                if not (quest_lat and quest_lon):
                    return float('inf')
                
                R = 6371
                lat1_rad = math.radians(start_lat)
                lat2_rad = math.radians(float(quest_lat))
                delta_lat = math.radians(float(quest_lat) - start_lat)
                delta_lon = math.radians(float(quest_lon) - start_lon)
                
                a = (math.sin(delta_lat / 2) ** 2 + 
                     math.cos(lat1_rad) * math.cos(lat2_rad) * 
                     math.sin(delta_lon / 2) ** 2)
                c = 2 * math.asin(math.sqrt(a))
                return R * c
            
            for quest in regular_quests:
                quest["distance_from_start"] = calculate_distance_from_start(quest)
            regular_quests.sort(key=lambda x: (
                x.get("distance_from_start", float('inf')) * 0.3 +
                (1.0 - x.get("recommendation_score", 0)) * 0.7
            ))
            
            for quest in night_view_quests:
                quest["distance_from_start"] = calculate_distance_from_start(quest)
            night_view_quests.sort(key=lambda x: (x.get("distance_from_start", float('inf')), -x.get("recommendation_score", 0)))
        else:
            regular_quests.sort(key=lambda x: x.get("recommendation_score", 0), reverse=True)
            night_view_quests.sort(key=lambda x: x.get("recommendation_score", 0), reverse=True)
        
        use_ai_recommendation = os.getenv("USE_AI_ROUTE_RECOMMENDATION", "true").lower() == "true"
        
        if use_ai_recommendation and len(scored_quests) >= 4:
            from services.ai import generate_route_recommendation
            
            ai_recommended = generate_route_recommendation(
                candidate_quests=scored_quests[:20],
                preferences=request.preferences,
                completed_quest_ids=completed_quest_ids,
                language="en"
            )
            
            if ai_recommended and len(ai_recommended) >= 4:
                ai_quests_with_place = []
                for quest in ai_recommended[:4]:
                    quest_id = quest.get("id")
                    place_id = quest.get("place_id")
                    
                    quest_with_place = None
                    for scored_quest in scored_quests:
                        if scored_quest.get("id") == quest_id:
                            quest_with_place = scored_quest
                            break
                    
                    if not quest_with_place:
                        quest_result = db.table("quests").select("*, places(*)").eq("id", quest_id).single().execute()
                        if quest_result.data:
                            quest_with_place = dict(quest_result.data)
                            place = quest_with_place.get("places")
                            if place:
                                if isinstance(place, list) and len(place) > 0:
                                    place = place[0]
                                quest_with_place["district"] = place.get("district") if isinstance(place, dict) else None
                                quest_with_place["place_image_url"] = place.get("image_url") if isinstance(place, dict) else None
                    
                    if quest_with_place:
                        ai_quests_with_place.append(quest_with_place)
                
                recommended_quests = ai_quests_with_place[:4]
                
                final_quests = []
                night_quest_in_list = None
                must_visit_quest_id = must_visit_quest.get("id") if must_visit_quest else None
                
                for quest in recommended_quests:
                    if is_night_view_place(quest):
                        night_quest_in_list = quest
                    else:
                        final_quests.append(quest)
                
                if must_visit_quest_id and not any(q.get("id") == must_visit_quest_id for q in final_quests):
                    for quest in regular_quests:
                        if quest.get("id") == must_visit_quest_id:
                            inserted = False
                            for i, q in enumerate(final_quests):
                                if q.get("distance_from_start", float('inf')) > quest.get("distance_from_start", float('inf')):
                                    final_quests.insert(i, quest)
                                    inserted = True
                                    break
                            if not inserted:
                                final_quests.append(quest)
                            break
                
                if night_quest_in_list:
                    if len(final_quests) < 4:
                        final_quests.append(night_quest_in_list)
                else:
                    for quest in regular_quests:
                        if len(final_quests) >= 4:
                            break
                        place_id = quest.get("place_id")
                        if any(rq.get("place_id") == place_id for rq in final_quests):
                            continue
                        final_quests.append(quest)
                
                if len(final_quests) < 4:
                    for quest in regular_quests:
                        if len(final_quests) >= 4:
                            break
                        place_id = quest.get("place_id")
                        if any(rq.get("place_id") == place_id for rq in final_quests):
                            continue
                        final_quests.append(quest)
                
                recommended_quests = final_quests[:4]
                logger.info("Using AI-based recommendation")
            else:
                recommended_quests = []
                must_visit_quest_id = must_visit_quest.get("id") if must_visit_quest else None
                remaining_count = 3
                
                if start_lat and start_lon and len(regular_quests) > remaining_count:
                    distance_zones = {
                        "near": [],
                        "mid": [],
                        "far": []
                    }
                    
                    for quest in regular_quests:
                        dist = quest.get("distance_from_start", float('inf'))
                        if dist == float('inf'):
                            continue
                        
                        zone_ratio = dist / search_radius if search_radius > 0 else 0
                        if zone_ratio <= 0.33:
                            distance_zones["near"].append(quest)
                        elif zone_ratio <= 0.66:
                            distance_zones["mid"].append(quest)
                        else:
                            distance_zones["far"].append(quest)
                    
                    zones_order = ["near", "mid", "far"]
                    zone_idx = 0
                    
                    while len(recommended_quests) < remaining_count:
                        zone_name = zones_order[zone_idx % len(zones_order)]
                        zone_quests = distance_zones[zone_name]
                        
                        if zone_quests:
                            for quest in zone_quests:
                                if len(recommended_quests) >= remaining_count:
                                    break
                                place_id = quest.get("place_id")
                                if any(rq.get("place_id") == place_id for rq in recommended_quests):
                                    continue
                                recommended_quests.append(quest)
                        
                        zone_idx += 1
                        if zone_idx >= len(zones_order) * 2:
                            break
                    
                    if len(recommended_quests) < remaining_count:
                        for quest in regular_quests:
                            if len(recommended_quests) >= remaining_count:
                                break
                            place_id = quest.get("place_id")
                            if any(rq.get("place_id") == place_id for rq in recommended_quests):
                                continue
                            recommended_quests.append(quest)
                else:
                    for quest in regular_quests[:remaining_count * 2]:
                        if len(recommended_quests) >= remaining_count:
                            break
                        place_id = quest.get("place_id")
                        if any(rq.get("place_id") == place_id for rq in recommended_quests):
                            continue
                        recommended_quests.append(quest)
                
                if night_view_quests and len(recommended_quests) < 4:
                    for night_quest in night_view_quests:
                        if len(recommended_quests) >= 4:
                            break
                        place_id = night_quest.get("place_id")
                        if any(rq.get("place_id") == place_id for rq in recommended_quests):
                            continue
                        recommended_quests.append(night_quest)
                        break
                
                if len(recommended_quests) < 4:
                    for quest in regular_quests:
                        if len(recommended_quests) >= 4:
                            break
                        place_id = quest.get("place_id")
                        if any(rq.get("place_id") == place_id for rq in recommended_quests):
                            continue
                        recommended_quests.append(quest)
                
                recommended_quests = recommended_quests[:4]
                logger.info("Using score-based recommendation (AI fallback)")
        else:
            recommended_quests = []
            must_visit_quest_id = must_visit_quest.get("id") if must_visit_quest else None
            remaining_count = 3
            
            if start_lat and start_lon and len(regular_quests) > remaining_count:
                distance_zones = {
                    "near": [],
                    "mid": [],
                    "far": []
                }
                
                for quest in regular_quests:
                    dist = quest.get("distance_from_start", float('inf'))
                    if dist == float('inf'):
                        continue
                    
                    zone_ratio = dist / search_radius if search_radius > 0 else 0
                    if zone_ratio <= 0.33:
                        distance_zones["near"].append(quest)
                    elif zone_ratio <= 0.66:
                        distance_zones["mid"].append(quest)
                    else:
                        distance_zones["far"].append(quest)
                
                zones_order = ["near", "mid", "far"]
                zone_idx = 0
                
                while len(recommended_quests) < remaining_count:
                    zone_name = zones_order[zone_idx % len(zones_order)]
                    zone_quests = distance_zones[zone_name]
                    
                    if zone_quests:
                        for quest in zone_quests:
                            if len(recommended_quests) >= remaining_count:
                                break
                            place_id = quest.get("place_id")
                            if any(rq.get("place_id") == place_id for rq in recommended_quests):
                                continue
                            recommended_quests.append(quest)
                    
                    zone_idx += 1
                    if zone_idx >= len(zones_order) * 2:
                        break
                
                if len(recommended_quests) < remaining_count:
                    for quest in regular_quests:
                        if len(recommended_quests) >= remaining_count:
                            break
                        place_id = quest.get("place_id")
                        if any(rq.get("place_id") == place_id for rq in recommended_quests):
                            continue
                        recommended_quests.append(quest)
            else:
                for quest in regular_quests[:remaining_count * 2]:
                    if len(recommended_quests) >= remaining_count:
                        break
                    place_id = quest.get("place_id")
                    if any(rq.get("place_id") == place_id for rq in recommended_quests):
                        continue
                    recommended_quests.append(quest)
            
            if night_view_quests and len(recommended_quests) < 4:
                for night_quest in night_view_quests:
                    if len(recommended_quests) >= 4:
                        break
                    place_id = night_quest.get("place_id")
                    if any(rq.get("place_id") == place_id for rq in recommended_quests):
                        continue
                    recommended_quests.append(night_quest)
                    break
            
            if len(recommended_quests) < 4:
                for quest in regular_quests:
                    if len(recommended_quests) >= 4:
                        break
                    place_id = quest.get("place_id")
                    if any(rq.get("place_id") == place_id for rq in recommended_quests):
                        continue
                    recommended_quests.append(quest)
            
            recommended_quests = recommended_quests[:4]
            logger.info("Using score-based recommendation")
        
        session_id = str(uuid.uuid4())
        
        theme = request.preferences.get("theme") or request.preferences.get("category") or "Seoul Travel"
        if isinstance(theme, list):
            if len(theme) > 0:
                if isinstance(theme[0], dict):
                    theme = theme[0].get("name", "Seoul Travel")
                else:
                    theme = str(theme[0])
            else:
                theme = "Seoul Travel"
        elif isinstance(theme, dict):
            theme = theme.get("name", "Seoul Travel")
        elif isinstance(theme, str):
            theme = theme
        else:
            theme = "Seoul Travel"
        
        try:
            quest_ids = [q.get("id") for q in recommended_quests]

            db.table("chat_logs").insert({
                "user_id": user_id,
                "user_message": f"Route recommendation request: {request.preferences}",
                "ai_response": f"Recommended {len(recommended_quests)} quests.",
                "mode": "explore",
                "function_type": "route_recommend",
                "chat_session_id": session_id,
                "title": theme,
                "is_read_only": True,
                "quest_step": 99,
                "prompt_step_text": "AI-recommended travel course results!",
                "options": {"quest_ids": quest_ids},
                "selected_theme": theme,
                "selected_districts": request.preferences.get("districts"),
                "include_cart": request.preferences.get("include_cart", False)
            }).execute()
            logger.info(f"Route recommend chat log saved (session: {session_id}, quest_ids: {quest_ids})")
        except Exception as db_error:
            logger.warning(f"Failed to save chat log: {db_error}")
        
        if recommended_quests:
            from services.location_tracking import log_route_recommendation
            quest_ids = [q.get("id") for q in recommended_quests if q.get("id")]
            if quest_ids:
                log_route_recommendation(
                    user_id=user_id,
                    recommended_quest_ids=quest_ids,
                    user_latitude=request.latitude,
                    user_longitude=request.longitude,
                    start_latitude=request.start_latitude,
                    start_longitude=request.start_longitude
                )
        
        logger.info(f"Recommended {len(recommended_quests)} quests")
        
        for quest in recommended_quests:
            quest["is_night_view"] = is_night_view_place(quest)
        
        return {
            "success": True,
            "quests": recommended_quests,
            "count": len(recommended_quests),
            "session_id": session_id
        }
    
    except Exception as e:
        logger.error(f"Route recommend error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
