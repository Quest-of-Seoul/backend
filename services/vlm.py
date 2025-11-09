"""
VLM (Vision-Language Model) service
GPT-4V를 사용한 이미지 분석 및 장소 설명
"""

import os
import base64
from typing import Optional, Dict, List
from io import BytesIO
from PIL import Image

# OpenAI GPT-4V
openai_client = None
OPENAI_AVAILABLE = False

try:
    from openai import OpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        openai_client = OpenAI(api_key=api_key)
        OPENAI_AVAILABLE = True
    else:
        print("[VLM] ⚠️ OPENAI_API_KEY not set. GPT-4V will be unavailable.")
except ImportError:
    print("[VLM] ⚠️ OpenAI not installed. GPT-4V will be unavailable.")
except Exception as e:
    print(f"[VLM] ⚠️ Failed to initialize OpenAI client: {e}")


def compress_image(image_bytes: bytes, max_size: int = 1024) -> bytes:
    """
    이미지 압축 (VLM API 효율성 향상)
    
    Args:
        image_bytes: 원본 이미지 바이트
        max_size: 최대 가로/세로 크기 (픽셀)
    
    Returns:
        압축된 이미지 바이트
    """
    try:
        img = Image.open(BytesIO(image_bytes))
        
        # EXIF 회전 정보 적용
        try:
            from PIL import ImageOps
            img = ImageOps.exif_transpose(img)
        except:
            pass
        
        # RGB 변환 (RGBA, P 모드 처리)
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        # 리사이징
        if max(img.size) > max_size:
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        # JPEG로 압축
        output = BytesIO()
        img.save(output, format='JPEG', quality=85, optimize=True)
        return output.getvalue()
    
    except Exception as e:
        print(f"[VLM] ⚠️ Image compression failed: {e}")
        return image_bytes  # 실패시 원본 반환


def analyze_image_gpt4v(
    image_bytes: bytes,
    prompt: str,
    max_tokens: int = 500,
    detail: str = "high"
) -> Optional[str]:
    """
    GPT-4V를 사용한 이미지 분석
    
    Args:
        image_bytes: 이미지 바이트 데이터
        prompt: 분석 프롬프트
        max_tokens: 최대 응답 토큰 수
        detail: 이미지 해상도 ("low", "high", "auto")
    
    Returns:
        VLM 분석 결과 텍스트
    """
    if not OPENAI_AVAILABLE:
        print("[VLM] ❌ OpenAI not available")
        return None
    
    try:
        # 이미지 압축
        compressed_image = compress_image(image_bytes)
        
        # Base64 인코딩
        base64_image = base64.b64encode(compressed_image).decode('utf-8')
        
        # GPT-4V API 호출
        response = openai_client.chat.completions.create(
            model="gpt-4o",  # gpt-4o는 vision 기능 포함
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                                "detail": detail
                            }
                        }
                    ]
                }
            ],
            max_tokens=max_tokens,
            temperature=0.3  # 일관성 있는 응답을 위해 낮은 온도
        )
        
        result = response.choices[0].message.content
        print(f"[VLM] ✅ GPT-4V analysis complete: {len(result)} chars")
        return result
    
    except Exception as e:
        print(f"[VLM] ❌ GPT-4V error: {e}")
        return None


def analyze_place_image(
    image_bytes: bytes,
    nearby_places: Optional[List[Dict]] = None,
    language: str = "ko"
) -> Optional[str]:
    """
    장소 이미지 분석 (GPT-4V 전용)
    
    Args:
        image_bytes: 이미지 바이트 데이터
        nearby_places: 주변 장소 정보 리스트 (GPS 기반)
        language: 응답 언어 ("ko", "en")
    
    Returns:
        VLM 분석 결과 텍스트
    """
    
    # 프롬프트 생성
    prompt = build_place_analysis_prompt(nearby_places, language)
    
    # GPT-4V 사용 가능 여부 확인
    if not OPENAI_AVAILABLE:
        error_msg = "GPT-4V를 사용할 수 없습니다. OPENAI_API_KEY를 확인하세요." if language == "ko" else "GPT-4V unavailable. Check OPENAI_API_KEY."
        print(f"[VLM] ❌ {error_msg}")
        return None
    
    # GPT-4V로 이미지 분석
    result = analyze_image_gpt4v(image_bytes, prompt)
    
    if not result:
        error_msg = "이미지 분석에 실패했습니다." if language == "ko" else "Image analysis failed."
        print(f"[VLM] ❌ {error_msg}")
        return None
    
    return result


def build_place_analysis_prompt(
    nearby_places: Optional[List[Dict]] = None,
    language: str = "ko"
) -> str:
    """
    장소 분석용 프롬프트 생성
    
    Args:
        nearby_places: 주변 장소 정보 리스트
        language: 프롬프트 언어
    
    Returns:
        프롬프트 문자열
    """
    
    if language == "ko":
        prompt = """당신은 서울 관광 전문가입니다. 이미지를 분석하여 다음을 제공하세요:

**분석 요청사항:**
1. 이 장소가 무엇인지 정확히 식별
2. 건축 양식, 색상, 특징적인 요소 설명
3. 역사적/문화적 배경 (알려진 경우)
4. 이 장소의 대표적인 특징

**응답 형식:**
```
장소명: [구체적인 이름]
카테고리: [관광지/음식점/카페/공원/역사유적 등]
설명: [2-3문장으로 장소 설명]
특징: [시각적 특징과 특별한 점]
신뢰도: [high/medium/low]
```
"""
        
        if nearby_places:
            places_text = "\n".join([
                f"- {p.get('name', 'Unknown')} ({p.get('category', 'N/A')}) - {p.get('distance_km', 0):.2f}km"
                for p in nearby_places[:5]
            ])
            prompt += f"\n**참고: GPS 기반 주변 장소 (1km 이내):**\n{places_text}\n"
            prompt += "\n위 후보 중 이미지와 일치하는 장소가 있다면 우선 고려하세요."
    
    else:  # English
        prompt = """You are a Seoul tourism expert. Analyze this image and provide:

**Analysis Requirements:**
1. Identify the exact place/location
2. Describe architectural style, colors, distinctive features
3. Historical/cultural context (if known)
4. Key characteristics of this place

**Response Format:**
```
Place Name: [specific name]
Category: [tourist spot/restaurant/cafe/park/historic site, etc.]
Description: [2-3 sentences describing the place]
Features: [visual characteristics and special points]
Confidence: [high/medium/low]
```
"""
        
        if nearby_places:
            places_text = "\n".join([
                f"- {p.get('name', 'Unknown')} ({p.get('category', 'N/A')}) - {p.get('distance_km', 0):.2f}km"
                for p in nearby_places[:5]
            ])
            prompt += f"\n**Reference: Nearby places within 1km (GPS-based):**\n{places_text}\n"
            prompt += "\nIf the image matches any of these candidates, prioritize them."
    
    return prompt


def extract_place_info_from_vlm_response(vlm_response: str) -> Dict[str, str]:
    """
    VLM 응답에서 장소 정보 추출
    
    Args:
        vlm_response: VLM 분석 결과 텍스트
    
    Returns:
        추출된 정보 딕셔너리
    """
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
            
            # 장소명 추출
            if line.startswith(('장소명:', 'Place Name:')):
                info["place_name"] = line.split(':', 1)[1].strip()
            
            # 카테고리 추출
            elif line.startswith(('카테고리:', 'Category:')):
                info["category"] = line.split(':', 1)[1].strip()
            
            # 설명 추출
            elif line.startswith(('설명:', 'Description:')):
                info["description"] = line.split(':', 1)[1].strip()
            
            # 특징 추출
            elif line.startswith(('특징:', 'Features:')):
                info["features"] = line.split(':', 1)[1].strip()
            
            # 신뢰도 추출
            elif line.startswith(('신뢰도:', 'Confidence:')):
                confidence_text = line.split(':', 1)[1].strip().lower()
                if 'high' in confidence_text or '높' in confidence_text:
                    info["confidence"] = "high"
                elif 'medium' in confidence_text or '중' in confidence_text:
                    info["confidence"] = "medium"
                else:
                    info["confidence"] = "low"
    
    except Exception as e:
        print(f"[VLM] ⚠️ Failed to extract place info: {e}")
    
    return info


def calculate_confidence_score(
    vlm_info: Dict[str, str],
    vector_similarity: Optional[float] = None,
    gps_distance_km: Optional[float] = None
) -> float:
    """
    종합 신뢰도 점수 계산
    
    Args:
        vlm_info: VLM 추출 정보
        vector_similarity: 벡터 유사도 (0.0-1.0)
        gps_distance_km: GPS 거리 (km)
    
    Returns:
        신뢰도 점수 (0.0-1.0)
    """
    score = 0.0
    
    # VLM 신뢰도 (40%)
    confidence_map = {"high": 0.4, "medium": 0.25, "low": 0.1}
    score += confidence_map.get(vlm_info.get("confidence", "low"), 0.1)
    
    # 벡터 유사도 (40%)
    if vector_similarity is not None:
        score += vector_similarity * 0.4
    
    # GPS 거리 (20%)
    if gps_distance_km is not None:
        # 거리가 가까울수록 높은 점수 (1km 이내)
        gps_score = max(0, 1 - (gps_distance_km / 1.0))
        score += gps_score * 0.2
    
    return round(min(score, 1.0), 2)

