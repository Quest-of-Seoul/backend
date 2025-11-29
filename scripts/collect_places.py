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
    map_category_to_visit_seoul_sn,
    CATEGORY_DATASET_INFO
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

def determine_target_count(category: str, requested_max: Optional[int]) -> Optional[int]:
    """
    CLI 입력을 고려해 목표 수집 개수를 계산
    """
    if requested_max is not None:
        if requested_max <= 0:
            return None
        return requested_max
    
    return None  # 기본값: 제한 없음


def normalize_cid(item: Dict) -> Optional[str]:
    """VISIT SEOUL 아이템에서 CID 추출"""
    return (
        item.get("cid")
        or item.get("contentId")
        or item.get("content_id")
        or item.get("id")
    )


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
    max_places: Optional[int] = None,
    area_code: str = "1",
    delay_between_api_calls: float = 1.0,
    create_embeddings: bool = True,
    lang_code_id: str = "en"
) -> Dict:
    """
    카테고리별 장소 수집 및 저장
    
    Args:
        category: Quest of Seoul 테마 (Attraction, Culture 등)
        max_places: 최대 수집 장소 수 (None이면 카테고리별 전체 수집)
        area_code: 지역코드 (서울: 1)
        delay_between_api_calls: API 호출 간 지연 시간 (초)
        create_embeddings: 이미지 임베딩 생성 여부
        lang_code_id: VISIT SEOUL 언어 코드
    
    Returns:
        수집 결과 통계
    """
    logger.info(f"=== Starting collection for category: {category} ===")
    
    target_total = determine_target_count(category, max_places)
    target_desc = target_total if target_total else "ALL"
    logger.info(f"Configured target for {category}: {target_desc} item(s) (lang: {lang_code_id})")
    
    stats = {
        "category": category,
        "lang_code_id": lang_code_id,
        "expected_total": None,
        "visit_seoul_places_collected": 0,
        "places_saved": 0,
        "quests_created": 0,
        "embeddings_created": 0,
        "errors": []
    }
    stats["expected_total"] = target_total
    
    try:
        logger.info(f"Step 1: Collecting VISIT SEOUL places for {category}...")
        # 카테고리를 VISIT SEOUL category_sn 리스트로 매핑
        from services.visit_seoul_api import map_category_to_visit_seoul_sn
        visit_seoul_category_sns = map_category_to_visit_seoul_sn(category, lang_code_id=lang_code_id)
        
        visit_seoul_items_by_cid: Dict[str, Dict] = {}
        if visit_seoul_category_sns:
            logger.info(f"Mapped category '{category}' to {len(visit_seoul_category_sns)} VISIT SEOUL category_sn(s): {visit_seoul_category_sns}")
            # 각 category_sn에 대해 장소 수집
            for category_sn in visit_seoul_category_sns:
                if target_total and len(visit_seoul_items_by_cid) >= target_total:
                    break
                
                per_sn_limit = None
                if target_total:
                    remaining = max(target_total - len(visit_seoul_items_by_cid), 0)
                    if remaining == 0:
                        break
                    per_sn_limit = remaining
                
                items = collect_visit_seoul_places(
                    category_sn=category_sn,
                    lang_code_id=lang_code_id,
                    max_places=per_sn_limit,
                    delay_between_pages=delay_between_api_calls
                )
                
                added = 0
                for item in items:
                    cid = normalize_cid(item)
                    if not cid:
                        continue
                    if cid not in visit_seoul_items_by_cid:
                        visit_seoul_items_by_cid[cid] = item
                        added += 1
                
                logger.info(
                    "Collected %d new places for category_sn: %s (unique total: %d)",
                    added,
                    category_sn,
                    len(visit_seoul_items_by_cid)
                )
        else:
            logger.warning(f"Could not map category '{category}' to VISIT SEOUL category_sn, collecting all categories")
            items = collect_visit_seoul_places(
                category_sn=None,  # 모든 카테고리 수집
                lang_code_id=lang_code_id,
                max_places=target_total,
                delay_between_pages=delay_between_api_calls
            )
            for item in items:
                cid = normalize_cid(item)
                if not cid:
                    continue
                visit_seoul_items_by_cid[cid] = item
        
        visit_seoul_items = list(visit_seoul_items_by_cid.values())
        stats["visit_seoul_places_collected"] = len(visit_seoul_items)
        logger.info(f"Collected {len(visit_seoul_items)} unique VISIT SEOUL places")
        
        if target_total and len(visit_seoul_items) < target_total:
            logger.warning(
                "Collected fewer places (%d) than expected target (%d) for category %s",
                len(visit_seoul_items),
                target_total,
                category
            )
        
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
                vs_place["category_label"] = category
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
        logger.info(
            "Summary: %d places saved, %d quests created, %d embeddings created (expected target: %s, collected: %d)",
            saved_count,
            quest_count,
            stats["embeddings_created"],
            target_total if target_total else "ALL",
            stats["visit_seoul_places_collected"]
        )
        
    except Exception as e:
        error_msg = f"Fatal error in collection: {e}"
        logger.error(error_msg, exc_info=True)
        stats["errors"].append(error_msg)
    
    return stats


def collect_all_categories(
    max_places_per_category: Optional[int] = None,
    area_code: str = "1",
    delay_between_api_calls: float = 1.0,
    create_embeddings: bool = True,
    lang_code_id: str = "en",
    delay_between_categories: float = 2.0
) -> Dict:
    """
    모든 카테고리 자동 수집
    
    Args:
        max_places_per_category: 카테고리별 최대 수집 장소 수
        area_code: 지역코드 (서울: 1)
        delay_between_api_calls: API 호출 간 지연 시간 (초)
        create_embeddings: 이미지 임베딩 생성 여부
        lang_code_id: VISIT SEOUL 언어 코드
        delay_between_categories: 카테고리 간 지연 시간 (초)
    
    Returns:
        전체 수집 결과 통계
    """
    all_categories = list(CATEGORY_DATASET_INFO.keys())
    logger.info(f"=== Starting collection for ALL categories ({len(all_categories)} categories) ===")
    logger.info(f"Categories: {', '.join(all_categories)}")
    
    overall_stats = {
        "total_categories": len(all_categories),
        "categories_processed": 0,
        "categories_succeeded": 0,
        "categories_failed": 0,
        "total_visit_seoul_places_collected": 0,
        "total_places_saved": 0,
        "total_quests_created": 0,
        "total_embeddings_created": 0,
        "category_stats": [],
        "all_errors": []
    }
    
    for idx, category in enumerate(all_categories, 1):
        logger.info("")
        logger.info("=" * 80)
        logger.info(f"Processing category {idx}/{len(all_categories)}: {category}")
        logger.info("=" * 80)
        
        try:
            category_stats = collect_category_places(
                category=category,
                max_places=max_places_per_category,
                area_code=area_code,
                delay_between_api_calls=delay_between_api_calls,
                create_embeddings=create_embeddings,
                lang_code_id=lang_code_id
            )
            
            overall_stats["categories_processed"] += 1
            if category_stats.get("places_saved", 0) > 0:
                overall_stats["categories_succeeded"] += 1
            else:
                overall_stats["categories_failed"] += 1
            
            overall_stats["total_visit_seoul_places_collected"] += category_stats.get("visit_seoul_places_collected", 0)
            overall_stats["total_places_saved"] += category_stats.get("places_saved", 0)
            overall_stats["total_quests_created"] += category_stats.get("quests_created", 0)
            overall_stats["total_embeddings_created"] += category_stats.get("embeddings_created", 0)
            overall_stats["all_errors"].extend(category_stats.get("errors", []))
            overall_stats["category_stats"].append(category_stats)
            
            logger.info(f"✓ Completed category {category}: {category_stats.get('places_saved', 0)} places saved")
            
        except Exception as e:
            error_msg = f"Fatal error processing category {category}: {e}"
            logger.error(error_msg, exc_info=True)
            overall_stats["categories_processed"] += 1
            overall_stats["categories_failed"] += 1
            overall_stats["all_errors"].append(error_msg)
        
        # 마지막 카테고리가 아니면 대기
        if idx < len(all_categories):
            logger.info(f"Waiting {delay_between_categories}s before next category...")
            time.sleep(delay_between_categories)
    
    return overall_stats


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Collect places from VISIT SEOUL API")
    parser.add_argument(
        "--category",
        type=str,
        default=None,
        choices=["Attractions", "History", "Culture", "Nature", "Food", "Drinks", "Shopping", "Activities", "Events"],
        help="Category to collect (if not specified, all categories will be collected automatically)"
    )
    parser.add_argument(
        "--all-categories",
        action="store_true",
        help="Collect all categories automatically (same as omitting --category)"
    )
    parser.add_argument(
        "--max-places",
        type=int,
        default=None,
        help="Maximum number of places to collect per category (default: category target, <=0 means ALL)"
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
        default=1.0,
        help="Delay between API calls in seconds (default: 1.0)"
    )
    parser.add_argument(
        "--lang-code",
        type=str,
        default="en",
        help="VISIT SEOUL language code (default: en)"
    )
    parser.add_argument(
        "--no-embeddings",
        action="store_true",
        help="Skip image embedding creation"
    )
    parser.add_argument(
        "--delay-between-categories",
        type=float,
        default=2.0,
        help="Delay between categories in seconds when collecting all categories (default: 2.0)"
    )
    
    args = parser.parse_args()
    
    # 카테고리 지정 여부 확인
    collect_all = args.all_categories or args.category is None
    
    logger.info("=" * 60)
    logger.info("Quest of Seoul - Place Collection Script")
    logger.info("=" * 60)
    if collect_all:
        logger.info("Mode: Collecting ALL categories automatically")
        logger.info(f"Categories to process: {', '.join(CATEGORY_DATASET_INFO.keys())}")
    else:
        logger.info(f"Mode: Single category collection")
        logger.info(f"Category: {args.category}")
    logger.info(f"Max places per category: {args.max_places if args.max_places else 'Category target'}")
    logger.info(f"Area code: {args.area_code}")
    logger.info(f"Language code: {args.lang_code}")
    logger.info(f"API call delay: {args.delay}s")
    if collect_all:
        logger.info(f"Delay between categories: {args.delay_between_categories}s")
    logger.info("=" * 60)
    
    if not os.getenv("VISIT_SEOUL_API_KEY"):
        logger.error("VISIT_SEOUL_API_KEY environment variable is required")
        sys.exit(1)
    
    if collect_all:
        # 모든 카테고리 자동 수집
        overall_stats = collect_all_categories(
            max_places_per_category=args.max_places,
            area_code=args.area_code,
            delay_between_api_calls=args.delay,
            create_embeddings=not args.no_embeddings,
            lang_code_id=args.lang_code,
            delay_between_categories=args.delay_between_categories
        )
        
        logger.info("")
        logger.info("=" * 80)
        logger.info("FINAL COLLECTION STATISTICS (ALL CATEGORIES)")
        logger.info("=" * 80)
        logger.info(f"  Total categories: {overall_stats['total_categories']}")
        logger.info(f"  Categories processed: {overall_stats['categories_processed']}")
        logger.info(f"  Categories succeeded: {overall_stats['categories_succeeded']}")
        logger.info(f"  Categories failed: {overall_stats['categories_failed']}")
        logger.info(f"  Total VISIT SEOUL places collected: {overall_stats['total_visit_seoul_places_collected']}")
        logger.info(f"  Total places saved: {overall_stats['total_places_saved']}")
        logger.info(f"  Total quests created: {overall_stats['total_quests_created']}")
        logger.info(f"  Total embeddings created: {overall_stats['total_embeddings_created']}")
        logger.info(f"  Total errors: {len(overall_stats['all_errors'])}")
        logger.info("")
        logger.info("Category-wise breakdown:")
        for cat_stat in overall_stats['category_stats']:
            logger.info(f"  - {cat_stat['category']}: {cat_stat.get('places_saved', 0)} places saved, "
                       f"{cat_stat.get('quests_created', 0)} quests, "
                       f"{cat_stat.get('embeddings_created', 0)} embeddings")
        
        if overall_stats['all_errors']:
            logger.warning("")
            logger.warning("Errors occurred during collection:")
            for error in overall_stats['all_errors'][:20]:
                logger.warning(f"  - {error}")
            if len(overall_stats['all_errors']) > 20:
                logger.warning(f"  ... and {len(overall_stats['all_errors']) - 20} more errors")
        
        logger.info("=" * 80)
    else:
        # 단일 카테고리 수집
        stats = collect_category_places(
            category=args.category,
            max_places=args.max_places,
            area_code=args.area_code,
            delay_between_api_calls=args.delay,
            create_embeddings=not args.no_embeddings,
            lang_code_id=args.lang_code
        )
        
        logger.info("=" * 60)
        logger.info("Collection Statistics:")
        logger.info(f"  Category: {stats['category']}")
        logger.info(f"  Lang code: {stats['lang_code_id']}")
        if stats.get("expected_total"):
            logger.info(f"  Target count: {stats['expected_total']}")
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
