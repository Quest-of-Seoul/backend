"""AI Station Router - 채팅 리스트 및 통합 기능"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, List
import base64
import uuid
import logging
from datetime import datetime

from services.ai import generate_docent_message
from services.db import get_db
from services.embedding import generate_text_embedding
from services.pinecone_store import search_similar_pinecone
from services.stt import speech_to_text_from_base64, speech_to_text
from services.tts import text_to_speech_url, text_to_speech
from services.storage import compress_and_upload_image

logger = logging.getLogger(__name__)
router = APIRouter()


class ChatListRequest(BaseModel):
    user_id: str
    mode: Optional[str] = None  # 'explore' or 'quest'
    function_type: Optional[str] = None  # 'rag_chat', 'vlm_chat', 'route_recommend', 'image_similarity'
    limit: int = 20


class ExploreRAGChatRequest(BaseModel):
    user_id: str
    user_message: str
    language: str = "ko"
    prefer_url: bool = False
    enable_tts: bool = True
    chat_session_id: Optional[str] = None


class QuestRAGChatRequest(BaseModel):
    user_id: str
    user_message: str
    landmark: Optional[str] = None
    language: str = "ko"
    prefer_url: bool = False
    enable_tts: bool = True
    chat_session_id: Optional[str] = None


class QuestVLMChatRequest(BaseModel):
    user_id: str
    image: str  # base64
    user_message: Optional[str] = None
    language: str = "ko"
    prefer_url: bool = False
    enable_tts: bool = True
    chat_session_id: Optional[str] = None


class STTTTSRequest(BaseModel):
    user_id: str
    audio: str  # base64 encoded audio
    language_code: str = "ko-KR"
    prefer_url: bool = False


class RouteRecommendRequest(BaseModel):
    user_id: str
    preferences: dict  # 사용자 취향 정보
    must_visit_place_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


@router.get("/chat-list")
async def get_chat_list(
    user_id: str,
    mode: Optional[str] = None,
    function_type: Optional[str] = None,
    limit: int = 20
):
    """
    채팅 리스트 조회 (하프 모달용)
    모드별, 기능별로 채팅 기록을 그룹화하여 반환
    """
    try:
        db = get_db()
        
        query = db.table("chat_logs").select("*").eq("user_id", user_id)
        
        if mode:
            query = query.eq("mode", mode)
        if function_type:
            query = query.eq("function_type", function_type)
        
        result = query.order("created_at", desc=True).limit(limit).execute()
        
        # 세션별로 그룹화
        sessions = {}
        for chat in result.data:
            session_id = chat.get("chat_session_id")
            if not session_id:
                session_id = str(chat.get("id"))
            
            if session_id not in sessions:
                sessions[session_id] = {
                    "session_id": session_id,
                    "mode": chat.get("mode", "explore"),
                    "function_type": chat.get("function_type", "rag_chat"),
                    "landmark": chat.get("landmark"),
                    "created_at": chat.get("created_at"),
                    "updated_at": chat.get("created_at"),
                    "preview": chat.get("user_message", "")[:50] if chat.get("user_message") else "",
                    "chats": []
                }
            
            sessions[session_id]["chats"].append({
                "id": chat.get("id"),
                "user_message": chat.get("user_message"),
                "ai_response": chat.get("ai_response"),
                "created_at": chat.get("created_at")
            })
            
            # 최신 업데이트 시간 갱신
            if chat.get("created_at") > sessions[session_id]["updated_at"]:
                sessions[session_id]["updated_at"] = chat.get("created_at")
        
        # 세션 리스트로 변환 (최신순)
        session_list = list(sessions.values())
        session_list.sort(key=lambda x: x["updated_at"], reverse=True)
        
        logger.info(f"Retrieved {len(session_list)} chat sessions for user: {user_id}")
        
        return {
            "success": True,
            "sessions": session_list,
            "count": len(session_list)
        }
    
    except Exception as e:
        logger.error(f"Chat list error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching chat list: {str(e)}")


@router.post("/explore/rag-chat")
async def explore_rag_chat(request: ExploreRAGChatRequest):
    """
    탐색 모드 - 일반 RAG 채팅 (텍스트만 저장)
    Pinecone에 저장된 장소 description을 RAG로 검색하여 답변 생성
    """
    try:
        logger.info(f"Explore RAG chat: {request.user_id}")
        
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
        try:
            db.table("chat_logs").insert({
                "user_id": request.user_id,
                "user_message": request.user_message,
                "ai_response": ai_response,
                "mode": "explore",
                "function_type": "rag_chat",
                "chat_session_id": session_id
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
async def quest_rag_chat(request: QuestRAGChatRequest):
    """
    퀘스트 모드 - 일반 RAG 채팅 (이미지+텍스트 저장 가능)
    """
    try:
        logger.info(f"Quest RAG chat: {request.user_id}, landmark: {request.landmark}")
        
        session_id = request.chat_session_id
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # 장소 정보 기반 RAG 채팅
        landmark = request.landmark or "현재 위치"
        
        ai_response = generate_docent_message(
            landmark=landmark,
            user_message=request.user_message,
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
        
        # 채팅 기록 저장
        try:
            db = get_db()
            db.table("chat_logs").insert({
                "user_id": request.user_id,
                "landmark": landmark,
                "user_message": request.user_message,
                "ai_response": ai_response,
                "mode": "quest",
                "function_type": "rag_chat",
                "chat_session_id": session_id
            }).execute()
        except Exception as db_error:
            logger.warning(f"Failed to save chat log: {db_error}")
        
        response = {
            "success": True,
            "message": ai_response,
            "landmark": landmark,
            "session_id": session_id
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
async def quest_vlm_chat(request: QuestVLMChatRequest):
    """
    퀘스트 모드 - VLM 채팅 (이미지+텍스트 저장)
    """
    try:
        logger.info(f"Quest VLM chat: {request.user_id}")
        
        session_id = request.chat_session_id
        if not session_id:
            session_id = str(uuid.uuid4())
        
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
        from services.db import search_places_by_radius, get_place_by_name
        from services.embedding import generate_image_embedding
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
        
        # 채팅 기록 저장 (이미지+텍스트)
        try:
            db = get_db()
            db.table("chat_logs").insert({
                "user_id": request.user_id,
                "landmark": matched_place.get("name") if matched_place else None,
                "user_message": request.user_message or "",
                "ai_response": ai_response,
                "mode": "quest",
                "function_type": "vlm_chat",
                "image_url": image_url,
                "chat_session_id": session_id
            }).execute()
        except Exception as db_error:
            logger.warning(f"Failed to save chat log: {db_error}")
        
        response = {
            "success": True,
            "message": ai_response,
            "place": matched_place,
            "image_url": image_url,
            "session_id": session_id
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
async def stt_and_tts(request: STTTTSRequest):
    """
    STT + TTS 통합 엔드포인트
    오디오를 받아서 텍스트로 변환하고, 그 텍스트를 다시 음성으로 변환
    """
    try:
        logger.info(f"STT+TTS request: {request.user_id}")
        
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
async def recommend_route(request: RouteRecommendRequest):
    """
    여행지 경로 추천
    사전 질문을 통해 사용자 취향을 파악하고, 4개의 퀘스트를 추천
    """
    try:
        logger.info(f"Route recommend: {request.user_id}")
        
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
        
        # 채팅 기록 저장
        try:
            db.table("chat_logs").insert({
                "user_id": request.user_id,
                "user_message": f"경로 추천 요청: {request.preferences}",
                "ai_response": f"{len(recommended_quests)}개의 퀘스트를 추천했습니다.",
                "mode": "explore",
                "function_type": "route_recommend",
                "chat_session_id": session_id
            }).execute()
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
