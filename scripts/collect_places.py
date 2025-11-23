"""Place Collection Script"""

import os
import sys
import logging
import time
from dotenv import load_dotenv
from typing import List, Dict, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.visit_seoul_api import (
    collect_all_places_by_category as collect_visit_seoul_places,
    get_place_detail as get_visit_seoul_detail,
    parse_visit_seoul_place,
    map_category_to_visit_seoul_sn
)
from services.place_parser import merge_place_data
from services.db import save_place, create_quest_from_place
from services.image_utils import download_image, hash_image
from services.embedding import generate_image_embedding
from services.pinecone_store import upsert_pinecone
import uuid

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_image_embedding_for_place(place_id: str, image_url: str) -> bool:
    """
    장소의 이미지 임베딩 생성 및 Pinecone 저장
    
    Args:
        place_id: 장소 ID
        image_url: 이미지 URL
    
    Returns:
        성공 여부
    """
    if not image_url:
        logger.warning(f"No image URL for place: {place_id}")
        return False
    
    try:
        # 이미지 다운로드
        image_bytes = download_image(image_url)
        if not image_bytes:
            logger.warning(f"Failed to download image for place: {place_id}")
            return False
        
        # 임베딩 생성
        embedding = generate_image_embedding(image_bytes)
        if not embedding:
            logger.warning(f"Failed to generate embedding for place: {place_id}")
            return False
        
        # Pinecone에 저장
        vector_id = f"vec-{place_id}"
        image_hash = hash_image(image_bytes)
        
        # 장소 정보 가져오기
        from services.db import get_place_by_id
        place = get_place_by_id(place_id)
        if not place:
            logger.warning(f"Place not found: {place_id}")
            return False
        
        metadata = {
            "place_id": place_id,
            "place_name": place.get("name", ""),
            "category": place.get("category", ""),
            "image_url": image_url,
            "image_hash": image_hash,
            "source": place.get("source", "visit_seoul"),
            "latitude": float(place.get("latitude", 0)) if place.get("latitude") else None,
            "longitude": float(place.get("longitude", 0)) if place.get("longitude") else None
        }
        
        result = upsert_pinecone(vector_id, embedding, metadata)
        if result:
            logger.info(f"Image embedding saved for place: {place_id}")
            return True
        else:
            logger.warning(f"Failed to save embedding to Pinecone for place: {place_id}")
            return False
    
    except Exception as e:
        logger.error(f"Error creating image embedding: {e}", exc_info=True)
        return False


def collect_category_places(
    category: str,
    max_places: int = 50,
    area_code: str = "1",
    delay_between_api_calls: float = 0.5,
    create_embeddings: bool = True
) -> Dict:
    """
    카테고리별 장소 수집 및 저장
    
    Args:
        category: Quest of Seoul 테마 (Attraction, Culture 등)
        max_places: 최대 수집 장소 수
        area_code: 지역코드 (서울: 1)
        delay_between_api_calls: API 호출 간 지연 시간 (초)
    
    Returns:
        수집 결과 통계
    """
    logger.info(f"=== Starting collection for category: {category} ===")
    
    stats = {
        "category": category,
        "visit_seoul_places_collected": 0,
        "places_saved": 0,
        "quests_created": 0,
        "embeddings_created": 0,
        "errors": []
    }
    
    try:
        logger.info(f"Step 1: Collecting VISIT SEOUL places for {category}...")
        # 카테고리를 VISIT SEOUL category_sn 리스트로 매핑
        from services.visit_seoul_api import map_category_to_visit_seoul_sn
        visit_seoul_category_sns = map_category_to_visit_seoul_sn(category)
        
        visit_seoul_items = []
        if visit_seoul_category_sns:
            logger.info(f"Mapped category '{category}' to {len(visit_seoul_category_sns)} VISIT SEOUL category_sn(s): {visit_seoul_category_sns}")
            # 각 category_sn에 대해 장소 수집
            for category_sn in visit_seoul_category_sns:
                items = collect_visit_seoul_places(
                    category_sn=category_sn,
                    lang_code_id="en",  # 영문으로 수집
                    max_places=max_places * 2,  # 매칭을 위해 더 많이 수집
                    delay_between_pages=delay_between_api_calls
                )
                visit_seoul_items.extend(items)
                logger.info(f"Collected {len(items)} places for category_sn: {category_sn}")
        else:
            logger.warning(f"Could not map category '{category}' to VISIT SEOUL category_sn, collecting all categories")
            visit_seoul_items = collect_visit_seoul_places(
                category_sn=None,  # 모든 카테고리 수집
                lang_code_id="en",  # 영문으로 수집
                max_places=max_places * 2,  # 매칭을 위해 더 많이 수집
                delay_between_pages=delay_between_api_calls
            )
        stats["visit_seoul_places_collected"] = len(visit_seoul_items)
        logger.info(f"Collected {len(visit_seoul_items)} VISIT SEOUL places")
        
        logger.info("Step 2: Fetching VISIT SEOUL place details...")
        visit_seoul_places = []
        for idx, item in enumerate(visit_seoul_items):
            try:
                content_id = item.get("cid") or item.get("contentId") or item.get("content_id") or item.get("id")
                
                if not content_id:
                    logger.warning(f"Skipping VISIT SEOUL item {idx + 1}: missing cid")
                    continue
                
                # 상세 정보 조회
                detail = get_visit_seoul_detail(content_id)
                time.sleep(delay_between_api_calls)
                
                # 파싱
                vs_place = parse_visit_seoul_place(item, detail)
                visit_seoul_places.append(vs_place)
                
                if (idx + 1) % 10 == 0:
                    logger.info(f"Processed {idx + 1}/{len(visit_seoul_items)} VISIT SEOUL places")
                
            except Exception as e:
                error_msg = f"Error processing VISIT SEOUL item {idx + 1}: {e}"
                logger.error(error_msg, exc_info=True)
                stats["errors"].append(error_msg)
        
        logger.info(f"Processed {len(visit_seoul_places)} VISIT SEOUL places with details")
        
        logger.info("Step 3: Saving places...")
        saved_count = 0
        quest_count = 0
        
        # VISIT SEOUL 장소 저장
        for vs_place in visit_seoul_places:
            try:
                # 데이터 통합 (VISIT SEOUL만 사용)
                merged_data = merge_place_data(None, vs_place, category=category)
                
                # DB 저장
                place_id = save_place(merged_data)
                if place_id:
                    saved_count += 1
                    logger.info(f"Saved place: {place_id} ({merged_data['name']})")
                    
                    # 퀘스트 생성
                    quest_id = create_quest_from_place(place_id)
                    if quest_id:
                        quest_count += 1
                        logger.info(f"Created quest: {quest_id} for place: {place_id}")
                    
                    # 이미지 임베딩 생성
                    if create_embeddings and merged_data.get("image_url"):
                        if create_image_embedding_for_place(place_id, merged_data["image_url"]):
                            stats["embeddings_created"] += 1
                
            except Exception as e:
                error_msg = f"Error saving place: {e}"
                logger.error(error_msg, exc_info=True)
                stats["errors"].append(error_msg)
        
        stats["places_saved"] = saved_count
        stats["quests_created"] = quest_count
        
        logger.info(f"=== Collection completed for {category} ===")
        logger.info(f"Summary: {saved_count} places saved, {quest_count} quests created, {stats['embeddings_created']} embeddings created")
        
    except Exception as e:
        error_msg = f"Fatal error in collection: {e}"
        logger.error(error_msg, exc_info=True)
        stats["errors"].append(error_msg)
    
    return stats


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Collect places from VISIT SEOUL API")
    parser.add_argument(
        "--category",
        type=str,
        required=True,
        choices=["Attractions", "History", "Culture", "Nature", "Food", "Drinks", "Shopping", "Activities", "Events"],
        help="Category to collect"
    )
    parser.add_argument(
        "--max-places",
        type=int,
        default=50,
        help="Maximum number of places to collect (default: 50)"
    )
    parser.add_argument(
        "--area-code",
        type=str,
        default="1",
        help="Area code (Seoul: 1, default: 1)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Delay between API calls in seconds (default: 0.5)"
    )
    parser.add_argument(
        "--no-embeddings",
        action="store_true",
        help="Skip image embedding creation"
    )
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("Quest of Seoul - Place Collection Script")
    logger.info("=" * 60)
    logger.info(f"Category: {args.category}")
    logger.info(f"Max places: {args.max_places}")
    logger.info(f"Area code: {args.area_code}")
    logger.info(f"API call delay: {args.delay}s")
    logger.info("=" * 60)
    
    if not os.getenv("VISIT_SEOUL_API_KEY"):
        logger.error("VISIT_SEOUL_API_KEY environment variable is required")
        sys.exit(1)
    
    stats = collect_category_places(
        category=args.category,
        max_places=args.max_places,
        area_code=args.area_code,
        delay_between_api_calls=args.delay,
        create_embeddings=not args.no_embeddings
    )
    
    logger.info("=" * 60)
    logger.info("Collection Statistics:")
    logger.info(f"  Category: {stats['category']}")
    logger.info(f"  VISIT SEOUL places collected: {stats['visit_seoul_places_collected']}")
    logger.info(f"  Places saved: {stats['places_saved']}")
    logger.info(f"  Quests created: {stats['quests_created']}")
    logger.info(f"  Embeddings created: {stats['embeddings_created']}")
    logger.info(f"  Errors: {len(stats['errors'])}")
    
    if stats['errors']:
        logger.warning("Errors occurred during collection:")
        for error in stats['errors'][:10]:
            logger.warning(f"  - {error}")
        if len(stats['errors']) > 10:
            logger.warning(f"  ... and {len(stats['errors']) - 10} more errors")
    
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
