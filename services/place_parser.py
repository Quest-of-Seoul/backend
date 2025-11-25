"""Place Parser Service"""

import logging
import re
from typing import Dict, Optional
from html import unescape

logger = logging.getLogger(__name__)


def clean_html(text: Optional[str]) -> str:
    """
    HTML 태그 제거 및 정리 (간단한 HTML 태그만 제거)
    
    Args:
        text: 원본 텍스트
    
    Returns:
        정리된 텍스트
    """
    if not text:
        return ""
    
    # script/style 블록 제거
    text = re.sub(
        r'<(script|style)[^>]*?>.*?</\1>',
        '',
        text,
        flags=re.IGNORECASE | re.DOTALL
    )

    # 줄바꿈 태그를 개행으로 변환
    text = re.sub(r'<\s*br\s*/?>', '\n', text, flags=re.IGNORECASE)

    # 블록 단위 태그 종료 시 개행 추가 (단락 구조 유지)
    block_tags = r'(?:p|div|section|article|li|ul|ol|table|tr|td|th|h[1-6]|hr)'
    text = re.sub(rf'</\s*{block_tags}\s*>', '\n', text, flags=re.IGNORECASE)

    # HTML 주석 제거
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
    
    # HTML 태그 제거
    text = re.sub(r'<[^>]+>', '', text)
    
    # HTML 엔티티 디코딩
    text = unescape(text)

    # 개행 통일
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # 줄 내 공백 정리 (개행 보존)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{2,}', '\n', text)
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(line for line in lines if line)
    
    # 앞뒤 공백 제거
    text = text.strip()
    
    return text


def parse_rag_text(visit_seoul_data: Dict) -> str:
    """
    RAG용 통합 텍스트 생성
    
    Args:
        visit_seoul_data: VISIT SEOUL API 데이터
    
    Returns:
        RAG용 텍스트
    """
    parts = []
    
    # 장소명
    name = visit_seoul_data.get("name") or ""
    if name:
        parts.append(f"[{name}]")
    
    # 카테고리 (우선 사용자 정의 카테고리명, 없으면 com_ctgry_sn)
    category_value = visit_seoul_data.get("category_label") or visit_seoul_data.get("category") or ""
    if category_value:
        parts.append(f"[카테고리] {category_value}")
    
    parts.append("")  # 빈 줄
    
    # VISIT SEOUL 내용 (content 또는 overview) - HTML 제거 후 사용
    raw_content = visit_seoul_data.get("content") or visit_seoul_data.get("overview") or ""
    content = clean_html(raw_content)
    if content:
        parts.append("[내용]")
        parts.append(content)
        parts.append("")
    
    # 이용시간
    vs_detail = visit_seoul_data.get("detail_info") or {}
    opening_hours = vs_detail.get("opening_hours") or ""
    if opening_hours:
        parts.append(f"[이용시간] {opening_hours}")
    
    # 휴무일
    closed_days = vs_detail.get("closed_days") or ""
    if closed_days:
        parts.append(f"[휴무일] {closed_days}")
    
    # 영업일
    business_days = vs_detail.get("business_days") or ""
    if business_days:
        parts.append(f"[영업일] {business_days}")
    
    parts.append("")
    
    # 전화번호
    tel = ""
    if visit_seoul_data.get("detail_info"):
        tel = visit_seoul_data["detail_info"].get("tel") or ""
    if tel:
        parts.append(f"[전화번호] {tel}")
    
    # 주소
    address = visit_seoul_data.get("address") or ""
    if address:
        parts.append(f"[주소] {address}")
    
    # 교통정보
    traffic_info = ""
    if visit_seoul_data.get("detail_info"):
        traffic_info = visit_seoul_data["detail_info"].get("traffic_info") or ""
    if traffic_info:
        parts.append(f"[교통정보] {traffic_info}")
    
    # 팁
    tip = visit_seoul_data.get("tip") or ""
    if tip:
        parts.append("[팁]")
        parts.append(tip)
    
    # 최종 텍스트 조합
    rag_text = "\n".join(parts)
    
    # 최대 길이 제한 (RAG 검색 효율성 고려)
    max_length = 2000
    if len(rag_text) > max_length:
        rag_text = rag_text[:max_length] + "..."
        logger.warning(f"RAG text truncated to {max_length} characters")
    
    return rag_text


def merge_place_data(tour_data: Optional[Dict], visit_seoul_data: Dict, category: Optional[str] = None) -> Dict:
    """
    VISIT SEOUL API 데이터를 장소 데이터로 변환
    
    Args:
        tour_data: TourAPI 데이터 (사용하지 않음, 호환성을 위해 유지)
        visit_seoul_data: VISIT SEOUL API 데이터
        category: 우리가 정의한 카테고리명 (Attractions, History, Culture 등)
    
    Returns:
        통합된 장소 데이터 (DB 저장용)
    """
    # VISIT SEOUL 데이터 사용
    name = visit_seoul_data.get("name") or ""
    visit_seoul_category_sn = visit_seoul_data.get("category")
    # category는 파라미터로 전달받은 것을 사용, 없으면 VISIT SEOUL 카테고리명/코드
    final_category = (
        category
        or visit_seoul_data.get("category_label")
        or visit_seoul_category_sn
        or ""
    )
    address = visit_seoul_data.get("address") or ""
    latitude = visit_seoul_data.get("latitude")
    longitude = visit_seoul_data.get("longitude")
    image_url = visit_seoul_data.get("image_url") or ""
    images = visit_seoul_data.get("images") or []
    
    # description 생성 (post_desc 그대로 사용) + HTML 정리
    raw_description = visit_seoul_data.get("content") or visit_seoul_data.get("overview")
    description = clean_html(raw_description)
    if raw_description:
        logger.debug(f"Description from post_desc, length: {len(raw_description)}")
    
    # metadata 생성
    # content가 없으면 overview 사용
    content_for_metadata = visit_seoul_data.get("content") or visit_seoul_data.get("overview") or ""
    clean_content_for_metadata = clean_html(content_for_metadata)
    metadata = {
        "visit_seoul": {
            "content_id": visit_seoul_data.get("content_id"),
            "lang_code_id": visit_seoul_data.get("lang_code_id"),
            "content": clean_content_for_metadata,  # post_desc 정제 후 사용
            "detail_info": visit_seoul_data.get("detail_info") or {},
            "tip": visit_seoul_data.get("tip") or "",
            "com_ctgry_sn": visit_seoul_category_sn,
            "category_label": visit_seoul_data.get("category_label") or category,
            "cate_depth": visit_seoul_data.get("cate_depth") or [],
            "multi_lang_list": visit_seoul_data.get("multi_lang_list"),
            "tags": visit_seoul_data.get("tags") or [],
            "schedule": visit_seoul_data.get("schedule") or {},
            "traffic": visit_seoul_data.get("traffic") or {},
            "extra": visit_seoul_data.get("extra") or {},
            "tourist": visit_seoul_data.get("tourist") or {}
        }
    }
    
    metadata["tags"] = visit_seoul_data.get("tags") or []
    metadata["schedule"] = visit_seoul_data.get("schedule") or {}
    metadata["traffic"] = visit_seoul_data.get("traffic") or {}
    metadata["multi_lang_list"] = visit_seoul_data.get("multi_lang_list")
    metadata["category_label"] = visit_seoul_data.get("category_label") or category
    
    # 통합 정보
    metadata["rag_text"] = parse_rag_text(visit_seoul_data)
    
    # 통합 이용정보
    if visit_seoul_data.get("detail_info"):
        vs_detail = visit_seoul_data["detail_info"]
        metadata["opening_hours"] = vs_detail.get("opening_hours") or ""
        metadata["closed_days"] = vs_detail.get("closed_days") or ""
        metadata["phone"] = vs_detail.get("tel") or ""
        metadata["traffic_info"] = vs_detail.get("traffic_info") or ""
        metadata["tip"] = visit_seoul_data.get("tip") or ""
    
    # source 결정
    source = "visit_seoul"
    
    place_data = {
        "name": name,
        "description": description,
        "category": final_category,  # 우리가 정의한 카테고리명 사용
        "address": address if address else None,
        "latitude": float(latitude) if latitude else None,
        "longitude": float(longitude) if longitude else None,
        "image_url": image_url if image_url else None,
        "images": images if images else None,
        "metadata": metadata,
        "source": source,
        "is_active": True
    }
    
    return place_data
