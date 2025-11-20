"""TourAPI Client"""

import os
import logging
import requests
import time
from typing import List, Dict, Optional
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

TOUR_API_BASE_URL = "http://apis.data.go.kr/B551011/KorService2"

CONTENT_TYPE_MAP = {
    "Attraction": "12",  # 관광지
    "Culture": "14",     # 문화시설
    "Events": "15",      # 축제/공연/행사
    "Leisure": "28",     # 레포츠
    "Sleep": "32",       # 숙박
    "Shopping": "38",    # 쇼핑
    "Cuisine": "39",     # 음식점
    "Transportation": "25"  # 교통
}


def get_tour_api_key() -> str:
    api_key = os.getenv("TOUR_API_KEY")
    if not api_key:
        raise ValueError("TOUR_API_KEY environment variable is required")
    return api_key


def get_content_type_id(category: str) -> Optional[str]:
    """카테고리를 Content Type ID로 변환"""
    return CONTENT_TYPE_MAP.get(category)


def search_places_by_category(
    category: str,
    area_code: str = "1",  # 서울: 1
    num_of_rows: int = 100,
    page_no: int = 1,
    retry_count: int = 3,
    retry_delay: float = 1.0
) -> List[Dict]:
    """
    카테고리별 장소 검색
    
    Args:
        category: Quest of Seoul 테마 (Attraction, Culture 등)
        area_code: 지역코드 (서울: 1)
        num_of_rows: 한 페이지 결과 수
        page_no: 페이지 번호
        retry_count: 재시도 횟수
        retry_delay: 재시도 간격 (초)
    
    Returns:
        장소 리스트
    """
    content_type_id = get_content_type_id(category)
    if not content_type_id:
        logger.error(f"Unknown category: {category}")
        return []
    
    api_key = get_tour_api_key()
    
    params = {
        "serviceKey": api_key,
        "numOfRows": num_of_rows,
        "pageNo": page_no,
        "MobileOS": "ETC",
        "MobileApp": "QuestOfSeoul",
        "_type": "json",
        #"listYN": "Y",
        "arrange": "A",  # 제목순 정렬
        "contentTypeId": content_type_id,
        "areaCode": area_code
    }
    
    url = f"{TOUR_API_BASE_URL}/areaBasedList2"
    
    for attempt in range(retry_count):
        try:
            logger.info(f"Fetching places (category: {category}, page: {page_no}, attempt: {attempt + 1})")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if "response" in data and "body" in data["response"]:
                body = data["response"]["body"]
                
                if "items" in body and "item" in body["items"]:
                    items = body["items"]["item"]
                    if isinstance(items, dict):
                        items = [items]
                    
                    logger.info(f"Found {len(items)} places for category {category}")
                    return items
                else:
                    logger.warning(f"No items found in response for category {category}")
                    return []
            else:
                logger.error(f"Unexpected response structure: {data}")
                return []
        
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request failed (attempt {attempt + 1}/{retry_count}): {e}")
            if attempt < retry_count - 1:
                time.sleep(retry_delay * (attempt + 1))
            else:
                logger.error(f"Failed to fetch places after {retry_count} attempts")
                return []
        
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return []
    
    return []


def get_place_detail(
    content_id: str,
    content_type_id: str,
    retry_count: int = 3,
    retry_delay: float = 1.0
) -> Optional[Dict]:
    """
    장소 상세 정보 조회
    
    Args:
        content_id: TourAPI contentId
        content_type_id: TourAPI contentTypeId
        retry_count: 재시도 횟수
        retry_delay: 재시도 간격 (초)
    
    Returns:
        장소 상세 정보
    """
    api_key = get_tour_api_key()
    
    params = {
        "serviceKey": api_key,
        "MobileOS": "ETC",
        "MobileApp": "QuestOfSeoul",
        "_type": "json",
        "contentId": content_id,
        #"contentTypeId": content_type_id
    }
    
    url = f"{TOUR_API_BASE_URL}/detailCommon2"
    
    for attempt in range(retry_count):
        try:
            logger.info(f"Fetching place detail (contentId: {content_id}, attempt: {attempt + 1})")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if "response" in data and "body" in data["response"]:
                body = data["response"]["body"]
                
                if "items" in body and "item" in body["items"]:
                    items = body["items"]["item"]
                    # 단일 아이템인 경우 첫 번째 아이템 반환
                    if isinstance(items, list) and len(items) > 0:
                        return items[0]
                    elif isinstance(items, dict):
                        return items
                    else:
                        logger.warning(f"No detail found for contentId: {content_id}")
                        return None
                else:
                    logger.warning(f"No items in detail response for contentId: {content_id}")
                    return None
            else:
                logger.error(f"Unexpected detail response structure: {data}")
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


def get_place_intro(
    content_id: str,
    content_type_id: str,
    retry_count: int = 3,
    retry_delay: float = 1.0
) -> Optional[Dict]:
    """
    장소 소개 정보 조회 (이용안내, 상세정보 등)
    
    Args:
        content_id: TourAPI contentId
        content_type_id: TourAPI contentTypeId
        retry_count: 재시도 횟수
        retry_delay: 재시도 간격 (초)
    
    Returns:
        장소 소개 정보
    """
    api_key = get_tour_api_key()
    
    params = {
        "serviceKey": api_key,
        "MobileOS": "ETC",
        "MobileApp": "QuestOfSeoul",
        "_type": "json",
        "contentId": content_id,
        "contentTypeId": content_type_id
    }
    
    url = f"{TOUR_API_BASE_URL}/detailIntro2"
    
    for attempt in range(retry_count):
        try:
            logger.info(f"Fetching place intro (contentId: {content_id}, attempt: {attempt + 1})")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if "response" in data and "body" in data["response"]:
                body = data["response"]["body"]
                
                if "items" in body and "item" in body["items"]:
                    items = body["items"]["item"]
                    if isinstance(items, list) and len(items) > 0:
                        return items[0]
                    elif isinstance(items, dict):
                        return items
                    else:
                        return None
                else:
                    return None
            else:
                return None
        
        except requests.exceptions.RequestException as e:
            logger.warning(f"Intro request failed (attempt {attempt + 1}/{retry_count}): {e}")
            if attempt < retry_count - 1:
                time.sleep(retry_delay * (attempt + 1))
            else:
                return None
        
        except Exception as e:
            logger.error(f"Unexpected error in get_place_intro: {e}", exc_info=True)
            return None
    
    return None


def parse_tour_api_place(item: Dict, detail: Optional[Dict] = None, intro: Optional[Dict] = None) -> Dict:
    """
    TourAPI 응답을 표준화된 장소 데이터로 변환
    
    Args:
        item: areaBasedList 응답 아이템
        detail: detailCommon 응답 (선택)
        intro: detailIntro 응답 (선택)
    
    Returns:
        표준화된 장소 데이터
    """
    # 좌표 변환 (TourAPI는 mapx, mapy를 사용 - WGS84 좌표계)
    # mapx, mapy는 KATEC 좌표계이므로 변환이 필요할 수 있음
    # 일단 그대로 사용 (실제 테스트 필요)
    latitude = None
    longitude = None
    
    if "mapy" in item:
        try:
            latitude = float(item["mapy"])
        except (ValueError, TypeError):
            pass
    
    if "mapx" in item:
        try:
            longitude = float(item["mapx"])
        except (ValueError, TypeError):
            pass
    
    # 주소 통합
    address_parts = []
    if item.get("addr1"):
        address_parts.append(item["addr1"])
    if item.get("addr2"):
        address_parts.append(item["addr2"])
    address = " ".join(address_parts) if address_parts else None
    
    # 이미지 URL
    image_url = item.get("firstimage") or item.get("firstimage2")
    images = []
    if item.get("firstimage"):
        images.append(item["firstimage"])
    if item.get("firstimage2") and item["firstimage2"] != item.get("firstimage"):
        images.append(item["firstimage2"])
    
    # 상세 정보 추출
    overview = None
    homepage = None
    tel = None
    
    if detail:
        overview = detail.get("overview")
        homepage = detail.get("homepage")
        tel = detail.get("tel")
    
    # 이용안내 추출
    usage_info = None
    if intro:
        # contentTypeId에 따라 다른 필드 사용
        usage_info_parts = []
        if intro.get("usetime"):
            usage_info_parts.append(f"이용시간: {intro['usetime']}")
        if intro.get("restdate"):
            usage_info_parts.append(f"휴무일: {intro['restdate']}")
        if intro.get("usefee"):
            usage_info_parts.append(f"이용요금: {intro['usefee']}")
        usage_info = "\n".join(usage_info_parts) if usage_info_parts else None
    
    return {
        "content_id": item.get("contentid"),
        "content_type_id": item.get("contenttypeid"),
        "name": item.get("title"),
        "name_en": None,  # TourAPI 기본 응답에는 없음, detail에서 가져올 수 있음
        "category": None,  # 나중에 매핑
        "address": address,
        "latitude": latitude,
        "longitude": longitude,
        "image_url": image_url,
        "images": images,
        "overview": overview,
        "homepage": homepage,
        "tel": tel,
        "usage_info": usage_info,
        "raw_data": {
            "item": item,
            "detail": detail,
            "intro": intro
        }
    }


def collect_all_places_by_category(
    category: str,
    area_code: str = "1",
    max_places: int = 50,
    delay_between_pages: float = 0.5
) -> List[Dict]:
    """
    카테고리별 모든 장소 수집 (여러 페이지)
    
    Args:
        category: Quest of Seoul 테마
        area_code: 지역코드 (서울: 1)
        max_places: 최대 수집 장소 수
        delay_between_pages: 페이지 간 지연 시간 (초)
    
    Returns:
        수집된 장소 리스트
    """
    all_places = []
    page_no = 1
    num_of_rows = 100
    
    logger.info(f"Starting collection for category: {category}, max_places: {max_places}")
    
    while len(all_places) < max_places:
        places = search_places_by_category(
            category=category,
            area_code=area_code,
            num_of_rows=num_of_rows,
            page_no=page_no
        )
        
        if not places:
            logger.info(f"No more places found at page {page_no}")
            break
        
        all_places.extend(places)
        logger.info(f"Collected {len(all_places)} places so far (page {page_no})")
        
        if len(places) < num_of_rows:
            # 마지막 페이지
            break
        
        if len(all_places) >= max_places:
            all_places = all_places[:max_places]
            break
        
        page_no += 1
        time.sleep(delay_between_pages)
    
    logger.info(f"Total collected: {len(all_places)} places for category {category}")
    return all_places
