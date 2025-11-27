"""AI Station Router - 채팅 리스트 및 통합 기능"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import base64
import uuid
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
    language: str = "ko"
    prefer_url: bool = False
    enable_tts: bool = True
    chat_session_id: Optional[str] = None


class QuestRAGChatRequest(BaseModel):
    quest_id: int
    user_message: str
    landmark: Optional[str] = None
    language: str = "ko"
    prefer_url: bool = False
    enable_tts: bool = True
    chat_session_id: Optional[str] = None


class QuestVLMChatRequest(BaseModel):
    quest_id: int
    image: str  # base64
    user_message: Optional[str] = None
    language: str = "ko"
    prefer_url: bool = False
    enable_tts: bool = True
    chat_session_id: Optional[str] = None


class STTTTSRequest(BaseModel):
    audio: str  # base64 encoded audio
    language_code: str = "ko-KR"
    prefer_url: bool = False


class RouteRecommendRequest(BaseModel):
    preferences: dict  # 사용자 취향 정보
    must_visit_place_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


def format_time_ago(created_at_str: str) -> str:
    """시간을 '몇분전' 또는 '몇월 며칠' 형식으로 변환"""
    try:
        from datetime import datetime, timezone, timedelta
        
        # 문자열을 datetime으로 변환
        if isinstance(created_at_str, str):
            # ISO 형식 문자열 파싱
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
        
        # UTC를 KST로 변환 (UTC+9)
        kst_offset = timedelta(hours=9)
        dt_kst = dt.astimezone(timezone(kst_offset))
        
        now = datetime.now(timezone(kst_offset))
        diff = now - dt_kst
        
        # 몇분전
        if diff.total_seconds() < 3600:  # 1시간 미만
            minutes = int(diff.total_seconds() / 60)
            if minutes < 1:
                return "방금"
            return f"{minutes}분전"
        
        # 몇시간전
        if diff.total_seconds() < 86400:  # 24시간 미만
            hours = int(diff.total_seconds() / 3600)
            return f"{hours}시간전"
        
        # 몇월 며칠
        return dt_kst.strftime("%m월 %d일")
    
    except Exception as e:
        logger.warning(f"Time formatting error: {e}")
        return ""


def fetch_quest_context(quest_id: int, db=None) -> Dict[str, Any]:
    """Fetch quest and associated place metadata for quest mode chat."""
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
    """Build structured context text for LLM prompts."""
    place = quest.get("place") or {}
    lines = [
        f"퀘스트 장소: {quest.get('name') or place.get('name', '')}",
    ]
    if place.get("address"):
        lines.append(f"주소: {place['address']}")
    if place.get("district"):
        lines.append(f"행정구역: {place['district']}")
    if place.get("category") or quest.get("category"):
        lines.append(f"카테고리: {quest.get('category') or place.get('category')}")
    if quest.get("reward_point"):
        lines.append(f"획득 포인트: {quest['reward_point']}점")
    if quest.get("description"):
        lines.append(f"장소 설명: {quest['description']}")
    elif place.get("description"):
        lines.append(f"장소 설명: {place['description']}")
    return "\n".join(lines)


@router.get("/chat-list")
async def get_chat_list(
    limit: int = Query(20),
    mode: Optional[str] = Query(None),
    function_type: Optional[str] = Query(None),
    user_id: str = Depends(get_current_user_id)
):
    """
    채팅 리스트 조회
    - mode: explore | quest
    - function_type:
        rag_chat, vlm_chat, route_recommend
    """
    try:
        db = get_db()

        # 기본 query
        query = db.table("chat_logs").select("*").eq("user_id", user_id)

        # 🔥 mode + function_type 조합 필터링
        if mode and function_type:
            # 둘 다 지정된 경우 정확히 필터
            query = query.eq("mode", mode).eq("function_type", function_type)

        elif mode:
            query = query.eq("mode", mode)

            # mode에 따른 function_type 제한
            if mode == "quest":
                # quest 모드에서는 rag_chat + vlm_chat만
                query = query.in_("function_type", ["rag_chat", "vlm_chat"])
            elif mode == "explore":
                # explore는 rag_chat + route
                query = query.in_("function_type", ["rag_chat", "route_recommend"])

        elif function_type:
            # function_type만 지정된 경우
            query = query.eq("function_type", function_type)

            # route_recommend는 explore 모드만 존재
            if function_type == "route_recommend":
                query = query.eq("mode", "explore")

        else:
            # 🔥 기본값: explore + rag_chat
            query = query.eq("mode", "explore").eq("function_type", "rag_chat")

        # 결과 가져오기
        result = query.order("created_at", desc=True).limit(limit * 10).execute()

        # 세션 그룹화
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

            # 새 세션 생성
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

            # 세션에 메시지 추가
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

            # 최신순 업데이트
            if chat.get("created_at") > sessions[session_id]["updated_at"]:
                sessions[session_id]["updated_at"] = chat.get("created_at")
                sessions[session_id]["time_ago"] = format_time_ago(chat.get("created_at"))

        # 정렬
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
    """
    특정 세션의 채팅 내역 조회
    사용자가 히스토리에서 세션을 클릭했을 때 전체 대화 내용을 반환
    """
    try:
        db = get_db()
        
        result = db.table("chat_logs").select("*").eq("chat_session_id", session_id).eq("user_id", user_id).order("created_at", asc=True).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # 세션 정보
        first_chat = result.data[0]
        session_info = {
            "session_id": session_id,
            "function_type": first_chat.get("function_type", "rag_chat"),
            "mode": first_chat.get("mode", "explore"),
            "title": first_chat.get("title", ""),
            "is_read_only": first_chat.get("is_read_only", False),
            "created_at": first_chat.get("created_at")
        }
        
        # 채팅 목록
        chats = []
        for chat in result.data:
            chat_data = {
                "id": chat.get("id"),
                "user_message": chat.get("user_message"),
                "ai_response": chat.get("ai_response"),
                "image_url": chat.get("image_url"),
                "created_at": chat.get("created_at")
            }
            
            # Plan Chat 전용 필드 추가
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
    """
    탐색 모드 - 일반 RAG 채팅 (텍스트만 저장)
    Pinecone에 저장된 장소 description을 RAG로 검색하여 답변 생성
    """
    try:
        logger.info(f"Explore RAG chat: {user_id}")
        
        # 세션 ID 생성 또는 기존 사용
        session_id = request.chat_session_id
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # 사용자 메시지를 임베딩하여 유사한 장소 검색
        text_embedding = generate_text_embedding(request.user_message)
        
        # Pinecone에서 유사한 장소 검색 (description 기반)
        # TODO: Pinecone에 place description 임베딩이 저장되어 있어야 함
        # 현재는 DB에서 직접 검색하는 방식으로 구현
        db = get_db()
        
        # RAG 검색: places 테이블의 metadata->>'rag_text'에서 검색
        places_result = db.rpc(
            "search_places_by_rag_text",
            {
                "search_query": request.user_message,
                "limit_count": 3
            }
        ).execute()
        
        context = ""
        if places_result.data:
            place_names = [p.get("name", "") for p in places_result.data[:3]]
            context = f"관련 장소: {', '.join(place_names)}\n\n"
        
        # AI 응답 생성
        ai_response = generate_docent_message(
            landmark="서울 여행지",
            user_message=f"{context}질문: {request.user_message}",
            language=request.language
        )
        
        # TTS 생성
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
        
        # 채팅 기록 저장 (텍스트만)
        # 첫 번째 질문인지 확인하여 제목 설정
        try:
            existing_session = db.table("chat_logs").select("id").eq("chat_session_id", session_id).limit(1).execute()
            is_first_message = not existing_session.data or len(existing_session.data) == 0
            
            title = None
            if is_first_message:
                title = request.user_message[:50]  # 첫 질문을 제목으로 사용
            
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
    """
    퀘스트 모드 - 일반 RAG 채팅 (이미지+텍스트 저장 가능)
    """
    try:
        if not request.quest_id:
            raise HTTPException(status_code=400, detail="quest_id is required for quest chat")

        logger.info(f"Quest RAG chat: user={user_id}, quest={request.quest_id}")
        db = get_db()
        ensure_user_exists(user_id)
        quest = fetch_quest_context(request.quest_id, db=db)

        session_id = request.chat_session_id or str(uuid.uuid4())

        landmark = quest.get("name") or quest.get("title") or request.landmark or "퀘스트 장소"
        context_block = build_quest_context_block(quest)
        user_prompt = f"""다음은 사용자가 진행 중인 퀘스트 장소에 대한 정보입니다:
{context_block}

위 정보를 참고해 아래 질문에 답해주세요.
질문: {request.user_message}"""
        
        ai_response = generate_docent_message(
            landmark=landmark,
            user_message=user_prompt,
            language=request.language
        )
        
        # TTS 생성
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
        
        # 퀘스트 채팅도 히스토리에 저장 (조회 전용)
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
    """
    퀘스트 모드 - VLM 채팅 (이미지+텍스트 저장)
    """
    try:
        if not request.quest_id:
            raise HTTPException(status_code=400, detail="quest_id is required for quest VLM chat")

        logger.info(f"Quest VLM chat: user={user_id}, quest={request.quest_id}")
        db = get_db()
        ensure_user_exists(user_id)
        
        session_id = request.chat_session_id or str(uuid.uuid4())
        quest = fetch_quest_context(request.quest_id, db=db)
        
        # 이미지 디코딩
        try:
            image_bytes = base64.b64decode(request.image)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid base64 image: {str(e)}")
        
        # 이미지 업로드
        image_url = compress_and_upload_image(
            image_bytes=image_bytes,
            max_size=1920,
            quality=85
        )
        
        # VLM 분석 (VLM 서비스 직접 사용)
        from services.vlm import analyze_place_image, extract_place_info_from_vlm_response, calculate_confidence_score
        from services.db import search_places_by_radius, get_place_by_name, save_vlm_log
        from services.embedding import generate_image_embedding, hash_image
        from services.optimized_search import search_with_gps_filter
        
        # 주변 장소 검색 (GPS 정보가 없으면 빈 리스트)
        nearby_places = []
        
        # VLM 분석
        vlm_response = analyze_place_image(
            image_bytes=image_bytes,
            nearby_places=nearby_places,
            language=request.language
        )
        
        if not vlm_response:
            raise HTTPException(status_code=503, detail="VLM service unavailable")
        
        # 장소 정보 추출
        place_info = extract_place_info_from_vlm_response(vlm_response)
        matched_place = None
        
        if place_info.get("place_name"):
            matched_place = get_place_by_name(place_info["place_name"], fuzzy=True)
        
        # 최종 설명 생성
        final_description = vlm_response
        if matched_place:
            from services.ai import generate_docent_message
            enhancement_prompt = f"""
VLM 분석 결과:
{vlm_response}

장소 정보:
- 이름: {matched_place.get('name')}
- 카테고리: {matched_place.get('category')}
- 설명: {matched_place.get('description')}

위 정보를 바탕으로 AR 도슨트처럼 친근하고 흥미롭게 3-4문장으로 이 장소를 소개해주세요.
"""
            try:
                final_description = generate_docent_message(
                    landmark=matched_place.get('name', '이 장소'),
                    user_message=enhancement_prompt if request.language == "ko" else None,
                    language=request.language
                )
            except Exception as e:
                logger.warning(f"Description enhancement failed: {e}")
        
        ai_response = final_description
        quest_context = build_quest_context_block(quest)
        ai_response = f"""{ai_response}

현재 진행 중인 퀘스트 참고 정보:
{quest_context}"""
        
        # TTS 생성
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
        
        # VLM 분석 로그 저장 (vlm_logs - 분석용)
        try:
            logger.info("💾 Saving VLM log to vlm_logs...")
            image_hash = hash_image(image_bytes)
            save_vlm_log(
                user_id=user_id,
                image_url=image_url,
                latitude=None,
                longitude=None,
                vlm_provider="gpt4v",
                vlm_response=vlm_response,
                final_description=final_description,
                matched_place_id=matched_place.get("id") if matched_place else None,
                image_hash=image_hash
            )
            logger.info("✅ VLM log saved to vlm_logs")
        except Exception as vlm_log_error:
            logger.error(f"❌ Failed to save VLM log: {vlm_log_error}", exc_info=True)
        
        # 히스토리에 저장 (chat_logs - 채팅 히스토리용)
        try:
            logger.info(f"💾 Saving VLM chat to chat_logs (session: {session_id})...")
            
            # 🔥 Image URL 검증
            if not image_url:
                logger.error("❌ Image URL is empty - upload may have failed!")
                raise HTTPException(status_code=500, detail="Image upload failed: url is empty")
            
            logger.info(f"📸 Image URL: {image_url}")
            
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
                "image_url": image_url,  # 🔥 반드시 포함
                "is_read_only": True
            }
            logger.info(f"📝 Chat data to save: mode={chat_data['mode']}, function_type={chat_data['function_type']}, session={session_id}, has_image={bool(image_url)}")
            
            result = db.table("chat_logs").insert(chat_data).execute()
            logger.info(f"✅ VLM chat saved to chat_logs (id: {result.data[0]['id'] if result.data else 'unknown'})")
        except Exception as db_error:
            logger.error(f"❌ Failed to save quest VLM chat log: {db_error}", exc_info=True)
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
    """
    STT + TTS 통합 엔드포인트
    오디오를 받아서 텍스트로 변환하고, 그 텍스트를 다시 음성으로 변환
    """
    try:
        logger.info(f"STT+TTS request: {user_id}")
        
        # STT: 오디오를 텍스트로 변환
        transcribed_text = speech_to_text_from_base64(
            audio_base64=request.audio,
            language_code=request.language_code
        )
        
        if not transcribed_text:
            raise HTTPException(status_code=400, detail="STT transcription failed")
        
        # TTS: 텍스트를 다시 음성으로 변환
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
    """
    여행지 경로 추천
    사전 질문을 통해 사용자 취향을 파악하고, 4개의 퀘스트를 추천
    """
    try:
        logger.info(f"Route recommend: {user_id}")
        
        db = get_db()
        
        # 필수 방문 장소가 있으면 포함
        must_visit_quest = None
        if request.must_visit_place_id:
            place_result = db.table("places").select("*, quests(*)").eq("id", request.must_visit_place_id).execute()
            if place_result.data and len(place_result.data) > 0:
                place = place_result.data[0]
                quests = place.get("quests", [])
                if quests and len(quests) > 0:
                    must_visit_quest = quests[0]
        
        # 사용자 취향 기반 추천 로직
        # TODO: 실제 추천 알고리즘 구현 필요
        # 현재는 간단히 주변 퀘스트를 가져오는 방식
        
        # 주변 퀘스트 조회
        if request.latitude and request.longitude:
            from routers.recommend import get_nearby_quests_route
            nearby_result = await get_nearby_quests_route(
                latitude=request.latitude,
                longitude=request.longitude,
                radius_km=10.0,
                limit=20
            )
            
            quests = nearby_result.get("quests", [])
        else:
            # 위치 정보가 없으면 전체 퀘스트에서 추천
            quests_result = db.table("quests").select("*, places(*)").eq("is_active", True).limit(20).execute()
            quests = []
            for q in quests_result.data:
                quest = dict(q)
                place = quest.get("places")
                if place:
                    quest["district"] = place.get("district")
                    quest["place_image_url"] = place.get("image_url")
                quests.append(quest)
        
        # 필수 방문 장소가 있으면 첫 번째로 추가
        recommended_quests = []
        if must_visit_quest:
            recommended_quests.append(must_visit_quest)
        
        # 나머지 3개 선택 (필수 방문 장소 제외)
        if must_visit_quest:
            must_visit_id = must_visit_quest.get("id")
            remaining_quests = [q for q in quests if q.get("id") != must_visit_id]
        else:
            remaining_quests = quests
        recommended_quests.extend(remaining_quests[:3])
        
        # 4개로 맞추기
        recommended_quests = recommended_quests[:4]
        
        # 세션 ID 생성
        session_id = str(uuid.uuid4())
        
        # 테마 추출 (preferences에서)
        theme = request.preferences.get("theme") or request.preferences.get("category") or "서울 여행"
        if isinstance(theme, dict):
            theme = theme.get("name", "서울 여행")
        
        # 채팅 기록 저장 (여행 일정 - 보기 전용)
        try:
            db.table("chat_logs").insert({
                "user_id": user_id,
                "user_message": f"경로 추천 요청: {request.preferences}",
                "ai_response": f"{len(recommended_quests)}개의 퀘스트를 추천했습니다.",
                "mode": "explore",
                "function_type": "route_recommend",
                "chat_session_id": session_id,
                "title": theme,  # ex: Events, Food, Culture 등
                "is_read_only": True,  # 보기 전용
                
                # 🔥 신규 필드 저장
                "quest_step": 99,  # 최종 결과 단계
                "prompt_step_text": "AI가 추천한 여행 코스 결과입니다!",
                "options": None,
                "selected_theme": theme,
                "selected_districts": request.preferences.get("districts"),
                "include_cart": request.preferences.get("include_cart", False)
            }).execute()
            logger.info(f"✅ Route recommend chat log saved (session: {session_id})")
        except Exception as db_error:
            logger.warning(f"Failed to save chat log: {db_error}")
        
        logger.info(f"Recommended {len(recommended_quests)} quests")
        
        return {
            "success": True,
            "quests": recommended_quests,
            "count": len(recommended_quests),
            "session_id": session_id
        }
    
    except Exception as e:
        logger.error(f"Route recommend error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
