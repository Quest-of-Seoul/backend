"""Place Parser Service"""

import logging
import html
from typing import Dict, Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def extract_text(text: Optional[str]) -> str:
    if not text:
        return ""
    soup = BeautifulSoup(text, "html.parser")
    for tag in soup(["style", "script"]):
        tag.decompose()
    text = soup.get_text(" ", strip=True)
    return html.unescape(text)


def parse_rag_text(visit_seoul_data: Dict) -> str:
    parts = []
    
    name = visit_seoul_data.get("name") or ""
    if name:
        parts.append(f"[{name}]")
    
    category_value = visit_seoul_data.get("category_label") or visit_seoul_data.get("category") or ""
    if category_value:
        parts.append(f"[Category] {category_value}")
    
    parts.append("")
    
    raw_content = visit_seoul_data.get("content") or visit_seoul_data.get("overview") or ""
    content = extract_text(raw_content)
    if content:
        parts.append("[Content]")
        parts.append(content)
        parts.append("")
    
    vs_detail = visit_seoul_data.get("detail_info") or {}
    opening_hours = vs_detail.get("opening_hours") or ""
    if opening_hours:
        parts.append(f"[Opening hours] {opening_hours}")
    
    closed_days = vs_detail.get("closed_days") or ""
    if closed_days:
        parts.append(f"[Closed days] {closed_days}")
    
    business_days = vs_detail.get("business_days") or ""
    if business_days:
        parts.append(f"[Business days] {business_days}")
    
    parts.append("")
    
    tel = ""
    if visit_seoul_data.get("detail_info"):
        tel = visit_seoul_data["detail_info"].get("tel") or ""
    if tel:
        parts.append(f"[Phone number] {tel}")
    
    address = visit_seoul_data.get("address") or ""
    if address:
        parts.append(f"[Address] {address}")
    
    traffic_info = ""
    if visit_seoul_data.get("detail_info"):
        traffic_info = visit_seoul_data["detail_info"].get("traffic_info") or ""
    if traffic_info:
        parts.append(f"[Traffic information] {traffic_info}")
    
    tip = visit_seoul_data.get("tip") or ""
    if tip:
        parts.append("[Tip]")
        parts.append(tip)
    
    rag_text = "\n".join(parts)
    
    max_length = 2000
    if len(rag_text) > max_length:
        rag_text = rag_text[:max_length] + "..."
        logger.warning(f"RAG text truncated to {max_length} characters")
    
    return rag_text


def merge_place_data(tour_data: Optional[Dict], visit_seoul_data: Dict, category: Optional[str] = None) -> Dict:
    name = visit_seoul_data.get("name") or ""
    visit_seoul_category_sn = visit_seoul_data.get("category")
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
    
    raw_description = visit_seoul_data.get("content") or visit_seoul_data.get("overview")
    description = extract_text(raw_description)
    if raw_description:
        logger.debug(f"Description from post_desc, length: {len(raw_description)}")
    
    content_for_metadata = visit_seoul_data.get("content") or visit_seoul_data.get("overview") or ""
    clean_content_for_metadata = extract_text(content_for_metadata)
    metadata = {
        "visit_seoul": {
            "content_id": visit_seoul_data.get("content_id"),
            "lang_code_id": visit_seoul_data.get("lang_code_id"),
            "content": clean_content_for_metadata,
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
    
    metadata["rag_text"] = parse_rag_text(visit_seoul_data)
    
    if visit_seoul_data.get("detail_info"):
        vs_detail = visit_seoul_data["detail_info"]
        metadata["opening_hours"] = vs_detail.get("opening_hours") or ""
        metadata["closed_days"] = vs_detail.get("closed_days") or ""
        metadata["phone"] = vs_detail.get("tel") or ""
        metadata["traffic_info"] = vs_detail.get("traffic_info") or ""
        metadata["tip"] = visit_seoul_data.get("tip") or ""
    
    source = "visit_seoul"
    
    district = None
    
    if name and len(name) > 255:
        logger.warning(f"Place name exceeds 255 characters, truncating: {name[:50]}...")
        name = name[:255]
    
    if final_category and len(final_category) > 50:
        logger.warning(f"Category exceeds 50 characters, truncating: {final_category[:50]}...")
        final_category = final_category[:50]
    
    if address and len(address) > 500:
        logger.warning(f"Address exceeds 500 characters, truncating: {address[:50]}...")
        address = address[:500]
    
    place_data = {
        "name": name,
        "description": description,
        "category": final_category,
        "address": address if address else None,
        "district": district,
        "latitude": float(latitude) if latitude else None,
        "longitude": float(longitude) if longitude else None,
        "image_url": image_url if image_url else None,
        "images": images if images else None,
        "metadata": metadata,
        "source": source,
        "is_active": True
    }
    
    return place_data
