"""Anonymous location tracking service for marketing data collection"""

import hashlib
import logging
from typing import Optional, Dict, Any
from services.db import get_db

logger = logging.getLogger(__name__)


def anonymize_user_id(user_id: str) -> str:
    """
    사용자 ID를 SHA-256 해시로 익명화
    
    Args:
        user_id: 원본 사용자 ID (UUID)
    
    Returns:
        SHA-256 해시값 (64자리 hex 문자열)
    """
    return hashlib.sha256(user_id.encode()).hexdigest()


def calculate_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Haversine 공식을 사용하여 두 지점 간 거리 계산 (km)
    
    Args:
        lat1, lon1: 첫 번째 지점의 위도, 경도
        lat2, lon2: 두 번째 지점의 위도, 경도
    
    Returns:
        거리 (km)
    """
    import math
    
    R = 6371  # 지구 반지름 (km)
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def log_location_data(
    user_id: str,
    quest_id: Optional[int] = None,
    place_id: Optional[str] = None,
    user_latitude: Optional[float] = None,
    user_longitude: Optional[float] = None,
    start_latitude: Optional[float] = None,
    start_longitude: Optional[float] = None,
    interest_type: str = "quest_start",
    treasure_hunt_count: int = 0,
    distance_threshold_km: float = 1.0
) -> bool:
    """
    위치 정보를 익명화하여 수집 (1km 이내일 때만)
    
    Args:
        user_id: 사용자 ID (익명화됨)
        quest_id: 퀘스트 ID
        place_id: 장소 ID
        user_latitude: 사용자 현재 위치 위도
        user_longitude: 사용자 현재 위치 경도
        start_latitude: 출발 위치 위도
        start_longitude: 출발 위치 경도
        interest_type: 관심 유형 (quest_start, quest_view, route_recommend, image_similarity 등)
        treasure_hunt_count: 보물 찾기 횟수
        distance_threshold_km: 거리 임계값 (기본: 1.0km)
    
    Returns:
        수집 성공 여부 (1km 이내일 때만 True)
    """
    try:
        # 1km 이내 확인
        if quest_id and user_latitude and user_longitude:
            db = get_db()
            
            # 퀘스트 위치 조회
            quest_result = db.table("quests").select("latitude, longitude, place_id").eq("id", quest_id).single().execute()
            
            if not quest_result.data:
                logger.warning(f"Quest {quest_id} not found")
                return False
            
            quest_lat = float(quest_result.data["latitude"])
            quest_lon = float(quest_result.data["longitude"])
            quest_place_id = quest_result.data.get("place_id")
            
            # 거리 계산
            distance_km = calculate_distance_km(
                user_latitude, user_longitude,
                quest_lat, quest_lon
            )
            
            # 1km 이내가 아니면 수집하지 않음
            if distance_km > distance_threshold_km:
                logger.info(f"User {user_id[:8]}... is {distance_km:.2f}km away from quest {quest_id}, skipping log")
                return False
            
            # Place 정보 조회 (district 등)
            district = None
            if quest_place_id:
                place_result = db.table("places").select("district").eq("id", quest_place_id).single().execute()
                if place_result.data:
                    district = place_result.data.get("district")
            
            # 익명화된 사용자 ID 생성
            anonymous_user_id = anonymize_user_id(user_id)
            
            # 위치 정보 로그 저장
            log_data = {
                "anonymous_user_id": anonymous_user_id,
                "quest_id": quest_id,
                "place_id": quest_place_id or place_id,
                "user_latitude": float(user_latitude) if user_latitude else None,
                "user_longitude": float(user_longitude) if user_longitude else None,
                "start_latitude": float(start_latitude) if start_latitude else None,
                "start_longitude": float(start_longitude) if start_longitude else None,
                "distance_from_quest_km": round(distance_km, 3),
                "district": district,
                "interest_type": interest_type,
                "treasure_hunt_count": treasure_hunt_count
            }
            
            db.table("anonymous_location_logs").insert(log_data).execute()
            
            logger.info(f"Location log saved: quest_id={quest_id}, district={district}, distance={distance_km:.2f}km")
            return True
        
        # Quest ID가 없거나 위치 정보가 없으면 수집하지 않음
        logger.debug(f"Missing required data for location logging: quest_id={quest_id}, lat={user_latitude}, lon={user_longitude}")
        return False
    
    except Exception as e:
        logger.error(f"Error logging location data: {e}", exc_info=True)
        return False


def log_route_recommendation(
    user_id: str,
    recommended_quest_ids: list,
    user_latitude: Optional[float] = None,
    user_longitude: Optional[float] = None,
    start_latitude: Optional[float] = None,
    start_longitude: Optional[float] = None
) -> int:
    """
    경로 추천 시 관심 장소 로그 수집
    
    Args:
        user_id: 사용자 ID
        recommended_quest_ids: 추천된 퀘스트 ID 리스트
        user_latitude: 사용자 현재 위치 위도
        user_longitude: 사용자 현재 위치 경도
        start_latitude: 출발 위치 위도
        start_longitude: 출발 위치 경도
    
    Returns:
        수집된 로그 개수
    """
    count = 0
    for quest_id in recommended_quest_ids:
        # 경로 추천은 거리 제한 없이 관심도만 기록
        try:
            db = get_db()
            quest_result = db.table("quests").select("place_id, latitude, longitude").eq("id", quest_id).single().execute()
            
            if quest_result.data:
                place_id = quest_result.data.get("place_id")
                quest_lat = quest_result.data.get("latitude")
                quest_lon = quest_result.data.get("longitude")
                
                # Place 정보 조회
                district = None
                if place_id:
                    place_result = db.table("places").select("district").eq("id", place_id).single().execute()
                    if place_result.data:
                        district = place_result.data.get("district")
                
                # 거리 계산 (표시용)
                distance_km = None
                if user_latitude and user_longitude and quest_lat and quest_lon:
                    distance_km = calculate_distance_km(
                        user_latitude, user_longitude,
                        float(quest_lat), float(quest_lon)
                    )
                
                # 익명화된 사용자 ID 생성
                anonymous_user_id = anonymize_user_id(user_id)
                
                log_data = {
                    "anonymous_user_id": anonymous_user_id,
                    "quest_id": quest_id,
                    "place_id": place_id,
                    "user_latitude": float(user_latitude) if user_latitude else None,
                    "user_longitude": float(user_longitude) if user_longitude else None,
                    "start_latitude": float(start_latitude) if start_latitude else None,
                    "start_longitude": float(start_longitude) if start_longitude else None,
                    "distance_from_quest_km": round(distance_km, 3) if distance_km else None,
                    "district": district,
                    "interest_type": "route_recommend",
                    "treasure_hunt_count": 0
                }
                
                db.table("anonymous_location_logs").insert(log_data).execute()
                count += 1
        except Exception as e:
            logger.error(f"Error logging route recommendation for quest {quest_id}: {e}", exc_info=True)
    
    return count


def log_periodic_location(
    user_id: str,
    user_latitude: float,
    user_longitude: float,
    quest_id: Optional[int] = None,
    place_id: Optional[str] = None
) -> bool:
    """
    주기적인 위치 추적 (시간별 이동 경로 추적용)
    거리 제한 없이 모든 위치를 기록
    
    Args:
        user_id: 사용자 ID
        user_latitude: 사용자 현재 위치 위도
        user_longitude: 사용자 현재 위치 경도
        quest_id: 현재 진행 중인 퀘스트 ID (선택)
        place_id: 현재 위치한 장소 ID (선택)
    
    Returns:
        수집 성공 여부
    """
    try:
        db = get_db()
        
        # 익명화된 사용자 ID 생성
        anonymous_user_id = anonymize_user_id(user_id)
        
        # District 추출 (주변 장소 기반 또는 reverse geocoding)
        district = None
        
        # 1. place_id가 있으면 해당 장소의 district 사용
        if place_id:
            place_result = db.table("places").select("district").eq("id", place_id).single().execute()
            if place_result.data:
                district = place_result.data.get("district")
        
        # 2. place_id가 없고 quest_id가 있으면 퀘스트의 place_id로 district 조회
        if not district and quest_id:
            quest_result = db.table("quests").select("place_id").eq("id", quest_id).single().execute()
            if quest_result.data:
                quest_place_id = quest_result.data.get("place_id")
                if quest_place_id:
                    place_result = db.table("places").select("district").eq("id", quest_place_id).single().execute()
                    if place_result.data:
                        district = place_result.data.get("district")
        
        # 3. 주변 장소 기반으로 district 추정 (500m 이내)
        if not district:
            nearby_places = db.rpc(
                "search_places_by_radius",
                {
                    "lat": float(user_latitude),
                    "lon": float(user_longitude),
                    "radius_km": 0.5,  # 500m
                    "limit_count": 1
                }
            ).execute()
            
            if nearby_places.data and len(nearby_places.data) > 0:
                # 주변 장소의 district 사용
                nearby_place = nearby_places.data[0]
                # address에서 district 추출
                address = nearby_place.get("address", "")
                if address:
                    # 간단한 정규식으로 district 추출 시도
                    import re
                    match = re.search(r'([가-힣]+구)', address)
                    if match:
                        district = match.group(1)
        
        # 거리 계산 (quest_id가 있으면)
        distance_from_quest_km = None
        if quest_id:
            quest_result = db.table("quests").select("latitude, longitude").eq("id", quest_id).single().execute()
            if quest_result.data:
                quest_lat = float(quest_result.data["latitude"])
                quest_lon = float(quest_result.data["longitude"])
                distance_from_quest_km = calculate_distance_km(
                    user_latitude, user_longitude,
                    quest_lat, quest_lon
                )
        
        # 위치 정보 로그 저장
        log_data = {
            "anonymous_user_id": anonymous_user_id,
            "quest_id": quest_id,
            "place_id": place_id,
            "user_latitude": float(user_latitude),
            "user_longitude": float(user_longitude),
            "start_latitude": None,  # 주기적 추적에서는 출발지 정보 없음
            "start_longitude": None,
            "distance_from_quest_km": round(distance_from_quest_km, 3) if distance_from_quest_km else None,
            "district": district,
            "interest_type": "location_tracking",  # 새로운 타입
            "treasure_hunt_count": 0
        }
        
        db.table("anonymous_location_logs").insert(log_data).execute()
        
        logger.debug(f"Periodic location log saved: user_id={user_id[:8]}..., lat={user_latitude}, lon={user_longitude}, district={district}")
        return True
    
    except Exception as e:
        logger.error(f"Error logging periodic location data: {e}", exc_info=True)
        return False


def get_user_location_history(
    user_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 1000
) -> list:
    """
    사용자의 이동 경로 조회 (시간순)
    
    Args:
        user_id: 사용자 ID
        start_date: 시작 날짜 (YYYY-MM-DD)
        end_date: 종료 날짜 (YYYY-MM-DD)
        limit: 최대 조회 개수
    
    Returns:
        위치 로그 리스트 (시간순)
    """
    try:
        db = get_db()
        anonymous_user_id = anonymize_user_id(user_id)
        
        query = db.table("anonymous_location_logs") \
            .select("*") \
            .eq("anonymous_user_id", anonymous_user_id) \
            .eq("interest_type", "location_tracking") \
            .order("created_at", desc=False) \
            .limit(limit)
        
        if start_date:
            query = query.gte("created_at", start_date)
        if end_date:
            from datetime import datetime, timedelta
            end_datetime = datetime.fromisoformat(end_date) + timedelta(days=1)
            query = query.lt("created_at", end_datetime.isoformat())
        
        result = query.execute()
        
        return result.data if result.data else []
    
    except Exception as e:
        logger.error(f"Error getting user location history: {e}", exc_info=True)
        return []
