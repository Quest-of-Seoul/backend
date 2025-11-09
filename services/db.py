"""
Database service - Supabase client
VLM 이미지 분석 및 장소 검색 기능 포함
"""

from supabase import create_client, Client
import os
from typing import List, Dict, Optional, Tuple

# Initialize Supabase client
def get_supabase() -> Client:
    """Get Supabase client instance"""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")

    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in environment")

    return create_client(url, key)

# Singleton instance
supabase_client = None

def get_db() -> Client:
    """Get or create Supabase client singleton"""
    global supabase_client
    if supabase_client is None:
        supabase_client = get_supabase()
    return supabase_client


# ============================================================
# VLM & 장소 검색 함수들
# ============================================================

def search_similar_images(
    embedding: List[float],
    match_threshold: float = 0.7,
    match_count: int = 5
) -> List[Dict]:
    """
    벡터 유사도 기반 이미지 검색 (pgvector)
    
    Args:
        embedding: 쿼리 이미지 임베딩 벡터 (512차원)
        match_threshold: 최소 유사도 임계값
        match_count: 반환할 최대 결과 수
    
    Returns:
        유사 이미지 리스트 (장소 정보 포함)
    """
    try:
        db = get_db()
        
        # pgvector 함수 호출
        result = db.rpc(
            "search_similar_images",
            {
                "query_embedding": embedding,
                "match_threshold": match_threshold,
                "match_count": match_count
            }
        ).execute()
        
        if not result.data:
            print("[DB] No similar images found")
            return []
        
        # 장소 정보 조인
        similar_images = []
        for item in result.data:
            place_id = item.get("place_id")
            if place_id:
                place = get_place_by_id(place_id)
                similar_images.append({
                    "id": item.get("id"),
                    "image_url": item.get("image_url"),
                    "similarity": item.get("similarity"),
                    "place": place
                })
        
        print(f"[DB] ✅ Found {len(similar_images)} similar images")
        return similar_images
    
    except Exception as e:
        print(f"[DB] ❌ Error searching similar images: {e}")
        return []


def search_places_by_radius(
    latitude: float,
    longitude: float,
    radius_km: float = 1.0,
    limit_count: int = 10
) -> List[Dict]:
    """
    GPS 반경 내 장소 검색
    
    Args:
        latitude: 위도
        longitude: 경도
        radius_km: 검색 반경 (km)
        limit_count: 최대 결과 수
    
    Returns:
        주변 장소 리스트 (거리 포함)
    """
    try:
        db = get_db()
        
        # pgvector earthdistance 함수 호출
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
            print(f"[DB] No places found within {radius_km}km")
            return []
        
        print(f"[DB] ✅ Found {len(result.data)} places within {radius_km}km")
        return result.data
    
    except Exception as e:
        print(f"[DB] ❌ Error searching places by radius: {e}")
        return []


def get_place_by_id(place_id: str) -> Optional[Dict]:
    """
    장소 ID로 상세 정보 조회
    
    Args:
        place_id: 장소 UUID
    
    Returns:
        장소 정보 딕셔너리
    """
    try:
        db = get_db()
        result = db.table("places").select("*").eq("id", place_id).single().execute()
        
        if result.data:
            print(f"[DB] ✅ Found place: {result.data.get('name')}")
            return result.data
        
        return None
    
    except Exception as e:
        print(f"[DB] ❌ Error getting place: {e}")
        return None


def get_place_by_name(name: str, fuzzy: bool = True) -> Optional[Dict]:
    """
    장소명으로 검색
    
    Args:
        name: 장소명
        fuzzy: 퍼지 매칭 사용 여부
    
    Returns:
        장소 정보 딕셔너리
    """
    try:
        db = get_db()
        
        if fuzzy:
            # ILIKE를 사용한 부분 매칭
            result = db.table("places").select("*").ilike("name", f"%{name}%").limit(1).execute()
        else:
            # 정확한 매칭
            result = db.table("places").select("*").eq("name", name).limit(1).execute()
        
        if result.data and len(result.data) > 0:
            print(f"[DB] ✅ Found place: {result.data[0].get('name')}")
            return result.data[0]
        
        return None
    
    except Exception as e:
        print(f"[DB] ❌ Error searching place by name: {e}")
        return None


def save_image_vector(
    place_id: str,
    image_url: str,
    embedding: List[float],
    image_hash: Optional[str] = None,
    source: str = "dataset",
    metadata: Optional[Dict] = None
) -> Optional[str]:
    """
    이미지 벡터를 DB에 저장
    
    Args:
        place_id: 장소 UUID
        image_url: 이미지 URL
        embedding: 512차원 임베딩 벡터
        image_hash: 이미지 해시
        source: 출처
        metadata: 추가 메타데이터
    
    Returns:
        생성된 벡터 ID
    """
    try:
        db = get_db()
        
        data = {
            "place_id": place_id,
            "image_url": image_url,
            "embedding": embedding,
            "source": source
        }
        
        if image_hash:
            data["image_hash"] = image_hash
        
        if metadata:
            data["metadata"] = metadata
        
        result = db.table("image_vectors").insert(data).execute()
        
        if result.data and len(result.data) > 0:
            vector_id = result.data[0].get("id")
            print(f"[DB] ✅ Image vector saved: {vector_id}")
            return vector_id
        
        return None
    
    except Exception as e:
        print(f"[DB] ❌ Error saving image vector: {e}")
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
    """
    VLM 분석 로그 저장
    
    Args:
        user_id: 사용자 ID
        image_url: 이미지 URL
        latitude: 촬영 위치 위도
        longitude: 촬영 위치 경도
        vlm_provider: VLM 제공자 (gpt4v)
        vlm_response: VLM 원본 응답
        final_description: 최종 설명
        matched_place_id: 매칭된 장소 ID
        similar_places: 유사 장소 리스트
        confidence_score: 신뢰도 점수
        processing_time_ms: 처리 시간
        image_hash: 이미지 해시
        error_message: 에러 메시지
    
    Returns:
        로그 ID
    """
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
            print(f"[DB] ✅ VLM log saved: {log_id}")
            return log_id
        
        return None
    
    except Exception as e:
        print(f"[DB] ❌ Error saving VLM log: {e}")
        return None


def get_cached_vlm_result(image_hash: str, max_age_hours: int = 24) -> Optional[Dict]:
    """
    이미지 해시로 캐싱된 VLM 결과 조회
    
    Args:
        image_hash: 이미지 SHA-256 해시
        max_age_hours: 최대 캐시 유효 시간
    
    Returns:
        캐싱된 VLM 로그
    """
    try:
        db = get_db()
        
        # 최근 N시간 이내 결과만 조회
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
            print(f"[DB] ✅ Found cached VLM result for hash: {image_hash[:16]}...")
            return result.data[0]
        
        return None
    
    except Exception as e:
        print(f"[DB] ❌ Error getting cached result: {e}")
        return None


def increment_place_view_count(place_id: str) -> bool:
    """
    장소 조회수 증가
    
    Args:
        place_id: 장소 UUID
    
    Returns:
        성공 여부
    """
    try:
        db = get_db()
        
        # 현재 조회수 가져오기
        place = get_place_by_id(place_id)
        if not place:
            return False
        
        current_count = place.get("view_count", 0)
        
        # 조회수 증가
        db.table("places").update({"view_count": current_count + 1}).eq("id", place_id).execute()
        
        print(f"[DB] ✅ Incremented view count for place: {place_id}")
        return True
    
    except Exception as e:
        print(f"[DB] ❌ Error incrementing view count: {e}")
        return False


def get_popular_places(limit: int = 10) -> List[Dict]:
    """
    인기 장소 조회 (조회수 기준)
    
    Args:
        limit: 최대 결과 수
    
    Returns:
        인기 장소 리스트
    """
    try:
        db = get_db()
        
        result = db.table("places") \
            .select("*") \
            .eq("is_active", True) \
            .order("view_count", desc=True) \
            .limit(limit) \
            .execute()
        
        print(f"[DB] ✅ Retrieved {len(result.data)} popular places")
        return result.data
    
    except Exception as e:
        print(f"[DB] ❌ Error getting popular places: {e}")
        return []
