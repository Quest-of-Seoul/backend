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
    match_threshold: float = 0.65,
    match_count: int = 5,
    quest_only: bool = False
) -> List[Dict]:
    """Search with GPS filtering and vector similarity"""
    try:
        if latitude and longitude:
            logger.info(f"GPS filtering: {radius_km}km radius")
            
            nearby_places = search_places_by_radius(
                latitude=latitude,
                longitude=longitude,
                radius_km=radius_km,
                limit_count=100
            )
            
            if not nearby_places:
                logger.warning("No nearby places found")
                return []
            
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
                    logger.warning("No quest places nearby")
                    return []
                
                filter_ids = quest_place_ids
            else:
                filter_ids = nearby_place_ids
            
            logger.info(f"Vector search with {len(filter_ids)} candidates")
            
            results = search_similar_pinecone(
                embedding=embedding,
                match_threshold=match_threshold,
                match_count=match_count * 3
            )
            
            filtered_results = [
                r for r in results
                if r.get('place', {}).get('id') in filter_ids
            ][:match_count]
            
            logger.info(f"Final results: {len(filtered_results)}")
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
    match_threshold: float = 0.65,
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
