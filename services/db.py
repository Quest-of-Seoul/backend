"""Database Service - Supabase Client"""

from supabase import create_client, Client
import os
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

supabase_client = None

DISTRICT_QUEST_POINTS: Dict[str, int] = {
    # 200 포인트권 (주요 상권)
    "강남구": 200, "Gangnam-gu": 200,
    "광진구": 200, "Gwangjin-gu": 200,
    "마포구": 200, "Mapo-gu": 200,
    "서초구": 200, "Seocho-gu": 200,
    "송파구": 200, "Songpa-gu": 200,
    "용산구": 200, "Yongsan-gu": 200,
    "종로구": 200, "Jongno-gu": 200,
    "중구": 200, "Jung-gu": 200,
    # 250 포인트권
    "동대문구": 250, "Dongdaemun-gu": 250,
    "동작구": 250, "Dongjak-gu": 250,
    "서대문구": 250, "Seodaemun-gu": 250,
    "성동구": 250, "Seongdong-gu": 250,
    "영등포구": 250, "Yeongdeungpo-gu": 250,
    # 300 포인트권
    "강동구": 300, "Gangdong-gu": 300,
    "강서구": 300, "Gangseo-gu": 300,
    "관악구": 300, "Gwanak-gu": 300,
    "노원구": 300, "Nowon-gu": 300,
    "성북구": 300, "Seongbuk-gu": 300,
    "양천구": 300, "Yangcheon-gu": 300,
    "중랑구": 300, "Jungnang-gu": 300,
    # 350 포인트권
    "구로구": 350, "Guro-gu": 350,
    # 400 포인트권 (비주류/숨겨진 지역)
    "강북구": 400, "Gangbuk-gu": 400,
    "금천구": 400, "Geumcheon-gu": 400,
    "도봉구": 400, "Dobong-gu": 400,
    "은평구": 400, "Eunpyeong-gu": 400,
}

DEFAULT_QUEST_POINTS = 300


def get_points_for_district(district: Optional[str]) -> int:
    """자치구 기준 포인트 산정"""
    if not district:
        return DEFAULT_QUEST_POINTS
    normalized = district.strip()
    return DISTRICT_QUEST_POINTS.get(normalized, DEFAULT_QUEST_POINTS)


def get_supabase() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")

    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")

    return create_client(url, key)


def get_db() -> Client:
    global supabase_client
    if supabase_client is None:
        supabase_client = get_supabase()
    return supabase_client


def ensure_user_exists(user_id: str, email: Optional[str] = None, nickname: str = "Guest User") -> None:
    """
    Ensure that a user row exists so that FK constrained tables (points, chat_logs, etc.) can insert safely.
    """
    try:
        db = get_db()
        existing = db.table("users").select("id").eq("id", user_id).limit(1).execute()
        if existing.data:
            return
        db.table("users").insert({
            "id": user_id,
            "email": email or f"{user_id}@guest.local",
            "nickname": nickname
        }).execute()
    except Exception as exc:
        logger.error(f"Failed to ensure user exists ({user_id}): {exc}", exc_info=True)
        raise


def search_places_by_radius(
    latitude: float,
    longitude: float,
    radius_km: float = 1.0,
    limit_count: int = 10
) -> List[Dict]:
    """Search places within GPS radius"""
    try:
        db = get_db()
        
        result = db.rpc(
            "search_places_by_radius",
            {
                "lat": latitude,
                "lon": longitude,
                "radius_km": radius_km,
                "limit_count": limit_count
            }
        ).execute()
        
        if not result.data:
            logger.info(f"No places found within {radius_km}km")
            return []
        
        logger.info(f"Found {len(result.data)} places within {radius_km}km")
        return result.data
    
    except Exception as e:
        logger.error(f"Error searching places: {e}", exc_info=True)
        return []


def get_place_by_id(place_id: str) -> Optional[Dict]:
    """Get place by ID"""
    try:
        db = get_db()
        result = db.table("places").select("*").eq("id", place_id).single().execute()
        
        if result.data:
            logger.info(f"Found place: {result.data.get('name')}")
            return result.data
        
        return None
    
    except Exception as e:
        logger.error(f"Error getting place: {e}", exc_info=True)
        return None


def get_place_by_name(name: str, fuzzy: bool = True) -> Optional[Dict]:
    """Search place by name with optional fuzzy matching"""
    try:
        db = get_db()
        
        if fuzzy:
            result = db.table("places").select("*").ilike("name", f"%{name}%").limit(1).execute()
        else:
            result = db.table("places").select("*").eq("name", name).limit(1).execute()
        
        if result.data and len(result.data) > 0:
            logger.info(f"Found place: {result.data[0].get('name')}")
            return result.data[0]
        
        return None
    
    except Exception as e:
        logger.error(f"Error searching place by name: {e}", exc_info=True)
        return None


def save_vlm_log(
    user_id: str,
    image_url: Optional[str],
    latitude: Optional[float],
    longitude: Optional[float],
    vlm_provider: str,
    vlm_response: str,
    final_description: str,
    matched_place_id: Optional[str] = None,
    similar_places: Optional[List[Dict]] = None,
    confidence_score: Optional[float] = None,
    processing_time_ms: Optional[int] = None,
    image_hash: Optional[str] = None,
    error_message: Optional[str] = None
) -> Optional[str]:
    """Save VLM analysis log"""
    try:
        db = get_db()
        
        data = {
            "user_id": user_id,
            "vlm_provider": vlm_provider,
            "vlm_response": vlm_response,
            "final_description": final_description
        }
        
        if image_url:
            data["image_url"] = image_url
        
        if latitude and longitude:
            data["latitude"] = latitude
            data["longitude"] = longitude
        
        if matched_place_id:
            data["matched_place_id"] = matched_place_id
        
        if similar_places:
            data["similar_places"] = similar_places
        
        if confidence_score is not None:
            data["confidence_score"] = confidence_score
        
        if processing_time_ms is not None:
            data["processing_time_ms"] = processing_time_ms
        
        if image_hash:
            data["image_hash"] = image_hash
        
        if error_message:
            data["error_message"] = error_message
        
        result = db.table("vlm_logs").insert(data).execute()
        
        if result.data and len(result.data) > 0:
            log_id = result.data[0].get("id")
            logger.info(f"VLM log saved: {log_id}")
            return log_id
        
        return None
    
    except Exception as e:
        logger.error(f"Error saving VLM log: {e}", exc_info=True)
        return None


def get_cached_vlm_result(image_hash: str, max_age_hours: int = 24) -> Optional[Dict]:
    """Get cached VLM result by image hash"""
    try:
        db = get_db()
        from datetime import datetime, timedelta
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        result = db.table("vlm_logs") \
            .select("*") \
            .eq("image_hash", image_hash) \
            .gte("created_at", cutoff_time.isoformat()) \
            .order("created_at", desc=True) \
            .limit(1) \
            .execute()
        
        if result.data and len(result.data) > 0:
            logger.info(f"Found cached VLM result for hash: {image_hash[:16]}...")
            return result.data[0]
        
        return None
    
    except Exception as e:
        logger.error(f"Error getting cached result: {e}", exc_info=True)
        return None


def increment_place_view_count(place_id: str) -> bool:
    """Increment place view count"""
    try:
        db = get_db()
        place = get_place_by_id(place_id)
        if not place:
            return False
        
        current_count = place.get("view_count", 0)
        db.table("places").update({"view_count": current_count + 1}).eq("id", place_id).execute()
        
        logger.info(f"Incremented view count for place: {place_id}")
        return True
    
    except Exception as e:
        logger.error(f"Error incrementing view count: {e}", exc_info=True)
        return False


def save_place(place_data: Dict) -> Optional[str]:
    """
    장소 데이터를 DB에 저장
    
    Args:
        place_data: 저장할 장소 데이터 딕셔너리
    
    Returns:
        저장된 place_id 또는 None
    """
    try:
        db = get_db()
        
        # 필수 필드 검증
        if not place_data.get("name"):
            logger.error("Place name is required")
            return None
        
        if not place_data.get("latitude") or not place_data.get("longitude"):
            logger.error("Place coordinates are required")
            return None
        
        # 중복 체크 (이름으로만 - UNIQUE 제약이 name에 있음)
        # 이름이 같으면 같은 장소로 간주하고 업데이트
        existing = db.table("places") \
            .select("id") \
            .ilike("name", place_data["name"]) \
            .limit(1) \
            .execute()
        
        if existing.data and len(existing.data) > 0:
            place_id = existing.data[0]["id"]
            logger.info(f"Place already exists: {place_id} ({place_data['name']})")
            
            # 업데이트
            db.table("places").update(place_data).eq("id", place_id).execute()
            return place_id
        
        # 새로 생성
        result = db.table("places").insert(place_data).execute()
        
        if result.data and len(result.data) > 0:
            place_id = result.data[0].get("id")
            logger.info(f"Place saved: {place_id} ({place_data['name']})")
            return place_id
        
        return None
    
    except Exception as e:
        logger.error(f"Error saving place: {e}", exc_info=True)
        return None


def create_quest_from_place(place_id: str, quest_data: Optional[Dict] = None) -> Optional[int]:
    """
    장소로부터 퀘스트 생성
    
    Args:
        place_id: 장소 ID
        quest_data: 추가 퀘스트 데이터 (선택)
    
    Returns:
        생성된 quest_id 또는 None
    """
    try:
        db = get_db()
        
        # 장소 정보 가져오기
        place = get_place_by_id(place_id)
        if not place:
            logger.error(f"Place not found: {place_id}")
            return None
        
        # 퀘스트 데이터 준비
        quest_points = get_points_for_district(place.get("district"))
        logger.info(
            "Calculated quest points for place %s (district: %s): %d",
            place_id,
            place.get("district"),
            quest_points
        )
        
        # 문자열 길이 제한 검증 (스키마 제약 조건)
        quest_name = place.get("name") or ""
        if len(quest_name) > 255:
            logger.warning(f"Quest name exceeds 255 characters, truncating: {quest_name[:50]}...")
            quest_name = quest_name[:255]
        
        quest_category = place.get("category") or ""
        if quest_category and len(quest_category) > 50:
            logger.warning(f"Quest category exceeds 50 characters, truncating: {quest_category[:50]}...")
            quest_category = quest_category[:50]
        
        quest_insert = {
            "place_id": place_id,
            "name": quest_name,
            "title": quest_name,  # title도 255자 제한
            "description": place.get("description"),
            "category": quest_category,
            "latitude": float(place.get("latitude")),
            "longitude": float(place.get("longitude")),
            "reward_point": quest_points,
            "points": quest_points,
            "difficulty": "easy",
            "is_active": True
        }
        
        # 추가 데이터 병합
        if quest_data:
            quest_insert.update(quest_data)
        
        # 중복 체크
        existing = db.table("quests") \
            .select("id") \
            .eq("place_id", place_id) \
            .limit(1) \
            .execute()
        
        if existing.data and len(existing.data) > 0:
            quest_id = existing.data[0]["id"]
            logger.info(f"Quest already exists for place: {place_id} (quest_id: {quest_id})")
            return quest_id
        
        # 새로 생성
        result = db.table("quests").insert(quest_insert).execute()
        
        if result.data and len(result.data) > 0:
            quest_id = result.data[0].get("id")
            logger.info(f"Quest created: {quest_id} for place: {place_id}")
            return quest_id
        
        return None
    
    except Exception as e:
        logger.error(f"Error creating quest: {e}", exc_info=True)
        return None
