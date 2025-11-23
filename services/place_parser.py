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
    
    # HTML 태그 제거
    text = re.sub(r'<[^>]+>', '', text)
    
    # HTML 엔티티 디코딩
    text = unescape(text)
    
    # 연속된 공백 정리
    text = re.sub(r'\s+', ' ', text)
    
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
    
    # 카테고리 (RAG 텍스트에는 com_ctgry_sn 사용 가능, 하지만 실제 DB 저장 시에는 우리 카테고리명 사용)
    category = visit_seoul_data.get("category") or ""
    if category:
        parts.append(f"[카테고리] {category}")
    
    parts.append("")  # 빈 줄
    
    # VISIT SEOUL 내용 (content 또는 overview) - post_desc 그대로 사용
    content = visit_seoul_data.get("content") or visit_seoul_data.get("overview") or ""
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
    # category는 파라미터로 전달받은 것을 사용, 없으면 visit_seoul_data에서 가져옴
    final_category = category or visit_seoul_data.get("category") or ""
    address = visit_seoul_data.get("address") or ""
    latitude = visit_seoul_data.get("latitude")
    longitude = visit_seoul_data.get("longitude")
    image_url = visit_seoul_data.get("image_url") or ""
    images = visit_seoul_data.get("images") or []
    
    # description 생성 (post_desc 그대로 사용)
    description = visit_seoul_data.get("content") or visit_seoul_data.get("overview")
    if description:
        logger.debug(f"Description from post_desc, length: {len(description)}")
    
    # metadata 생성
    # content가 없으면 overview 사용
    content_for_metadata = visit_seoul_data.get("content") or visit_seoul_data.get("overview") or ""
    metadata = {
        "visit_seoul": {
            "content_id": visit_seoul_data.get("content_id"),
            "content": content_for_metadata,  # post_desc 그대로 사용
            "detail_info": visit_seoul_data.get("detail_info") or {},
            "tip": visit_seoul_data.get("tip") or "",
            "com_ctgry_sn": category  # com_ctgry_sn 추가
        }
    }
    
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
