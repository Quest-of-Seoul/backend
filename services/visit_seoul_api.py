import os
import logging
import requests
import time
from typing import List, Dict, Optional, Set

logger = logging.getLogger(__name__)

VISIT_SEOUL_BASE_URL = "https://api-call.visitseoul.net/api/v1"


def normalize_category_path(path: Optional[str]) -> str:
    if not path:
        return ""
    parts = [segment.strip() for segment in path.split(">") if segment.strip()]
    return " > ".join(parts)


CATEGORY_DATASET_INFO: Dict[str, Dict] = {
    "Attractions": {
        "include_paths": [
            "문화관광 > 랜드마크관광",
            "문화관광 > 테마공원",
            "문화관광 > 기타문화관광지"
        ],
        "include_paths_en": [
            "Culture > Landmarks",
            "Culture > Theme Parks",
            "Culture > Cultural Facilities > Others Cultural Facilities"
        ],
        "include_keywords": ["랜드마크", "테마공원"],
        "include_keywords_en": ["Landmark", "Theme Park", "Attraction", "Hot Spot"]
    },
    "History": {
        "include_paths": [
            "역사관광"
        ],
        "include_paths_en": [
            "History",
            "History > Historical Sites",
            "History > Religious Sites"
        ],
        "include_keywords": ["역사관광", "역사", "유적", "궁", "전통"],
        "include_keywords_en": ["History", "Historic", "Heritage", "Palace", "Traditional", "Historical Sites", "Religious Sites"]
    },
    "Culture": {
        "include_paths": [
            "문화관광 > 전시시설",
            "문화관광 > 기타전시시설",
            "문화관광 > 미술관/화랑",
            "문화관광 > 박물관",
            "축제/공연/행사 > 전시회"
        ],
        "include_paths_en": [
            "Culture > Convention Centers",
            "Culture > Cultural Facilities",
            "Culture > Cultural Facilities > Art Museums/Galleries",
            "Culture > Cultural Facilities > Museums",
            "Festivals/Events/Performances > Events > Exhibitions"
        ],
        "include_keywords": ["전시", "미술관", "박물관"],
        "include_keywords_en": ["Museum", "Gallery", "Exhibition", "Art Gallery", "Art Museum"]
    },
    "Nature": {
        "include_paths": [
            "자연관광",
            "문화관광 > 도시공원"
        ],
        "include_paths_en": [
            "Nature",
            "Nature > Natural Sites(Mountains)",
            "Nature > Natural Sites(Parks)",
            "Nature > Natural Sites(Rivers)",
            "Culture > Parks"
        ],
        "include_keywords": ["자연", "공원"],
        "include_keywords_en": ["Nature", "Park", "Urban Park", "Natural", "Mountain", "River"]
    },
    "Food": {
        "include_prefixes": ["음식"],
        "include_prefixes_en": ["Cuisine"],
        "include_keywords": ["음식", "맛집"],
        "include_keywords_en": ["Food", "Restaurant", "Dining"],
        "exclude_keywords": ["카페", "찻집", "주점", "티하우스"],
        "exclude_keywords_en": ["Cafe", "Coffee", "Bar", "Tea House", "Cafes & Tea Shops", "Bars & Clubs"]
    },
    "Drinks": {
        "include_paths": [
            "음식 > 카페/찻집",
            "음식 > 주점"
        ],
        "include_paths_en": [
            "Cuisine > Cafes & Tea Shops",
            "Cuisine > Bars & Clubs"
        ],
        "include_keywords": ["카페", "찻집", "주점", "티하우스"],
        "include_keywords_en": ["Cafe", "Coffee", "Bar", "Tea House", "Beverage"]
    },
    "Shopping": {
        "include_paths": [
            "쇼핑"
        ],
        "include_paths_en": [
            "Shopping",
            "Shopping > Department Stores",
            "Shopping > Duty Free Shops",
            "Shopping > Shopping Malls & Outlets",
            "Shopping > Specialty Shops & Stores",
            "Shopping > Supermarkets & Warehouses",
            "Shopping > Traditional Markets"
        ],
        "include_keywords": ["쇼핑", "시장", "마켓"],
        "include_keywords_en": ["Shopping", "Market", "Store", "Shopping Mall", "Department Store", "Duty Free", "Traditional Market"]
    },
    "Activities": {
        "include_paths": [
            "체험관광",
            "문화관광 > 레저스포츠시설"
        ],
        "include_paths_en": [
            "Experience Programs",
            "Experience Programs > Craft Workshops",
            "Experience Programs > Industrial Sites",
            "Experience Programs > Other Experiences",
            "Experience Programs > Temple Stays",
            "Experience Programs > Traditional Experience",
            "Experience Programs > Wellness",
            "Culture > Leisure/Sports Centers"
        ],
        "include_keywords": ["체험", "레저", "스포츠"],
        "include_keywords_en": ["Experience", "Leisure", "Sports", "Activity", "Adventure", "Workshop", "Temple Stay", "Wellness"]
    },
    "Events": {
        "include_paths": [
            "축제/공연/행사 > 축제",
            "축제/공연/행사 > 공연",
            "축제/공연/행사 > 행사",
            "축제/공연/행사 > 기타행사",
            "축제/공연/행사 > 박람회"
        ],
        "include_paths_en": [
            "Festivals/Events/Performances > Festivals",
            "Festivals/Events/Performances > Performances",
            "Festivals/Events/Performances > Events",
            "Festivals/Events/Performances > Events > Other Events",
            "Festivals/Events/Performances > Events > Expos"
        ],
        "include_keywords": ["축제", "공연", "행사", "박람회"],
        "include_keywords_en": ["Festival", "Performance", "Event", "Show", "Fair"],
        "exclude_keywords": ["전시회"],
        "exclude_keywords_en": ["Exhibition"]
    }
}


def get_visit_seoul_api_key() -> str:
    api_key = os.getenv("VISIT_SEOUL_API_KEY")
    if not api_key:
        raise ValueError("VISIT_SEOUL_API_KEY environment variable is required")
    return api_key


def get_api_headers() -> Dict[str, str]:
    return {
        "Accept": "application/json;charset=UTF-8",
        "VISITSEOUL-API-KEY": get_visit_seoul_api_key()
    }


def get_category_list(lang_code_id: str = "en", retry_count: int = 5, retry_delay: float = 1.0) -> List[Dict]:
    url = f"{VISIT_SEOUL_BASE_URL}/category/list"
    headers = get_api_headers()
    
    for attempt in range(retry_count):
        try:
            logger.info(f"Fetching category list (lang: {lang_code_id}, attempt: {attempt + 1})")
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
    lang_code_id: str = "en",
    retry_count: int = 5,
    retry_delay: float = 1.0
) -> Optional[List[str]]:
    categories = get_category_list(lang_code_id, retry_count, retry_delay)
    if not categories:
        logger.warning(f"Could not fetch VISIT SEOUL categories, returning None for {category}")
        return None
    
    category_info = CATEGORY_DATASET_INFO.get(category, {})
    
    is_english = lang_code_id == "en"
    if is_english:
        include_paths = [normalize_category_path(p) for p in category_info.get("include_paths_en", [])]
        include_prefixes = [normalize_category_path(p) for p in category_info.get("include_prefixes_en", [])]
        include_keywords = category_info.get("include_keywords_en", [])
        exclude_keywords = category_info.get("exclude_keywords_en", [])
    else:
        include_paths = [normalize_category_path(p) for p in category_info.get("include_paths", [])]
        include_prefixes = [normalize_category_path(p) for p in category_info.get("include_prefixes", [])]
        include_keywords = category_info.get("include_keywords") or []
        exclude_keywords = category_info.get("exclude_keywords", [])
    
    if not include_paths and not include_keywords and not include_prefixes:
        logger.warning(f"Unknown category: {category}")
        return None
    
    matched_category_sns: List[str] = []
    matched_paths: Set[str] = set()
    
    normalized_include_paths = [normalize_category_path(p) for p in include_paths] if include_paths else []
    
    for cat in categories:
        ctgry_nm = cat.get("ctgry_nm", "").strip()
        ctgry_path_raw = cat.get("ctgry_path") or ctgry_nm
        ctgry_path = normalize_category_path(ctgry_path_raw)
        category_sn = cat.get("com_ctgry_sn")
        
        if not category_sn:
            continue
        
        if any(ex_keyword in ctgry_nm or ex_keyword in ctgry_path for ex_keyword in exclude_keywords):
            continue
        
        path_match = ctgry_path in normalized_include_paths if normalized_include_paths else False
        
        path_prefix_match = False
        if normalized_include_paths:
            for include_path in normalized_include_paths:
                if ctgry_path == include_path or ctgry_path.startswith(include_path + " > "):
                    path_prefix_match = True
                    break
                include_segments = [s.strip().lower() for s in include_path.split(" > ")]
                path_segments = [s.strip().lower() for s in ctgry_path.split(" > ")]
                if len(include_segments) <= len(path_segments):
                    match = True
                    for i, include_seg in enumerate(include_segments):
                        if i >= len(path_segments):
                            match = False
                            break
                        if (include_seg not in path_segments[i] and 
                            path_segments[i] not in include_seg and
                            not any(keyword.lower() in path_segments[i] for keyword in include_seg.split() if len(keyword) > 3)):
                            match = False
                            break
                    if match:
                        path_prefix_match = True
                        break
        
        prefix_match = any(
            ctgry_path.startswith(prefix) or ctgry_path.startswith(prefix + " > ")
            for prefix in include_prefixes
            if prefix
        ) if include_prefixes else False
        
        keyword_match = False
        if include_keywords:
            for keyword in include_keywords:
                keyword_lower = keyword.lower()
                if (keyword_lower in ctgry_nm.lower() or 
                    keyword_lower in ctgry_path.lower() or
                    any(keyword_lower in segment.lower() for segment in ctgry_path.split(" > "))):
                    keyword_match = True
                    break
        
        if not (path_match or path_prefix_match or prefix_match or keyword_match):
            continue
        
        sn_str = str(category_sn)
        if sn_str not in matched_category_sns:
            matched_category_sns.append(sn_str)
            matched_paths.add(ctgry_path)
            logger.debug(
                "Matched category '%s' with VISIT SEOUL category_sn '%s' (name: %s, path: %s)",
                category,
                sn_str,
                ctgry_nm,
                ctgry_path
            )
    
    if matched_category_sns:
        logger.info(
            "Mapped category '%s' to %d VISIT SEOUL category_sn(s): %s",
            category,
            len(matched_category_sns),
            matched_category_sns
        )
        logger.info(
            "Matched paths for '%s': %s",
            category,
            sorted(matched_paths)
        )
        return matched_category_sns
    
    logger.warning(f"Could not find matching VISIT SEOUL category for category: {category}")
    logger.warning(f"  Searched paths: {normalized_include_paths}")
    logger.warning(f"  Searched prefixes: {include_prefixes}")
    logger.warning(f"  Searched keywords: {include_keywords[:5]}...")
    return None


def search_places_by_category(
    category: Optional[str] = None,
    lang_code_id: str = "en",
    keyword: Optional[str] = None,
    sort_type: str = "latest",
    page_no: int = 1,
    retry_count: int = 5,
    retry_delay: float = 1.0
) -> Dict:
    url = f"{VISIT_SEOUL_BASE_URL}/contents/list"
    headers = get_api_headers()
    headers["Content-Type"] = "application/json;charset=UTF-8"
    
    payload = {
        "lang_code_id": lang_code_id,
        "sort_type": sort_type,
        "page_no": page_no
    }
    
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
    retry_count: int = 5,
    retry_delay: float = 1.0
) -> Optional[Dict]:
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
    data = detail if detail else item
    lang_code_id = data.get("lang_code_id") or item.get("lang_code_id")
    cate_depth_raw = data.get("cate_depth") or item.get("cate_depth") or []
    cate_depth = [
        depth.strip()
        for depth in cate_depth_raw
        if isinstance(depth, str) and depth.strip()
    ] if isinstance(cate_depth_raw, list) else []
    tags = []
    multi_lang_list = data.get("multi_lang_list") or item.get("multi_lang_list")
    schedule = {}
    traffic_data: Dict = {}
    extra_data: Dict = {}
    tourist_data: Dict = {}
    
    cid = data.get("cid") or item.get("cid")
    logger.debug(f"Parsing VISIT SEOUL place - CID: {cid}")
    logger.debug(f"Item keys: {list(item.keys()) if item else 'None'}")
    logger.debug(f"Detail keys: {list(detail.keys()) if detail else 'None'}")
    
    latitude = None
    longitude = None
    
    if detail and detail.get("traffic"):
        traffic_data = detail.get("traffic") or {}
        if traffic_data.get("map_position_y"):
            try:
                latitude = float(traffic_data["map_position_y"])
            except (ValueError, TypeError):
                pass
        if traffic_data.get("map_position_x"):
            try:
                longitude = float(traffic_data["map_position_x"])
            except (ValueError, TypeError):
                pass
    
    address = None
    if traffic_data:
        address = traffic_data.get("new_adres") or traffic_data.get("adres")
    
    image_url = None
    images = []
    
    if detail:
        detail_tags = detail.get("tag") or []
        if isinstance(detail_tags, list):
            tags = [tag for tag in detail_tags if isinstance(tag, str)]
        elif detail_tags:
            tags = [str(detail_tags)]
        
        schedule = {
            "start_date": detail.get("schdul_info_bgnde"),
            "end_date": detail.get("schdul_info_endde")
        }
        
        extra_data = detail.get("extra") or {}
        tourist_data = detail.get("tourist") or {}
        
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
    
    overview = None
    content = None
    homepage = None
    tel = None
    usage_info = None
    tip = None
    detail_info = {}
    
    if detail:
        overview = detail.get("post_desc") or detail.get("sumry")
        content = overview
        
        if extra_data:
            homepage = extra_data.get("cmmn_hmpg_url")
            tel = extra_data.get("cmmn_telno")
            tip = extra_data.get("cmmn_tip") or extra_data.get("tip")
            
            logger.debug(f"Extra keys: {list(extra_data.keys()) if extra_data else 'None'}")
            logger.debug(f"Homepage: {homepage}, Tel: {tel}, Tip: {tip}")
            
            detail_info = {
                "opening_hours": extra_data.get("cmmn_use_time") or "",
                "closed_days": extra_data.get("closed_days") or "",
                "business_days": extra_data.get("business_days") or extra_data.get("cmmn_business_days") or "",
                "tel": tel or "",
                "traffic_info": traffic_data.get("subway_info") or "" if traffic_data else "",
                "homepage": homepage or "",
                "important": extra_data.get("cmmn_important") or "",
                "admission_fee": extra_data.get("trrsrt_use_chrge") or "",
                "admission_fee_guidance": extra_data.get("trrsrt_use_chrge_guidance") or "",
                "disabled_facility": extra_data.get("disabled_facility") or []
            }
            
            usage_info_parts = []
            if extra_data.get("cmmn_use_time"):
                usage_info_parts.append(f"Opening hours: {extra_data['cmmn_use_time']}")
            if extra_data.get("closed_days"):
                usage_info_parts.append(f"Closed days: {extra_data['closed_days']}")
            if extra_data.get("trrsrt_use_chrge_guidance"):
                usage_info_parts.append(f"Admission fee: {extra_data['trrsrt_use_chrge_guidance']}")
            if extra_data.get("cmmn_important"):
                usage_info_parts.append(f"Important: {extra_data['cmmn_important']}")
            
            usage_info = "\n".join(usage_info_parts) if usage_info_parts else None
        else:
            logger.debug("No 'extra' field in detail")
    else:
        overview = item.get("sumry")
        content = overview
        logger.debug(f"Using item data - overview: {overview[:100] if overview else 'None'}...")
    
    category_sn = data.get("com_ctgry_sn") or item.get("com_ctgry_sn")
    
    parsed_data = {
        "content_id": data.get("cid") or item.get("cid"),
        "content_type_id": None,
        "name": data.get("post_sj") or item.get("post_sj"),
        "category": category_sn,
        "lang_code_id": lang_code_id,
        "cate_depth": cate_depth,
        "multi_lang_list": multi_lang_list,
        "tags": tags,
        "schedule": schedule,
        "traffic": traffic_data,
        "extra": extra_data,
        "tourist": tourist_data,
        "address": address,
        "latitude": latitude,
        "longitude": longitude,
        "image_url": image_url,
        "images": images,
        "overview": overview or item.get("sumry"),
        "content": content,
        "homepage": homepage,
        "tel": tel,
        "usage_info": usage_info,
        "tip": tip,
        "detail_info": detail_info,
        "raw_data": {
            "item": item,
            "detail": detail
        }
    }
    
    logger.info(f"Parsed place - Name: {parsed_data['name']}, Content: {bool(content)}, Detail_info keys: {list(detail_info.keys())}, category_sn: {category_sn}")
    
    return parsed_data


def collect_all_places_by_category(
    category_sn: Optional[str] = None,
    lang_code_id: str = "en",
    max_places: Optional[int] = None,
    delay_between_pages: float = 1.0
) -> List[Dict]:
    all_places: List[Dict] = []
    seen_cids: Set[str] = set()
    page_no = 1
    limit_desc = max_places if max_places else "ALL"
    
    category_desc = category_sn if category_sn else "all categories"
    logger.info(f"Starting VISIT SEOUL collection for category: {category_desc}, target: {limit_desc}")
    
    while True:
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
        
        page_size = paging.get("page_size", 50)
        total_count = paging.get("total_count")
        
        for place in places:
            cid = (
                place.get("cid")
                or place.get("contentId")
                or place.get("content_id")
                or place.get("id")
            )
            if cid and cid in seen_cids:
                continue
            
            if cid:
                seen_cids.add(cid)
            
            all_places.append(place)
            
            if max_places and len(all_places) >= max_places:
                logger.info(f"Reached requested max_places ({max_places}) for category {category_desc}")
                return all_places
        
        logger.info(
            "Collected %d places so far (page %d, total reported: %s)",
            len(all_places),
            page_no,
            total_count if total_count is not None else "unknown"
        )
        
        if not places or len(places) < page_size:
            break
        
        page_no += 1
        time.sleep(delay_between_pages)
    
    category_desc = category_sn if category_sn else "all categories"
    logger.info(f"Total collected: {len(all_places)} places for category {category_desc}")
    return all_places
