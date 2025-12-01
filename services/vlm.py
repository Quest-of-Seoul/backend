"""VLM Service"""

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
    language: str = "en",
    quest_context: Optional[Dict] = None
) -> Optional[str]:
    prompt = build_place_analysis_prompt(nearby_places, language, quest_context)
    
    if not OPENAI_AVAILABLE:
        logger.error("GPT-4V unavailable.")
        return None
    
    result = analyze_image_gpt4v(image_bytes, prompt)
    
    if not result:
        logger.error("Image analysis failed.")
        return None
    
    return result


def build_place_analysis_prompt(
    nearby_places: Optional[List[Dict]] = None,
    language: str = "en",
    quest_context: Optional[Dict] = None
) -> str:    
    if quest_context:
        from services.quest_rag import generate_quest_rag_text
        
        quest_place = quest_context.get("place", {})
        quest_name = quest_context.get("name") or quest_context.get("title", "")
        place_name = quest_place.get("name", "") if quest_place else ""
        quest_location = place_name or quest_name
        
        quest_rag_text = generate_quest_rag_text(quest_context, quest_place)
        
        prompt = f"""You are a Seoul tourism expert. 

[IMPORTANT CONTEXT]
This image was taken INSIDE or AT the quest location: "{quest_location}"
The user is asking about something WITHIN this quest location (e.g., a specific feature, object, facility, or element inside the place).

[Quest Location Information]
{quest_rag_text}

[Your Task]
Analyze this image with the understanding that:
1. The image shows something INSIDE or AT "{quest_location}"
2. It could be a specific element, feature, object, facility, or detail within this quest location
3. Examples: a lock on a fence (if quest is Namsan Tower), a specific building detail, a statue, a sign, a specific area within the place, etc.
4. Identify what specific element/feature/object is shown in the image
5. Describe how it relates to the quest location "{quest_location}"
6. Provide historical/cultural context if relevant

Response Format:
Place Name: [the quest location name: {quest_location}]
Specific Element: [what specific element/feature/object is shown in the image, e.g., "Love Locks", "Observation Deck", "Specific Statue", etc.]
Category: [tourist spot/restaurant/cafe/park/historic site/feature within location, etc.]
Description: [2-3 sentences describing the specific element and its relationship to the quest location]
Features: [visual characteristics and special points of the element]
Confidence: [high/medium/low]"""
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
    score = 0.0
    
    confidence_map = {"high": 0.4, "medium": 0.25, "low": 0.1}
    score += confidence_map.get(vlm_info.get("confidence", "low"), 0.1)
    
    if vector_similarity is not None:
        score += vector_similarity * 0.4
    
    if gps_distance_km is not None:
        gps_score = max(0, 1 - (gps_distance_km / 1.0))
        score += gps_score * 0.2
    
    return round(min(score, 1.0), 2)
