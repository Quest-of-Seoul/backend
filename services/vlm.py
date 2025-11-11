"""VLM Service - GPT-4V Image Analysis"""

import os
import base64
import logging
from typing import Optional, Dict
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
    """Analyze image using GPT-4V"""
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
    language: str = "ko"
) -> Optional[str]:
    """Analyze place image"""
    
    if language == "ko":
        prompt = """이 이미지에 보이는 장소를 분석해주세요.

다음 정보를 포함해주세요:
1. 장소 이름 (한글과 영문)
2. 장소 유형 (예: 궁궐, 사찰, 타워, 광장 등)
3. 주요 특징과 건축 양식
4. 역사적/문화적 의미

간결하고 정확하게 설명해주세요."""
    else:
        prompt = """Analyze the place shown in this image.

Include:
1. Place name (in English and Korean if applicable)
2. Type (e.g., palace, temple, tower, square)
3. Key features and architectural style
4. Historical/cultural significance

Be concise and accurate."""
    
    return analyze_image_gpt4v(image_bytes, prompt, max_tokens=500)
