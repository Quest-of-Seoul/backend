"""VISIT SEOUL API Client"""

import os
import logging
import requests
import time
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

VISIT_SEOUL_BASE_URL = "https://api.visitseoul.net"

CATEGORY_MAP = {
    "Attraction": ["역사관광", "자연관광"],  # TourAPI Attraction에 매핑
    "Culture": ["문화관광"],  # TourAPI Culture에 매핑
    "Events": ["축제/공연/행사"],
    "Shopping": ["쇼핑"],
    "Food": ["음식"],
    "Extreme": ["체험관광"],
    "Sleep": ["숙박"]
}


def get_visit_seoul_api_key() -> str:
    api_key = os.getenv("VISIT_SEOUL_API_KEY")
    if not api_key:
        raise ValueError("VISIT_SEOUL_API_KEY environment variable is required")
    return api_key


def search_places_by_category(
    category: str,
    lang: str = "ko",
    page_no: int = 1,
    page_size: int = 100,
    retry_count: int = 3,
    retry_delay: float = 1.0
) -> List[Dict]:
    """
    카테고리별 장소 검색
    
    Args:
        category: Quest of Seoul 테마 (Attraction, Culture 등)
        lang: 언어 (ko, en)
        page_no: 페이지 번호
        page_size: 페이지 크기
        retry_count: 재시도 횟수
        retry_delay: 재시도 간격 (초)
    
    Returns:
        장소 리스트
    """
    api_key = get_visit_seoul_api_key()
    
    # VISIT SEOUL API 카테고리 매핑
    visit_seoul_categories = CATEGORY_MAP.get(category, [])
    if not visit_seoul_categories:
        logger.warning(f"No VISIT SEOUL category mapping for: {category}")
        return []
    
    all_places = []
    
    # 여러 카테고리에 대해 검색 (예: Attraction은 역사관광 + 자연관광)
    for vs_category in visit_seoul_categories:
        params = {
            "key": api_key,
            "lang": lang,
            "pageNo": page_no,
            "pageSize": page_size,
            "category": vs_category
        }
        
        url = f"{VISIT_SEOUL_BASE_URL}/contents/search"
        
        for attempt in range(retry_count):
            try:
                logger.info(f"Fetching VISIT SEOUL places (category: {vs_category}, page: {page_no}, attempt: {attempt + 1})")
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                
                if "contents" in data:
                    places = data["contents"]
                    if isinstance(places, list):
                        all_places.extend(places)
                        logger.info(f"Found {len(places)} places for category {vs_category}")
                    elif isinstance(places, dict):
                        all_places.append(places)
                        logger.info(f"Found 1 place for category {vs_category}")
                    break
                else:
                    logger.warning(f"No contents in response for category {vs_category}")
                    break
            
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}/{retry_count}): {e}")
                if attempt < retry_count - 1:
                    time.sleep(retry_delay * (attempt + 1))
                else:
                    logger.error(f"Failed to fetch places after {retry_count} attempts")
            
            except Exception as e:
                logger.error(f"Unexpected error: {e}", exc_info=True)
        
        # API 호출 간 지연
        if vs_category != visit_seoul_categories[-1]:
            time.sleep(0.3)
    
    return all_places


def get_place_detail(
    content_id: str,
    lang: str = "ko",
    retry_count: int = 3,
    retry_delay: float = 1.0
) -> Optional[Dict]:
    """
    장소 상세 정보 조회
    
    Args:
        content_id: VISIT SEOUL contentId
        lang: 언어 (ko, en)
        retry_count: 재시도 횟수
        retry_delay: 재시도 간격 (초)
    
    Returns:
        장소 상세 정보
    """
    api_key = get_visit_seoul_api_key()
    
    params = {
        "key": api_key,
        "lang": lang
    }
    
    url = f"{VISIT_SEOUL_BASE_URL}/contents/standard/view/{content_id}"
    
    for attempt in range(retry_count):
        try:
            logger.info(f"Fetching VISIT SEOUL place detail (contentId: {content_id}, attempt: {attempt + 1})")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if "contents" in data:
                contents = data["contents"]
                if isinstance(contents, list) and len(contents) > 0:
                    return contents[0]
                elif isinstance(contents, dict):
                    return contents
                else:
                    logger.warning(f"No detail found for contentId: {content_id}")
                    return None
            else:
                logger.warning(f"No contents in detail response for contentId: {content_id}")
                return None
        
        except requests.exceptions.RequestException as e:
            logger.warning(f"Detail request failed (attempt {attempt + 1}/{retry_count}): {e}")
            if attempt < retry_count - 1:
                time.sleep(retry_delay * (attempt + 1))
            else:
                logger.error(f"Failed to fetch place detail after {retry_count} attempts")
                return None
        
        except Exception as e:
            logger.error(f"Unexpected error in get_place_detail: {e}", exc_info=True)
            return None
    
    return None


def parse_visit_seoul_place(item: Dict, detail: Optional[Dict] = None) -> Dict:
    """
    VISIT SEOUL API 응답을 표준화된 장소 데이터로 변환
    
    Args:
        item: search 응답 아이템
        detail: detail 응답 (선택)
    
    Returns:
        표준화된 장소 데이터
    """
    # detail이 있으면 detail 사용, 없으면 item 사용
    data = detail if detail else item
    
    # 좌표 추출
    latitude = None
    longitude = None
    
    if "latitude" in data:
        try:
            latitude = float(data["latitude"])
        except (ValueError, TypeError):
            pass
    
    if "longitude" in data:
        try:
            longitude = float(data["longitude"])
        except (ValueError, TypeError):
            pass
    
    # 주소
    address = data.get("address") or data.get("addr")
    
    # 이미지 URL
    image_url = data.get("image") or data.get("thumbnail") or data.get("mainImage")
    images = []
    if data.get("image"):
        images.append(data["image"])
    if data.get("thumbnail") and data["thumbnail"] != data.get("image"):
        images.append(data["thumbnail"])
    if data.get("mainImage") and data["mainImage"] not in images:
        images.append(data["mainImage"])
    
    # 상세 정보 추출
    content = data.get("content") or data.get("description")
    
    # detailInfo 추출
    detail_info = {}
    if data.get("tel"):
        detail_info["tel"] = data["tel"]
    if data.get("address") or data.get("addr"):
        detail_info["address"] = address
    if data.get("trafficInfo"):
        detail_info["traffic_info"] = data["trafficInfo"]
    if data.get("openingHours") or data.get("opening_hours"):
        detail_info["opening_hours"] = data.get("openingHours") or data.get("opening_hours")
    if data.get("businessDays") or data.get("business_days"):
        detail_info["business_days"] = data.get("businessDays") or data.get("business_days")
    if data.get("closedDays") or data.get("closed_days"):
        detail_info["closed_days"] = data.get("closedDays") or data.get("closed_days")
    
    # 팁
    tip = data.get("tip") or data.get("recommendation")
    
    return {
        "content_id": data.get("contentId") or data.get("content_id") or data.get("id"),
        "name": data.get("title") or data.get("name"),
        "name_en": data.get("titleEn") or data.get("title_en"),
        "category": data.get("category"),
        "address": address,
        "latitude": latitude,
        "longitude": longitude,
        "image_url": image_url,
        "images": images,
        "content": content,
        "detail_info": detail_info if detail_info else None,
        "tip": tip,
        "raw_data": {
            "item": item,
            "detail": detail
        }
    }


def collect_all_places_by_category(
    category: str,
    lang: str = "ko",
    max_places: int = 50,
    delay_between_pages: float = 0.5
) -> List[Dict]:
    """
    카테고리별 모든 장소 수집 (여러 페이지)
    
    Args:
        category: Quest of Seoul 테마
        lang: 언어 (ko, en)
        max_places: 최대 수집 장소 수
        delay_between_pages: 페이지 간 지연 시간 (초)
    
    Returns:
        수집된 장소 리스트
    """
    all_places = []
    page_no = 1
    page_size = 100
    
    logger.info(f"Starting VISIT SEOUL collection for category: {category}, max_places: {max_places}")
    
    while len(all_places) < max_places:
        places = search_places_by_category(
            category=category,
            lang=lang,
            page_no=page_no,
            page_size=page_size
        )
        
        if not places:
            logger.info(f"No more places found at page {page_no}")
            break
        
        all_places.extend(places)
        logger.info(f"Collected {len(all_places)} places so far (page {page_no})")
        
        if len(places) < page_size:
            # 마지막 페이지
            break
        
        if len(all_places) >= max_places:
            all_places = all_places[:max_places]
            break
        
        page_no += 1
        time.sleep(delay_between_pages)
    
    logger.info(f"Total collected: {len(all_places)} places for category {category}")
    return all_places
