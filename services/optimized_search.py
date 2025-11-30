"""Optimized image search service"""

import logging
import math
from typing import List, Dict, Optional
from services.db import get_db
from services.pinecone_store import search_similar_pinecone
from services.embedding import generate_image_embedding

logger = logging.getLogger(__name__)


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points using Haversine formula (returns km)"""
    R = 6371
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def search_with_gps_filter(
    embedding: List[float],
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    start_latitude: Optional[float] = None,
    start_longitude: Optional[float] = None,
    radius_km: float = 5.0,  # 사용 안 함 (하위 호환성 유지)
    match_threshold: float = 0.2,  # 임계값 낮춤 (상위 3개 추천이므로)
    match_count: int = 5,
    quest_only: bool = False
) -> List[Dict]:
    """
    Image similarity search without GPS filtering.
    Results are sorted by distance from start location (or current location if start not provided).
    """
    try:
        # 출발 위치가 있으면 사용, 없으면 현재 위치 사용
        anchor_lat = start_latitude if start_latitude is not None else latitude
        anchor_lon = start_longitude if start_longitude is not None else longitude
        
        logger.info(f"Image similarity search: quest_only={quest_only}, anchor=({anchor_lat}, {anchor_lon})")

        # 이미지 유사도만으로 검색 (GPS 필터링 제거)
        results = search_similar_pinecone(
            embedding=embedding,
            match_threshold=match_threshold,
            match_count=match_count * 3  # 더 많이 가져와서 필터링 후 정렬
        )
        logger.info(f"Pinecone returned {len(results)} results")

        # quest_only 필터링
        if quest_only:
            db = get_db()
            all_quest_result = db.table("quests") \
                .select("place_id") \
                .eq("is_active", True) \
                .execute()
            all_quest_place_ids = set([q['place_id'] for q in all_quest_result.data])
            
            results = [
                r for r in results
                if r.get('place', {}).get('id') in all_quest_place_ids
            ]
            logger.info(f"Filtered to {len(results)} quest places")

        # 출발 위치(또는 현재 위치) 기준으로 거리 계산 및 정렬
        if anchor_lat is not None and anchor_lon is not None:
            for result in results:
                place = result.get('place', {})
                if place and place.get('latitude') and place.get('longitude'):
                    distance = haversine_distance(
                        anchor_lat, anchor_lon,
                        float(place['latitude']), float(place['longitude'])
                    )
                    result['distance_from_anchor'] = distance
            
            # 거리순 정렬
            results.sort(key=lambda x: x.get('distance_from_anchor', float('inf')))
            logger.info(f"Sorted {len(results)} results by distance from anchor")
        else:
            logger.info("No anchor location provided, using similarity order")

        # 최종 결과 반환
        final_results = results[:match_count]
        logger.info(f"Final results: {len(final_results)}")
        
        return final_results
    
    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        return []


def search_similar_with_optimization(
    image_bytes: bytes,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    start_latitude: Optional[float] = None,
    start_longitude: Optional[float] = None,
    radius_km: float = 5.0,  # 사용 안 함 (하위 호환성 유지)
    match_threshold: float = 0.2,  # 임계값 낮춤 (상위 3개 추천이므로)
    match_count: int = 5,
    quest_only: bool = False
) -> List[Dict]:
    """Image similarity search with optimization"""
    embedding = generate_image_embedding(image_bytes)
    
    if not embedding:
        logger.error("Embedding generation failed")
        return []
    
    return search_with_gps_filter(
        embedding=embedding,
        latitude=latitude,
        longitude=longitude,
        start_latitude=start_latitude,
        start_longitude=start_longitude,
        radius_km=radius_km,
        match_threshold=match_threshold,
        match_count=match_count,
        quest_only=quest_only
    )


def get_quest_places_by_category(category: str, limit: int = 20) -> List[Dict]:
    """Get quest places by category"""
    try:
        db = get_db()
        
        result = db.rpc(
            "get_places_with_quests",
            {
                "category_filter": category,
                "limit_count": limit
            }
        ).execute()
        
        return result.data if result.data else []
    
    except Exception as e:
        logger.error(f"Error getting quest places: {e}", exc_info=True)
        return []


def search_nearby_quests(
    latitude: float,
    longitude: float,
    radius_km: float = 5.0,
    limit: int = 10
) -> List[Dict]:
    """Search nearby quests"""
    try:
        db = get_db()
        
        result = db.rpc(
            "search_nearby_quests",
            {
                "lat": latitude,
                "lon": longitude,
                "radius_km": radius_km,
                "limit_count": limit
            }
        ).execute()
        
        return result.data if result.data else []
    
    except Exception as e:
        logger.error(f"Error searching nearby quests: {e}", exc_info=True)
        return []
