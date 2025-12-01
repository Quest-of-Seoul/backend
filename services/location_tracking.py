"""Anonymous location tracking service"""

import hashlib
import logging
from typing import Optional, Dict, Any
from services.db import get_db

logger = logging.getLogger(__name__)


def anonymize_user_id(user_id: str) -> str:
    return hashlib.sha256(user_id.encode()).hexdigest()


def calculate_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    import math
    
    R = 6371
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
    try:
        if quest_id and user_latitude and user_longitude:
            db = get_db()
            
            quest_result = db.table("quests").select("latitude, longitude, place_id").eq("id", quest_id).single().execute()
            
            if not quest_result.data:
                logger.warning(f"Quest {quest_id} not found")
                return False
            
            quest_lat = float(quest_result.data["latitude"])
            quest_lon = float(quest_result.data["longitude"])
            quest_place_id = quest_result.data.get("place_id")
            
            distance_km = calculate_distance_km(
                user_latitude, user_longitude,
                quest_lat, quest_lon
            )
            
            if distance_km > distance_threshold_km:
                logger.info(f"User {user_id[:8]}... is {distance_km:.2f}km away from quest {quest_id}, skipping log")
                return False
            
            district = None
            if quest_place_id:
                place_result = db.table("places").select("district").eq("id", quest_place_id).single().execute()
                if place_result.data:
                    district = place_result.data.get("district")
            
            anonymous_user_id = anonymize_user_id(user_id)
            
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
            
            try:
                db.table("anonymous_location_logs").insert(log_data).execute()
                logger.info(f"Location log saved: quest_id={quest_id}, district={district}, distance={distance_km:.2f}km")
            except Exception as db_error:
                logger.warning(f"Failed to save location log {db_error}")
            
            return True
        
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
    count = 0
    for quest_id in recommended_quest_ids:
        try:
            db = get_db()
            quest_result = db.table("quests").select("place_id, latitude, longitude").eq("id", quest_id).single().execute()
            
            if quest_result.data:
                place_id = quest_result.data.get("place_id")
                quest_lat = quest_result.data.get("latitude")
                quest_lon = quest_result.data.get("longitude")
                
                district = None
                if place_id:
                    place_result = db.table("places").select("district").eq("id", place_id).single().execute()
                    if place_result.data:
                        district = place_result.data.get("district")
                
                distance_km = None
                if user_latitude and user_longitude and quest_lat and quest_lon:
                    distance_km = calculate_distance_km(
                        user_latitude, user_longitude,
                        float(quest_lat), float(quest_lon)
                    )
                
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
                
                try:
                    db.table("anonymous_location_logs").insert(log_data).execute()
                    count += 1
                except Exception as db_error:
                    logger.warning(f"Failed to save location log: {db_error}")
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
    try:
        db = get_db()
        
        anonymous_user_id = anonymize_user_id(user_id)
        
        district = None
        
        if place_id:
            place_result = db.table("places").select("district").eq("id", place_id).single().execute()
            if place_result.data:
                district = place_result.data.get("district")
        
        if not district and quest_id:
            quest_result = db.table("quests").select("place_id").eq("id", quest_id).single().execute()
            if quest_result.data:
                quest_place_id = quest_result.data.get("place_id")
                if quest_place_id:
                    place_result = db.table("places").select("district").eq("id", quest_place_id).single().execute()
                    if place_result.data:
                        district = place_result.data.get("district")
        
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
                nearby_place = nearby_places.data[0]
                address = nearby_place.get("address", "")
                if address:
                    import re
                    match = re.search(r'([가-힣]+구)', address)
                    if match:
                        district = match.group(1)
                    else:
                        match = re.search(r'([A-Za-z]+-gu)', address, re.IGNORECASE)
                        if match:
                            district = match.group(1)
        
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
        
        log_data = {
            "anonymous_user_id": anonymous_user_id,
            "quest_id": quest_id,
            "place_id": place_id,
            "user_latitude": float(user_latitude),
            "user_longitude": float(user_longitude),
            "start_latitude": None,
            "start_longitude": None,
            "distance_from_quest_km": round(distance_from_quest_km, 3) if distance_from_quest_km else None,
            "district": district,
            "interest_type": "location_tracking",
            "treasure_hunt_count": 0
        }
        
        try:
            db.table("anonymous_location_logs").insert(log_data).execute()
        except Exception as db_error:
            logger.warning(f"Failed to save location log: {db_error}")
        
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
