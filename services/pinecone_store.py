"""Pinecone Vector Store Service"""

from pinecone import Pinecone
import os
import logging
from typing import List, Dict, Optional
from services.db import get_place_by_id

logger = logging.getLogger(__name__)

_pinecone_client = None
_index = None


def get_pinecone_client():
    global _pinecone_client
    
    if _pinecone_client is None:
        api_key = os.getenv("PINECONE_API_KEY")
        if not api_key:
            raise ValueError("PINECONE_API_KEY not set in environment")
        
        _pinecone_client = Pinecone(api_key=api_key)
        logger.info("Pinecone client initialized")
    
    return _pinecone_client


def get_pinecone_index(index_name: str = "quest-of-seoul"):
    global _index
    
    if _index is None:
        pc = get_pinecone_client()
        _index = pc.Index(index_name)
        logger.info(f"Connected to index: {index_name}")
    
    return _index


def search_similar_pinecone(
    embedding: List[float],
    match_threshold: float = 0.7,
    match_count: int = 5,
    filter_dict: Optional[Dict] = None
) -> List[Dict]:
    """Vector similarity search"""
    try:
        index = get_pinecone_index()
        
        query_params = {
            "vector": embedding,
            "top_k": match_count,
            "include_metadata": True
        }
        
        if filter_dict:
            query_params["filter"] = filter_dict
        
        results = index.query(**query_params)
        
        if not results or not results.get('matches'):
            logger.info("No similar images found")
            return []
        
        similar_images = []
        for match in results['matches']:
            score = match.get('score', 0.0)
            
            if score >= match_threshold:
                place_id = match['metadata'].get('place_id')
                
                place = None
                if place_id:
                    place = get_place_by_id(place_id)
                
                similar_images.append({
                    "id": match['id'],
                    "place_id": place_id,
                    "image_url": match['metadata'].get('image_url'),
                    "similarity": score,
                    "place": place
                })
        
        logger.info(f"Found {len(similar_images)} matches (threshold: {match_threshold})")
        return similar_images
    
    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        return []


def upsert_pinecone(
    vector_id: str,
    embedding: List[float],
    metadata: Dict
) -> Optional[str]:
    """Save vector to Pinecone"""
    try:
        index = get_pinecone_index()
        
        if not metadata.get('place_id'):
            logger.warning("place_id not provided in metadata")
        
        if not metadata.get('image_url'):
            logger.warning("image_url not provided in metadata")
        
        index.upsert(
            vectors=[(vector_id, embedding, metadata)],
            namespace=""
        )
        
        logger.info(f"Vector saved: {vector_id[:8]}...")
        return vector_id
    
    except Exception as e:
        logger.error(f"Upsert error: {e}", exc_info=True)
        return None


def upsert_batch_pinecone(vectors: List[tuple], batch_size: int = 100) -> int:
    """Batch upsert vectors"""
    try:
        index = get_pinecone_index()
        
        total = len(vectors)
        success_count = 0
        
        for i in range(0, total, batch_size):
            batch = vectors[i:i+batch_size]
            
            try:
                index.upsert(vectors=batch, namespace="")
                success_count += len(batch)
                logger.info(f"Batch {i//batch_size + 1}: {len(batch)} vectors upserted")
            
            except Exception as batch_error:
                logger.error(f"Batch {i//batch_size + 1} failed: {batch_error}")
        
        logger.info(f"Total upserted: {success_count}/{total}")
        return success_count
    
    except Exception as e:
        logger.error(f"Batch upsert error: {e}", exc_info=True)
        return 0


def get_index_stats() -> Dict:
    """Get index statistics"""
    try:
        index = get_pinecone_index()
        stats = index.describe_index_stats()
        
        result = {
            "total_vectors": int(stats.get('total_vector_count', 0)),
            "dimension": int(stats.get('dimension', 512)),
            "index_fullness": float(stats.get('index_fullness', 0.0))
        }
        
        logger.info(f"Stats: {result['total_vectors']} vectors, {result['dimension']}D")
        return result
    
    except Exception as e:
        logger.error(f"Stats error: {e}", exc_info=True)
        return {
            "total_vectors": 0,
            "dimension": 512,
            "index_fullness": 0.0
        }


def fetch_vector_by_id(vector_id: str) -> Optional[Dict]:
    """Fetch vector by ID"""
    try:
        index = get_pinecone_index()
        result = index.fetch(ids=[vector_id], namespace="")
        
        vectors = getattr(result, 'vectors', None)
        
        if not vectors or vector_id not in vectors:
            logger.warning(f"Vector not found: {vector_id}")
            return None
        
        vector_data = vectors[vector_id]
        logger.info(f"Vector fetched: {vector_id}")
        
        return {
            "id": vector_id,
            "values": getattr(vector_data, 'values', []),
            "metadata": getattr(vector_data, 'metadata', {})
        }
    
    except Exception as e:
        logger.error(f"Fetch error: {e}", exc_info=True)
        return None
