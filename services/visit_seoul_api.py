"""VISIT SEOUL API Client"""

import os
import logging
import requests
import time
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

VISIT_SEOUL_BASE_URL = "https://api-call.visitseoul.net/api/v1"


def get_visit_seoul_api_key() -> str:
    api_key = os.getenv("VISIT_SEOUL_API_KEY")
    if not api_key:
        raise ValueError("VISIT_SEOUL_API_KEY environment variable is required")
    return api_key


def get_api_headers() -> Dict[str, str]:
    """API 요청 헤더 생성"""
    return {
        "Accept": "application/json;charset=UTF-8",
        "VISITSEOUL-API-KEY": get_visit_seoul_api_key()
    }


def get_category_list(retry_count: int = 3, retry_delay: float = 1.0) -> List[Dict]:
    """
    카테고리 목록 조회
    
    Args:
        retry_count: 재시도 횟수
        retry_delay: 재시도 간격 (초)
    
    Returns:
        카테고리 리스트
    """
    url = f"{VISIT_SEOUL_BASE_URL}/category/list"
    headers = get_api_headers()
    
    for attempt in range(retry_count):
        try:
            logger.info(f"Fetching category list (attempt: {attempt + 1})")
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("result_code") == 200 and "data" in data:
                categories = data["data"]
                logger.info(f"Found {len(categories)} categories")
                return categories
            else:
                logger.error(f"Unexpected response: {data}")
                return []
        
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request failed (attempt {attempt + 1}/{retry_count}): {e}")
            if attempt < retry_count - 1:
                time.sleep(retry_delay * (attempt + 1))
            else:
                logger.error(f"Failed to fetch categories after {retry_count} attempts")
                return []
        
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return []
    
    return []


def map_category_to_visit_seoul_sn(
    category: str,
    retry_count: int = 3,
    retry_delay: float = 1.0
) -> Optional[List[str]]:
    """
    카테고리를 VISIT SEOUL category_sn 리스트로 매핑 (카테고리 목록 API 사용)
    이미지 기준 테마 정의에 따라 여러 하위 카테고리를 포함할 수 있음
    
    Args:
        category: 카테고리 (Attractions, History, Culture, Nature, Food, Drinks, Shopping, Activities, Events)
        retry_count: 재시도 횟수
        retry_delay: 재시도 간격 (초)
    
    Returns:
        VISIT SEOUL category_sn (com_ctgry_sn) 리스트 또는 None
    """
    # 카테고리 목록 가져오기
    categories = get_category_list(retry_count, retry_delay)
    if not categories:
        logger.warning(f"Could not fetch VISIT SEOUL categories, returning None for {category}")
        return None
    
    # 카테고리별 매핑 키워드
    # ctgry_nm 또는 ctgry_path에서 매칭
    category_keywords = {
        "Attractions": [
            # 문화관광 > 랜드마크관광, 테마공원, 기타문화관광지
            "랜드마크관광", "랜드마크", "Landmark",
            "테마공원", "Theme Park",
            "기타문화관광지"
        ],
        "History": [
            # 역사관광
            "역사관광", "역사", "History", "Historic", "유적", "궁", "전통"
        ],
        "Culture": [
            # 문화관광 > 전시시설, 기타전시시설, 미술관/화랑, 박물관
            # 축제/공연/행사 > 전시회
            "전시시설", "전시", "Exhibition",
            "미술관", "화랑", "Museum", "Gallery",
            "박물관",
            "기타전시시설",
            "전시회"  # 축제/공연/행사 > 전시회
        ],
        "Nature": [
            # 자연관광
            # 문화관광 > 도시공원
            "자연관광", "자연", "Nature",
            "도시공원", "공원", "Park"
        ],
        "Food": [
            # 음식 > 카페/찻집, 주점 제외한 모든 중분류
            "음식", "식당", "맛집", "레스토랑", "Restaurant", "Food"
            # 주의: "카페", "찻집", "주점"은 제외해야 함 (아래 exclude_keywords에서 처리)
        ],
        "Drinks": [
            # 음식 > 카페/찻집, 주점
            "카페", "찻집", "Cafe", "Coffee", "티하우스",
            "주점", "Bar", "바"
        ],
        "Shopping": [
            # 쇼핑
            "쇼핑", "Shopping", "마켓", "시장", "상점", "Market"
        ],
        "Activities": [
            # 체험관광
            # 문화관광 > 레저스포츠시설
            "체험관광", "체험", "Experience",
            "레저스포츠시설", "레저", "스포츠", "Leisure", "Sports", "액티비티"
        ],
        "Events": [
            # 축제/공연/행사 > 축제, 공연, 행사, 기타행사, 박람회
            "축제", "Festival",
            "공연", "Performance",
            "행사", "Event",
            "기타행사",
            "박람회"
            # 주의: "전시회"는 Culture에 포함되므로 Events에서는 제외 (하지만 키워드 매칭 시 중복 가능성 있음)
        ]
    }
    
    keywords = category_keywords.get(category, [])
    if not keywords:
        logger.warning(f"Unknown category: {category}")
        return None
    
    matched_category_sns = []
    
    # 카테고리 목록에서 매칭되는 카테고리 찾기
    for cat in categories:
        ctgry_nm = cat.get("ctgry_nm", "").strip()
        ctgry_path = cat.get("ctgry_path", "").strip()
        category_sn = cat.get("com_ctgry_sn")
        
        if not category_sn:
            continue
        
        # Food 카테고리는 카페/찻집, 주점 제외
        if category == "Food":
            exclude_keywords = ["카페", "찻집", "주점", "Cafe", "Coffee", "Bar", "바", "티하우스"]
            if any(exclude in ctgry_nm or exclude in ctgry_path for exclude in exclude_keywords):
                continue
        
        # Events 카테고리는 전시회 제외 (전시회는 Culture에 포함)
        if category == "Events":
            if "전시회" in ctgry_nm or "전시회" in ctgry_path:
                continue
        
        # ctgry_nm 또는 ctgry_path에 키워드가 포함되어 있는지 확인
        for keyword in keywords:
            if keyword in ctgry_nm or keyword in ctgry_path:
                if category_sn not in matched_category_sns:
                    matched_category_sns.append(str(category_sn))
                    logger.debug(f"Matched category '{category}' with VISIT SEOUL category_sn '{category_sn}' (name: {ctgry_nm}, path: {ctgry_path})")
                break
    
    if matched_category_sns:
        logger.info(f"Mapped category '{category}' to {len(matched_category_sns)} VISIT SEOUL category_sn(s): {matched_category_sns}")
        return matched_category_sns
    else:
        logger.warning(f"Could not find matching VISIT SEOUL category for category: {category}")
        return None


def get_lang_code_list(retry_count: int = 3, retry_delay: float = 1.0) -> List[Dict]:
    """
    언어 코드 목록 조회
    
    Args:
        retry_count: 재시도 횟수
        retry_delay: 재시도 간격 (초)
    
    Returns:
        언어 코드 리스트
    """
    url = f"{VISIT_SEOUL_BASE_URL}/code/lang"
    headers = get_api_headers()
    
    for attempt in range(retry_count):
        try:
            logger.info(f"Fetching language code list (attempt: {attempt + 1})")
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("result_code") == 200 and "data" in data:
                lang_codes = data["data"]
                logger.info(f"Found {len(lang_codes)} language codes")
                return lang_codes
            else:
                logger.error(f"Unexpected response: {data}")
                return []
        
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request failed (attempt {attempt + 1}/{retry_count}): {e}")
            if attempt < retry_count - 1:
                time.sleep(retry_delay * (attempt + 1))
            else:
                logger.error(f"Failed to fetch language codes after {retry_count} attempts")
                return []
        
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return []
    
    return []


def search_places_by_category(
    category: Optional[str] = None,
    lang_code_id: str = "ko",
    keyword: Optional[str] = None,
    sort_type: str = "latest",
    page_no: int = 1,
    retry_count: int = 3,
    retry_delay: float = 1.0
) -> Dict:
    """
    카테고리별 장소 검색 (콘텐츠 목록 조회)
    
    Args:
        category: 카테고리 일련번호 (com_ctgry_sn, 선택사항)
        lang_code_id: 언어 코드 (ko, en, ja, zh)
        keyword: 검색 키워드 (선택)
        sort_type: 정렬 방식 ("latest": 최신순, "abc": 가나다순)
        page_no: 페이지 번호 (1부터 시작)
        retry_count: 재시도 횟수
        retry_delay: 재시도 간격 (초)
    
    Returns:
        응답 데이터 (data, paging 포함)
    """
    url = f"{VISIT_SEOUL_BASE_URL}/contents/list"
    headers = get_api_headers()
    headers["Content-Type"] = "application/json;charset=UTF-8"
    
    payload = {
        "lang_code_id": lang_code_id,
        "sort_type": sort_type,
        "page_no": page_no
    }
    
    # 카테고리가 제공된 경우에만 추가
    if category:
        payload["com_ctgry_sn"] = category
    
    if keyword:
        payload["keyword"] = keyword
    
    for attempt in range(retry_count):
        try:
            category_desc = category if category else "all categories"
            logger.info(f"Fetching VISIT SEOUL places (category: {category_desc}, page: {page_no}, attempt: {attempt + 1})")
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("result_code") == 200:
                places = data.get("data", [])
                paging = data.get("paging", {})
                logger.info(f"Found {len(places)} places (page {page_no}, total: {paging.get('total_count', 0)})")
                return data
            else:
                logger.error(f"API error: {data.get('result_message', 'Unknown error')}")
                return {
                    "data": [],
                    "paging": {"page_no": page_no, "page_size": 50, "total_count": 0},
                    "result_code": data.get("result_code", -1),
                    "result_message": data.get("result_message", "Unknown error")
                }
        
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request failed (attempt {attempt + 1}/{retry_count}): {e}")
            if attempt < retry_count - 1:
                time.sleep(retry_delay * (attempt + 1))
            else:
                logger.error(f"Failed to fetch places after {retry_count} attempts")
                return {
                    "data": [],
                    "paging": {"page_no": page_no, "page_size": 50, "total_count": 0},
                    "result_code": -1,
                    "result_message": str(e)
                }
        
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return {
                "data": [],
                "paging": {"page_no": page_no, "page_size": 50, "total_count": 0},
                "result_code": -1,
                "result_message": str(e)
            }
    
    return {
        "data": [],
        "paging": {"page_no": page_no, "page_size": 50, "total_count": 0},
        "result_code": -1,
        "result_message": "Failed after retries"
    }


def get_place_detail(
    cid: str,
    retry_count: int = 3,
    retry_delay: float = 1.0
) -> Optional[Dict]:
    """
    장소 상세 정보 조회
    
    Args:
        cid: 콘텐츠 고유 ID
        retry_count: 재시도 횟수
        retry_delay: 재시도 간격 (초)
    
    Returns:
        장소 상세 정보
    """
    url = f"{VISIT_SEOUL_BASE_URL}/contents/info"
    headers = get_api_headers()
    headers["Content-Type"] = "application/json;charset=UTF-8"
    
    payload = {
        "cid": cid
    }
    
    for attempt in range(retry_count):
        try:
            logger.info(f"Fetching VISIT SEOUL place detail (cid: {cid}, attempt: {attempt + 1})")
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("result_code") == 200 and "data" in data:
                detail = data["data"]
                logger.info(f"Found detail for cid: {cid}")
                return detail
            else:
                logger.warning(f"No detail found for cid: {cid}, result_code: {data.get('result_code')}")
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
        item: contents/list 응답 아이템
        detail: contents/info 응답 (선택)
    
    Returns:
        표준화된 장소 데이터
    """
    # detail이 있으면 detail 사용, 없으면 item 사용
    data = detail if detail else item
    
    # 디버깅: 원본 데이터 로깅
    cid = data.get("cid") or item.get("cid")
    logger.debug(f"Parsing VISIT SEOUL place - CID: {cid}")
    logger.debug(f"Item keys: {list(item.keys()) if item else 'None'}")
    logger.debug(f"Detail keys: {list(detail.keys()) if detail else 'None'}")
    
    # 좌표 추출 (traffic.map_position_x/y 사용)
    latitude = None
    longitude = None
    
    if detail and "traffic" in detail:
        traffic = detail["traffic"]
        if traffic.get("map_position_y"):
            try:
                latitude = float(traffic["map_position_y"])
            except (ValueError, TypeError):
                pass
        if traffic.get("map_position_x"):
            try:
                longitude = float(traffic["map_position_x"])
            except (ValueError, TypeError):
                pass
    
    # 주소 추출 (traffic.new_adres 우선, 없으면 adres)
    address = None
    if detail and "traffic" in detail:
        traffic = detail["traffic"]
        address = traffic.get("new_adres") or traffic.get("adres")
    
    # 이미지 URL
    image_url = None
    images = []
    
    if detail:
        if detail.get("main_img"):
            image_url = detail["main_img"]
            images.append(detail["main_img"])
        
        if detail.get("relate_img"):
            relate_imgs = detail["relate_img"]
            if isinstance(relate_imgs, list):
                for img in relate_imgs:
                    if img and img not in images:
                        images.append(img)
    
    if not image_url and item.get("main_img"):
        image_url = item["main_img"]
        images.append(item["main_img"])
    
    # 상세 정보 추출
    overview = None
    content = None
    homepage = None
    tel = None
    usage_info = None
    tip = None
    detail_info = {}
    
    if detail:
        # overview와 content는 post_desc 또는 sumry에서 가져옴 (그대로 사용)
        overview = detail.get("post_desc") or detail.get("sumry")
        content = overview  # content는 overview와 동일하게 사용
        
        if "extra" in detail:
            extra = detail["extra"]
            homepage = extra.get("cmmn_hmpg_url")
            tel = extra.get("cmmn_telno")
            tip = extra.get("cmmn_tip") or extra.get("tip")
            
            logger.debug(f"Extra keys: {list(extra.keys()) if extra else 'None'}")
            logger.debug(f"Homepage: {homepage}, Tel: {tel}, Tip: {tip}")
            
            # detail_info 구성 (API 응답 구조에 맞게)
            detail_info = {
                "opening_hours": extra.get("cmmn_use_time") or "",
                "closed_days": extra.get("closed_days") or "",
                "business_days": extra.get("business_days") or extra.get("cmmn_business_days") or "",
                "tel": tel or "",
                "traffic_info": detail.get("traffic", {}).get("subway_info") or "" if detail and "traffic" in detail else "",
                "homepage": homepage or "",
                "important": extra.get("cmmn_important") or "",
                "admission_fee": extra.get("trrsrt_use_chrge") or "",  # F: 무료, C: 유료
                "admission_fee_guidance": extra.get("trrsrt_use_chrge_guidance") or "",
                "disabled_facility": extra.get("disabled_facility") or []
            }
            
            # 이용안내 조합
            usage_info_parts = []
            if extra.get("cmmn_use_time"):
                usage_info_parts.append(f"이용시간: {extra['cmmn_use_time']}")
            if extra.get("closed_days"):
                usage_info_parts.append(f"휴무일: {extra['closed_days']}")
            if extra.get("trrsrt_use_chrge_guidance"):
                usage_info_parts.append(f"이용요금: {extra['trrsrt_use_chrge_guidance']}")
            if extra.get("cmmn_important"):
                usage_info_parts.append(f"이것만은 꼭!: {extra['cmmn_important']}")
            
            usage_info = "\n".join(usage_info_parts) if usage_info_parts else None
        else:
            logger.debug("No 'extra' field in detail")
    else:
        # detail이 없으면 item에서 가져오기 시도
        overview = item.get("sumry")
        content = overview
        logger.debug(f"Using item data - overview: {overview[:100] if overview else 'None'}...")
    
    # 카테고리 정보 추출
    category_sn = data.get("com_ctgry_sn") or item.get("com_ctgry_sn")
    
    # 최종 파싱 결과 로깅
    parsed_data = {
        "content_id": data.get("cid") or item.get("cid"),
        "content_type_id": None,  # VISIT SEOUL은 content_type_id를 사용하지 않음
        "name": data.get("post_sj") or item.get("post_sj"),
        "category": category_sn,  # com_ctgry_sn
        "address": address,
        "latitude": latitude,
        "longitude": longitude,
        "image_url": image_url,
        "images": images,
        "overview": overview or item.get("sumry"),
        "content": content,  # content 필드 추가
        "homepage": homepage,
        "tel": tel,
        "usage_info": usage_info,
        "tip": tip,  # tip 필드 추가
        "detail_info": detail_info,  # detail_info 필드 추가
        "raw_data": {
            "item": item,
            "detail": detail
        }
    }
    
    logger.info(f"Parsed place - Name: {parsed_data['name']}, Content: {bool(content)}, Detail_info keys: {list(detail_info.keys())}, category_sn: {category_sn}")
    
    return parsed_data


def collect_all_places_by_category(
    category_sn: Optional[str] = None,
    lang_code_id: str = "ko",
    max_places: int = 50,
    delay_between_pages: float = 0.5
) -> List[Dict]:
    """
    카테고리별 모든 장소 수집 (여러 페이지)
    
    Args:
        category_sn: 카테고리 일련번호 (com_ctgry_sn, 선택사항)
        lang_code_id: 언어 코드 (ko, en, ja, zh)
        max_places: 최대 수집 장소 수
        delay_between_pages: 페이지 간 지연 시간 (초)
    
    Returns:
        수집된 장소 리스트
    """
    all_places = []
    page_no = 1
    
    category_desc = category_sn if category_sn else "all categories"
    logger.info(f"Starting VISIT SEOUL collection for category: {category_desc}, max_places: {max_places}")
    
    while len(all_places) < max_places:
        result = search_places_by_category(
            category=category_sn,
            lang_code_id=lang_code_id,
            page_no=page_no
        )
        
        places = result.get("data", [])
        paging = result.get("paging", {})
        
        if not places:
            logger.info(f"No more places found at page {page_no}")
            break
        
        all_places.extend(places)
        logger.info(f"Collected {len(all_places)} places so far (page {page_no}, total: {paging.get('total_count', 0)})")
        
        # 페이지 크기 확인
        page_size = paging.get("page_size", 50)
        total_count = paging.get("total_count", 0)
        
        if len(places) < page_size or len(all_places) >= total_count:
            # 마지막 페이지
            break
        
        if len(all_places) >= max_places:
            all_places = all_places[:max_places]
            break
        
        page_no += 1
        time.sleep(delay_between_pages)
    
    category_desc = category_sn if category_sn else "all categories"
    logger.info(f"Total collected: {len(all_places)} places for category {category_desc}")
    return all_places