"""VLM Service - GPT-4V Image Analysis"""

import os
import base64
import logging
from typing import Optional, Dict, List
from io import BytesIO
from PIL import Image

logger = logging.getLogger(__name__)

openai_client = None
OPENAI_AVAILABLE = False

try:
    from openai import OpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        openai_client = OpenAI(api_key=api_key)
        OPENAI_AVAILABLE = True
    else:
        logger.warning("OPENAI_API_KEY not set")
except ImportError:
    logger.warning("OpenAI not installed")
except Exception as e:
    logger.warning(f"Failed to initialize OpenAI: {e}")


def compress_image(image_bytes: bytes, max_size: int = 1024) -> bytes:
    """Compress image for API efficiency"""
    try:
        img = Image.open(BytesIO(image_bytes))
        
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        if max(img.size) > max_size:
            ratio = max_size / max(img.size)
            new_size = tuple(int(dim * ratio) for dim in img.size)
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        output = BytesIO()
        img.save(output, format='JPEG', quality=85, optimize=True)
        return output.getvalue()
    
    except Exception as e:
        logger.warning(f"Image compression failed: {e}")
        return image_bytes


def analyze_image_gpt4v(
    image_bytes: bytes,
    prompt: str,
    max_tokens: int = 500
) -> Optional[str]:
    """Analyze image using GPT-4o-mini"""
    if not OPENAI_AVAILABLE:
        logger.error("OpenAI not available")
        return None
    
    try:
        compressed_image = compress_image(image_bytes)
        image_base64 = base64.b64encode(compressed_image).decode('utf-8')
        
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=max_tokens,
            temperature=0.3
        )
        
        result = response.choices[0].message.content
        logger.info(f"GPT-4V analysis complete: {len(result)} chars")
        return result
    
    except Exception as e:
        logger.error(f"GPT-4V error: {e}", exc_info=True)
        return None


def analyze_place_image(
    image_bytes: bytes,
    nearby_places: Optional[List[Dict]] = None,
    language: str = "ko"
) -> Optional[str]:
    """Analyze place image"""
    prompt = build_place_analysis_prompt(nearby_places, language)
    
    if not OPENAI_AVAILABLE:
        error_msg = "GPT-4V를 사용할 수 없습니다." if language == "ko" else "GPT-4V unavailable."
        logger.error(error_msg)
        return None
    
    result = analyze_image_gpt4v(image_bytes, prompt)
    
    if not result:
        error_msg = "이미지 분석에 실패했습니다." if language == "ko" else "Image analysis failed."
        logger.error(error_msg)
        return None
    
    return result


def build_place_analysis_prompt(
    nearby_places: Optional[List[Dict]] = None,
    language: str = "ko"
) -> str:
    """Build place analysis prompt"""
    
    if language == "ko":
        prompt = """당신은 서울 관광 전문가입니다. 이미지를 분석하여 다음을 제공하세요:

1. 이 장소가 무엇인지 정확히 식별
2. 건축 양식, 색상, 특징적인 요소 설명
3. 역사적/문화적 배경 (알려진 경우)
4. 이 장소의 대표적인 특징

응답 형식:
장소명: [구체적인 이름]
카테고리: [관광지/음식점/카페/공원/역사유적 등]
설명: [2-3문장으로 장소 설명]
특징: [시각적 특징과 특별한 점]
신뢰도: [high/medium/low]"""
        
        if nearby_places:
            places_text = "\n".join([
                f"- {p.get('name', 'Unknown')} ({p.get('category', 'N/A')}) - {p.get('distance_km', 0):.2f}km"
                for p in nearby_places[:5]
            ])
            prompt += f"\n\n참고: GPS 기반 주변 장소 (1km 이내):\n{places_text}\n"
            prompt += "\n위 후보 중 이미지와 일치하는 장소가 있다면 우선 고려하세요."
    
    else:
        prompt = """You are a Seoul tourism expert. Analyze this image and provide:

1. Identify the exact place/location
2. Describe architectural style, colors, distinctive features
3. Historical/cultural context (if known)
4. Key characteristics of this place

Response Format:
Place Name: [specific name]
Category: [tourist spot/restaurant/cafe/park/historic site, etc.]
Description: [2-3 sentences describing the place]
Features: [visual characteristics and special points]
Confidence: [high/medium/low]"""
        
        if nearby_places:
            places_text = "\n".join([
                f"- {p.get('name', 'Unknown')} ({p.get('category', 'N/A')}) - {p.get('distance_km', 0):.2f}km"
                for p in nearby_places[:5]
            ])
            prompt += f"\n\nReference: Nearby places within 1km (GPS-based):\n{places_text}\n"
            prompt += "\nIf the image matches any of these candidates, prioritize them."
    
    return prompt


def extract_place_info_from_vlm_response(vlm_response: str) -> Dict[str, str]:
    """Extract place information from VLM response"""
    info = {
        "place_name": "",
        "category": "",
        "description": "",
        "features": "",
        "confidence": "low"
    }
    
    try:
        lines = vlm_response.split('\n')
        for line in lines:
            line = line.strip()
            
            if line.startswith(('장소명:', 'Place Name:')):
                info["place_name"] = line.split(':', 1)[1].strip()
            
            elif line.startswith(('카테고리:', 'Category:')):
                info["category"] = line.split(':', 1)[1].strip()
            
            elif line.startswith(('설명:', 'Description:')):
                info["description"] = line.split(':', 1)[1].strip()
            
            elif line.startswith(('특징:', 'Features:')):
                info["features"] = line.split(':', 1)[1].strip()
            
            elif line.startswith(('신뢰도:', 'Confidence:')):
                confidence_text = line.split(':', 1)[1].strip().lower()
                if 'high' in confidence_text or '높' in confidence_text:
                    info["confidence"] = "high"
                elif 'medium' in confidence_text or '중' in confidence_text:
                    info["confidence"] = "medium"
                else:
                    info["confidence"] = "low"
    
    except Exception as e:
        logger.warning(f"Failed to extract place info: {e}")
    
    return info


def calculate_confidence_score(
    vlm_info: Dict[str, str],
    vector_similarity: Optional[float] = None,
    gps_distance_km: Optional[float] = None
) -> float:
    """Calculate confidence score"""
    score = 0.0
    
    confidence_map = {"high": 0.4, "medium": 0.25, "low": 0.1}
    score += confidence_map.get(vlm_info.get("confidence", "low"), 0.1)
    
    if vector_similarity is not None:
        score += vector_similarity * 0.4
    
    if gps_distance_km is not None:
        gps_score = max(0, 1 - (gps_distance_km / 1.0))
        score += gps_score * 0.2
    
    return round(min(score, 1.0), 2)
