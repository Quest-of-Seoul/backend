"""RAG 텍스트 임베딩 저장 스크립트

모든 활성 장소의 RAG 텍스트를 임베딩으로 변환하여 Pinecone에 저장합니다.
"""

import os
import sys
import logging
from dotenv import load_dotenv

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from typing import Optional
from services.db import get_db
from services.embedding import generate_text_embedding
from services.pinecone_store import upsert_text_embedding, get_index_stats

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_rag_text_from_place(place: dict) -> str:
    """장소 데이터에서 RAG 텍스트 추출"""
    # metadata->>'rag_text' 우선 사용
    metadata = place.get("metadata") or {}
    if isinstance(metadata, dict):
        rag_text = metadata.get("rag_text")
        if rag_text:
            return rag_text
    
    # rag_text가 없으면 description과 기타 정보로 구성
    parts = []
    
    name = place.get("name", "")
    if name:
        parts.append(f"[{name}]")
    
    category = place.get("category", "")
    if category:
        parts.append(f"[카테고리] {category}")
    
    description = place.get("description", "")
    if description:
        parts.append("")
        parts.append("[설명]")
        parts.append(description)
    
    address = place.get("address", "")
    if address:
        parts.append("")
        parts.append(f"[주소] {address}")
    
    district = place.get("district", "")
    if district:
        parts.append(f"[행정구역] {district}")
    
    rag_text = "\n".join(parts)
    
    # 최대 길이 제한
    max_length = 2000
    if len(rag_text) > max_length:
        rag_text = rag_text[:max_length] + "..."
    
    return rag_text


def update_rag_embeddings(batch_size: int = 10, limit: Optional[int] = None):
    """모든 활성 장소의 RAG 텍스트 임베딩 저장"""
    try:
        db = get_db()
        
        # 활성 장소 조회
        query = db.table("places").select("*").eq("is_active", True)
        
        if limit:
            query = query.limit(limit)
        
        result = query.execute()
        
        if not result.data:
            logger.warning("No active places found")
            return
        
        places = result.data
        total = len(places)
        logger.info(f"Processing {total} places...")
        
        success_count = 0
        error_count = 0
        skipped_count = 0
        
        for i, place in enumerate(places, 1):
            place_id = place.get("id")
            place_name = place.get("name", "Unknown")
            
            try:
                # RAG 텍스트 추출
                rag_text = get_rag_text_from_place(place)
                
                if not rag_text or len(rag_text.strip()) < 10:
                    logger.warning(f"[{i}/{total}] Skipping {place_name}: No RAG text")
                    skipped_count += 1
                    continue
                
                # 텍스트 임베딩 생성
                logger.info(f"[{i}/{total}] Processing {place_name}...")
                text_embedding = generate_text_embedding(rag_text)
                
                if not text_embedding:
                    logger.error(f"[{i}/{total}] Failed to generate embedding for {place_name}")
                    error_count += 1
                    continue
                
                # Pinecone에 저장
                vector_id = upsert_text_embedding(
                    place_id=place_id,
                    text_embedding=text_embedding,
                    rag_text=rag_text,
                    metadata={
                        "name": place_name,
                        "category": place.get("category", ""),
                        "district": place.get("district", "")
                    }
                )
                
                if vector_id:
                    success_count += 1
                    logger.info(f"[{i}/{total}] ✓ Saved: {place_name} ({vector_id})")
                else:
                    error_count += 1
                    logger.error(f"[{i}/{total}] ✗ Failed to save: {place_name}")
                
                # 배치 처리 중간 통계
                if i % batch_size == 0:
                    logger.info(f"Progress: {i}/{total} (Success: {success_count}, Error: {error_count}, Skipped: {skipped_count})")
            
            except Exception as e:
                error_count += 1
                logger.error(f"[{i}/{total}] Error processing {place_name}: {e}", exc_info=True)
        
        # 최종 통계
        logger.info("=" * 60)
        logger.info("Final Statistics:")
        logger.info(f"  Total: {total}")
        logger.info(f"  Success: {success_count}")
        logger.info(f"  Error: {error_count}")
        logger.info(f"  Skipped: {skipped_count}")
        logger.info("=" * 60)
        
        # Pinecone 인덱스 통계
        try:
            stats = get_index_stats()
            logger.info(f"Pinecone Index Stats: {stats['total_vectors']} vectors")
        except Exception as e:
            logger.warning(f"Failed to get index stats: {e}")
    
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Update RAG text embeddings for all active places")
    parser.add_argument("--limit", type=int, help="Limit number of places to process")
    parser.add_argument("--batch-size", type=int, default=10, help="Batch size for progress logging")
    
    args = parser.parse_args()
    
    logger.info("Starting RAG embeddings update...")
    update_rag_embeddings(batch_size=args.batch_size, limit=args.limit)
    logger.info("RAG embeddings update completed!")
