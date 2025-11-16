"""Place Recommendation Service"""

import logging
import math
from typing import List, Dict, Optional
from services.embedding import generate_image_embedding
from services.pinecone_store import search_similar_pinecone, fetch_vector_by_id

logger = logging.getLogger(__name__)


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance using Haversine formula (returns km)"""
    R = 6371
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_lat / 2) ** 2 + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * 
         math.sin(delta_lon / 2) ** 2)
    c = 2 * math.asin(math.sqrt(a))
    
    distance = R * c
    return round(distance, 2)


def calculate_category_score(query_category: str, place_category: str) -> float:
    """Calculate category matching score"""
    if query_category == place_category:
        return 1.0
    
    similar_groups = [
        {"역사유적", "문화재", "궁궐", "유적지"},
        {"관광지", "명소", "전망대"},
        {"문화마을", "한옥마을", "전통마을"},
        {"종교시설", "사찰", "성당", "교회"},
        {"광장", "공원", "야외공간"},
    ]
    
    for group in similar_groups:
        if query_category in group and place_category in group:
            return 0.7
    
    return 0.5


def recommend_places(
    image_bytes: bytes,
    category: str,
    top_k: int = 5,
    threshold: float = 0.7,
    place_id: Optional[str] = None,
    gps: Optional[Dict[str, float]] = None,
    context: str = "search"
) -> Dict:
    """Recommend places based on image similarity and category"""
    logger.info(f"Recommendation request - category: {category}, context: {context}")
    
    try:
        embedding = generate_image_embedding(image_bytes)
        if not embedding:
            return {
                "success": False,
                "error": "Failed to generate image embedding",
                "recommendations": []
            }
        
        logger.info(f"Image embedding generated: {len(embedding)} dimensions")
        
        filter_dict = {"category": {"$eq": category}}
        
        if place_id:
            filter_dict["place_id"] = {"$ne": place_id}
            logger.info(f"Excluding place_id: {place_id}")
        
        search_count = top_k * 3
        results = search_similar_pinecone(
            embedding=embedding,
            match_threshold=0.5,
            match_count=search_count,
            filter_dict=filter_dict
        )
        
        logger.info(f"Found {len(results)} candidates from Pinecone")
        
        if not results:
            return {
                "success": True,
                "message": "No matching places found",
                "recommendations": [],
                "count": 0
            }
        
        recommendations = []
        for result in results:
            metadata = result["metadata"]
            
            image_similarity = result["similarity"]
            place_category = metadata.get("category", "")
            category_match = calculate_category_score(category, place_category)
            final_score = image_similarity * category_match
            
            if final_score < threshold:
                continue
            
            recommendation = {
                "place_id": metadata.get("place_id"),
                "name": metadata.get("place_name", "Unknown"),
                "name_en": metadata.get("name_en", ""),
                "category": place_category,
                "image_similarity": round(image_similarity, 3),
                "category_match": round(category_match, 3),
                "final_score": round(final_score, 3),
                "location": {
                    "latitude": metadata.get("latitude"),
                    "longitude": metadata.get("longitude")
                },
                "image_url": metadata.get("image_url", ""),
                "address": metadata.get("address", ""),
                "description": metadata.get("description", "")
            }
            
            if gps and metadata.get("latitude") and metadata.get("longitude"):
                distance = calculate_distance(
                    gps["latitude"], 
                    gps["longitude"],
                    metadata["latitude"],
                    metadata["longitude"]
                )
                recommendation["distance_km"] = distance
            
            recommendations.append(recommendation)
        
        recommendations.sort(key=lambda x: x["final_score"], reverse=True)
        recommendations = recommendations[:top_k]
        
        logger.info(f"Returning {len(recommendations)} recommendations")
        
        if len(recommendations) == 0:
            return {
                "success": True,
                "message": "No places meet the minimum confidence score",
                "recommendations": [],
                "count": 0,
                "threshold": threshold
            }
        
        return {
            "success": True,
            "recommendations": recommendations,
            "count": len(recommendations),
            "threshold": threshold,
            "context": context
        }
    
    except Exception as e:
        logger.error(f"Recommendation error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "recommendations": []
        }


def recommend_similar_to_place(
    place_id: str,
    top_k: int = 3,
    threshold: float = 0.7
) -> Dict:
    """Recommend similar places to a given place"""
    logger.info(f"Similar place recommendation for: {place_id}")
    
    try:
        place_vector = fetch_vector_by_id(f"vec-{place_id}")
        
        if not place_vector:
            logger.warning(f"Place vector not found: {place_id}")
            return {
                "success": False,
                "error": "Place not found in vector database",
                "recommendations": []
            }
        
        embedding = place_vector["values"]
        metadata = place_vector["metadata"]
        category = metadata.get("category", "")
        
        logger.info(f"Found place: {metadata.get('place_name')} (category: {category})")
        
        filter_dict = {
            "category": {"$eq": category},
            "place_id": {"$ne": place_id}
        }
        
        results = search_similar_pinecone(
            embedding=embedding,
            match_threshold=threshold,
            match_count=top_k * 2,
            filter_dict=filter_dict
        )
        
        logger.info(f"Found {len(results)} similar places")
        
        recommendations = []
        for result in results[:top_k]:
            meta = result["metadata"]
            recommendations.append({
                "place_id": meta.get("place_id"),
                "name": meta.get("place_name", "Unknown"),
                "name_en": meta.get("name_en", ""),
                "category": meta.get("category", ""),
                "similarity": round(result["similarity"], 3),
                "location": {
                    "latitude": meta.get("latitude"),
                    "longitude": meta.get("longitude")
                },
                "image_url": meta.get("image_url", "")
            })
        
        return {
            "success": True,
            "source_place": {
                "place_id": place_id,
                "name": metadata.get("place_name"),
                "category": category
            },
            "recommendations": recommendations,
            "count": len(recommendations)
        }
    
    except Exception as e:
        logger.error(f"Similar place recommendation error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "recommendations": []
        }

