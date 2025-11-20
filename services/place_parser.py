"""Place Parser Service"""

import logging
import re
from typing import Dict, Optional
from html import unescape

logger = logging.getLogger(__name__)


def clean_html(text: Optional[str]) -> str:
    """
    HTML 태그 제거 및 정리
    
    Args:
        text: 원본 텍스트
    
    Returns:
        정리된 텍스트
    """
    if not text:
        return ""
    
    text = re.sub(r'<[^>]+>', '', text)
    text = unescape(text)
    text = re.sub(r'\s+', ' ', text)    
    text = text.strip()
    return text


def parse_rag_text(tour_data: Dict, visit_seoul_data: Optional[Dict] = None) -> str:
    """
    RAG용 통합 텍스트 생성
    
    Args:
        tour_data: TourAPI 데이터
        visit_seoul_data: VISIT SEOUL API 데이터 (선택)
    
    Returns:
        RAG용 텍스트
    """
    parts = []
    
    # 장소명
    name = tour_data.get("name") or ""
    name_en = tour_data.get("name_en") or ""
    if name:
        if name_en:
            parts.append(f"[{name}] ({name_en})")
        else:
            parts.append(f"[{name}]")
    
    # 카테고리
    category = tour_data.get("category") or ""
    if category:
        parts.append(f"[카테고리] {category}")
    
    parts.append("")  # 빈 줄
    
    # 개요 (TourAPI)
    overview = clean_html(tour_data.get("overview") or "")
    if overview:
        parts.append("[개요]")
        parts.append(overview)
        parts.append("")
    
    # 상세정보 (TourAPI)
    detail_info = clean_html(tour_data.get("detail_info") or "")
    if detail_info:
        parts.append("[상세정보]")
        parts.append(detail_info)
        parts.append("")
    
    # 이용안내 (TourAPI)
    usage_info = tour_data.get("usage_info") or ""
    if usage_info:
        parts.append("[이용안내]")
        parts.append(usage_info)
        parts.append("")
    
    # VISIT SEOUL 내용
    if visit_seoul_data:
        vs_content = clean_html(visit_seoul_data.get("content") or "")
        if vs_content:
            parts.append("[VISIT SEOUL 내용]")
            parts.append(vs_content)
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
    
    # 입장료
    admission_fee = tour_data.get("admission_fee") or ""
    if admission_fee:
        parts.append(f"[입장료] {admission_fee}")
    
    # 전화번호
    tel = tour_data.get("tel") or ""
    if visit_seoul_data and visit_seoul_data.get("detail_info"):
        tel = visit_seoul_data["detail_info"].get("tel") or tel
    if tel:
        parts.append(f"[전화번호] {tel}")
    
    # 주소
    address = tour_data.get("address") or ""
    if visit_seoul_data and visit_seoul_data.get("detail_info"):
        address = visit_seoul_data["detail_info"].get("address") or address
    if address:
        parts.append(f"[주소] {address}")
    
    # 교통정보
    traffic_info = ""
    if visit_seoul_data and visit_seoul_data.get("detail_info"):
        traffic_info = visit_seoul_data["detail_info"].get("traffic_info") or ""
    if traffic_info:
        parts.append(f"[교통정보] {traffic_info}")
    
    # 팁
    tip = ""
    if visit_seoul_data:
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


def merge_place_data(tour_data: Dict, visit_seoul_data: Optional[Dict] = None) -> Dict:
    """
    TourAPI와 VISIT SEOUL API 데이터 통합
    
    Args:
        tour_data: TourAPI 데이터
        visit_seoul_data: VISIT SEOUL API 데이터 (선택)
    
    Returns:
        통합된 장소 데이터 (DB 저장용)
    """
    # 기본 정보 (TourAPI 우선)
    name = tour_data.get("name") or ""
    name_en = tour_data.get("name_en") or ""
    category = tour_data.get("category") or ""
    address = tour_data.get("address") or ""
    latitude = tour_data.get("latitude")
    longitude = tour_data.get("longitude")
    image_url = tour_data.get("image_url") or ""
    images = tour_data.get("images") or []
    
    # VISIT SEOUL 데이터로 보완
    if visit_seoul_data:
        # 이름 보완
        if not name_en and visit_seoul_data.get("name_en"):
            name_en = visit_seoul_data["name_en"]
        
        # 주소 보완
        if not address and visit_seoul_data.get("address"):
            address = visit_seoul_data["address"]
        
        # 좌표 보완
        if not latitude and visit_seoul_data.get("latitude"):
            latitude = visit_seoul_data["latitude"]
        if not longitude and visit_seoul_data.get("longitude"):
            longitude = visit_seoul_data["longitude"]
        
        # 이미지 보완
        if not image_url and visit_seoul_data.get("image_url"):
            image_url = visit_seoul_data["image_url"]
        if visit_seoul_data.get("images"):
            images.extend([img for img in visit_seoul_data["images"] if img not in images])
    
    # description 생성 (개요 + VISIT SEOUL 내용)
    description_parts = []
    if tour_data.get("overview"):
        description_parts.append(clean_html(tour_data["overview"]))
    if visit_seoul_data and visit_seoul_data.get("content"):
        vs_content = clean_html(visit_seoul_data["content"])
        if vs_content and vs_content not in description_parts:
            description_parts.append(vs_content)
    description = "\n\n".join(description_parts) if description_parts else None
    
    # metadata 생성
    metadata = {
        "tour_api": {
            "content_id": tour_data.get("content_id"),
            "content_type_id": tour_data.get("content_type_id"),
            "overview": clean_html(tour_data.get("overview") or ""),
            "detail_info": clean_html(tour_data.get("detail_info") or ""),
            "usage_info": tour_data.get("usage_info") or "",
            "homepage": tour_data.get("homepage") or "",
            "tel": tour_data.get("tel") or ""
        }
    }
    
    if visit_seoul_data:
        metadata["visit_seoul"] = {
            "content_id": visit_seoul_data.get("content_id"),
            "content": clean_html(visit_seoul_data.get("content") or ""),
            "detail_info": visit_seoul_data.get("detail_info") or {},
            "tip": visit_seoul_data.get("tip") or ""
        }
    
    # 통합 정보
    metadata["rag_text"] = parse_rag_text(tour_data, visit_seoul_data)
    
    # 통합 이용정보
    if visit_seoul_data and visit_seoul_data.get("detail_info"):
        vs_detail = visit_seoul_data["detail_info"]
        metadata["opening_hours"] = vs_detail.get("opening_hours") or ""
        metadata["closed_days"] = vs_detail.get("closed_days") or ""
        metadata["phone"] = vs_detail.get("tel") or tour_data.get("tel") or ""
        metadata["traffic_info"] = vs_detail.get("traffic_info") or ""
        metadata["tip"] = visit_seoul_data.get("tip") or ""
    else:
        metadata["phone"] = tour_data.get("tel") or ""
    
    metadata["homepage"] = tour_data.get("homepage") or ""
    metadata["admission_fee"] = tour_data.get("admission_fee") or ""
    
    # source 결정
    source = "both" if visit_seoul_data else "tour_api"
    
    place_data = {
        "name": name,
        "name_en": name_en if name_en else None,
        "description": description,
        "category": category,
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
