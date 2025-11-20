"""Database Service - Supabase Client"""

from supabase import create_client, Client
import os
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

supabase_client = None


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
        
        # 중복 체크 (이름과 좌표로)
        existing = db.table("places") \
            .select("id") \
            .ilike("name", place_data["name"]) \
            .eq("latitude", place_data["latitude"]) \
            .eq("longitude", place_data["longitude"]) \
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
        quest_insert = {
            "place_id": place_id,
            "name": place.get("name"),
            "title": place.get("name"),
            "description": place.get("description"),
            "category": place.get("category"),
            "latitude": float(place.get("latitude")),
            "longitude": float(place.get("longitude")),
            "reward_point": 100,
            "points": 10,
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

