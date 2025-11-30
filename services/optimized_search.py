"""Optimized image search service with GPS filtering"""

import logging
from typing import List, Dict, Optional
from services.db import get_db, search_places_by_radius
from services.pinecone_store import search_similar_pinecone
from services.embedding import generate_image_embedding

logger = logging.getLogger(__name__)


def search_with_gps_filter(
    embedding: List[float],
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    radius_km: float = 5.0,
    match_threshold: float = 0.2,  # 임계값 낮춤 (상위 3개 추천이므로)
    match_count: int = 5,
    quest_only: bool = False
) -> List[Dict]:
    """Search with GPS filtering and vector similarity"""
    try:
        logger.info(f"search_with_gps_filter called: lat={latitude}, lon={longitude}, radius={radius_km}, quest_only={quest_only}")

        if latitude and longitude:
            logger.info(f"GPS filtering: {radius_km}km radius")

            nearby_places = search_places_by_radius(
                latitude=latitude,
                longitude=longitude,
                radius_km=radius_km,
                limit_count=100
            )
            logger.info(f"search_places_by_radius returned {len(nearby_places) if nearby_places else 0} places")

            if not nearby_places:
                logger.warning("No nearby places found within radius, falling back to full search")
                # GPS 필터링 실패 시 전체 검색으로 fallback
                return search_similar_pinecone(
                    embedding=embedding,
                    match_threshold=match_threshold,
                    match_count=match_count
                )

            nearby_place_ids = [p['id'] for p in nearby_places]
            logger.info(f"Found {len(nearby_place_ids)} nearby places")

            if quest_only:
                db = get_db()
                quest_result = db.table("quests") \
                    .select("place_id") \
                    .eq("is_active", True) \
                    .in_("place_id", nearby_place_ids) \
                    .execute()

                quest_place_ids = [q['place_id'] for q in quest_result.data]
                logger.info(f"Filtered to {len(quest_place_ids)} quest places")

                if not quest_place_ids:
                    logger.warning("No quest places nearby, falling back to all quests")
                    # Quest 필터링 실패 시 전체 quest 검색으로 fallback
                    db = get_db()
                    all_quest_result = db.table("quests") \
                        .select("place_id") \
                        .eq("is_active", True) \
                        .execute()
                    all_quest_place_ids = [q['place_id'] for q in all_quest_result.data]

                    results = search_similar_pinecone(
                        embedding=embedding,
                        match_threshold=match_threshold,
                        match_count=match_count * 3
                    )

                    filtered_results = [
                        r for r in results
                        if r.get('place', {}).get('id') in all_quest_place_ids
                    ][:match_count]

                    logger.info(f"Final results (fallback): {len(filtered_results)}")
                    return filtered_results

                filter_ids = quest_place_ids
            else:
                filter_ids = nearby_place_ids

            logger.info(f"Vector search with {len(filter_ids)} candidates")

            results = search_similar_pinecone(
                embedding=embedding,
                match_threshold=match_threshold,
                match_count=match_count * 3
            )
            logger.info(f"Pinecone returned {len(results)} results")

            # 디버깅: 첫 몇 개 결과의 place_id 확인
            if results:
                sample_ids = [r.get('place', {}).get('id') for r in results[:3]]
                logger.info(f"Sample result place_ids: {sample_ids}")
                logger.info(f"Filter has {len(filter_ids)} ids, first few: {filter_ids[:5] if len(filter_ids) > 0 else []}")

            filtered_results = [
                r for r in results
                if r.get('place', {}).get('id') in filter_ids
            ][:match_count]

            logger.info(f"Final results after filtering: {len(filtered_results)}")

            # GPS 필터링 후 결과가 없으면 GPS 무시하고 전체에서 검색
            if len(filtered_results) == 0:
                logger.warning("No results after GPS filtering, searching without GPS filter")
                if quest_only:
                    # Quest만 검색
                    db = get_db()
                    all_quest_result = db.table("quests") \
                        .select("place_id") \
                        .eq("is_active", True) \
                        .execute()
                    all_quest_place_ids = [q['place_id'] for q in all_quest_result.data]

                    unfiltered_results = [
                        r for r in results
                        if r.get('place', {}).get('id') in all_quest_place_ids
                    ][:match_count]
                    logger.info(f"Results without GPS filter (quest only): {len(unfiltered_results)}")
                    return unfiltered_results
                else:
                    # 모든 place 검색
                    logger.info(f"Results without GPS filter (all places): {len(results[:match_count])}")
                    return results[:match_count]

            return filtered_results

        else:
            logger.info("Full vector search")
            return search_similar_pinecone(
                embedding=embedding,
                match_threshold=match_threshold,
                match_count=match_count
            )
    
    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        return []


def search_similar_with_optimization(
    image_bytes: bytes,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    radius_km: float = 5.0,
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
