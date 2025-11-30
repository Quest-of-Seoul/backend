"""AI Service - Google Gemini"""

import google.generativeai as genai
import os
import logging
import json
from typing import Optional, List, Dict, Set

logger = logging.getLogger(__name__)

api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')
    GEMINI_AVAILABLE = True
else:
    logger.warning("GOOGLE_API_KEY or GEMINI_API_KEY not set")
    model = None
    GEMINI_AVAILABLE = False

def generate_docent_message(
    landmark: str,
    user_message: Optional[str] = None,
    language: str = "en"
) -> str:
    """Generate AI docent response"""
    
    base_prompt = f"""You are a friendly AI docent for '{landmark}'.

{f'Question: {user_message}' if user_message else 'Please introduce this place.'}

Provide an engaging response in 3-4 sentences."""

    try:
        response = model.generate_content(base_prompt)
        return response.text
    except Exception as e:
        logger.error(f"Gemini error: {e}", exc_info=True)
        return "Cannot generate response."


def generate_quiz(landmark: str, language: str = "en") -> dict:
    """Generate quiz about landmark"""
    
    prompt = f"""Create a quiz about {landmark}.

Return in JSON format:
{{
    "question": "Quiz question",
    "options": ["Option 1", "Option 2", "Option 3", "Option 4"],
    "correct_answer": 0,
    "explanation": "Explanation"
}}"""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        
        return json.loads(text.strip())
    except Exception as e:
        logger.error(f"Quiz generation error: {e}", exc_info=True)
        return {
            "question": "Cannot generate quiz.",
            "options": ["A", "B", "C", "D"],
            "correct_answer": 0
        }


def generate_quest_quizzes(
    place_name: str,
    place_description: Optional[str] = None,
    place_category: Optional[str] = None,
    language: str = "ko",
    count: int = 5
) -> List[Dict]:
    """
    Generate multiple quizzes (default 5) for a quest place
    
    Args:
        place_name: 장소 이름
        place_description: 장소 설명 (선택)
        place_category: 장소 카테고리 (선택)
        language: 언어 (기본값: "ko")
        count: 생성할 퀴즈 개수 (기본값: 5)
    
    Returns:
        퀴즈 리스트 (각 퀴즈는 question, options, correct_answer, hint, explanation, difficulty 포함)
    """
    if not GEMINI_AVAILABLE:
        logger.warning("Gemini not available, cannot generate quizzes")
        return []
    
    try:
        description_text = f"\nDescription: {place_description}" if place_description else ""
        category_text = f"\nCategory: {place_category}" if place_category else ""
        
        prompt = f"""Create exactly {count} diverse quiz questions about the place "{place_name}".{description_text}{category_text}

Requirements:
1. Each quiz should have different difficulty levels (easy, medium, hard)
2. Questions should cover various aspects: history, architecture, significance, location, features, etc.
3. Each question must have exactly 4 options
4. correct_answer should be 0, 1, 2, or 3 (index of correct option)
5. Include helpful hints and explanations
6. Use {language} language

Return in JSON format:
{{
    "quizzes": [
        {{
            "question": "Question text",
            "options": ["Option 1", "Option 2", "Option 3", "Option 4"],
            "correct_answer": 0,
            "hint": "Helpful hint",
            "explanation": "Detailed explanation",
            "difficulty": "easy" // or "medium" or "hard"
        }}
    ]
}}"""

        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # Extract JSON
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        
        result = json.loads(text.strip())
        quizzes = result.get("quizzes", [])
        
        # Validate and normalize quizzes
        validated_quizzes = []
        for quiz in quizzes[:count]:  # Limit to requested count
            if not isinstance(quiz.get("options"), list) or len(quiz.get("options", [])) != 4:
                continue
            if quiz.get("correct_answer") not in [0, 1, 2, 3]:
                continue
            
            validated_quizzes.append({
                "question": quiz.get("question", ""),
                "options": quiz.get("options", []),
                "correct_answer": quiz.get("correct_answer", 0),
                "hint": quiz.get("hint", ""),
                "explanation": quiz.get("explanation", ""),
                "difficulty": quiz.get("difficulty", "easy")
            })
        
        logger.info(f"Generated {len(validated_quizzes)} quizzes for {place_name}")
        return validated_quizzes
    
    except Exception as e:
        logger.error(f"Error generating quest quizzes: {e}", exc_info=True)
        return []


def generate_route_recommendation(
    candidate_quests: list,
    preferences: dict,
    completed_quest_ids: set,
    language: str = "en"
) -> list:
    """AI-based travel itinerary recommendation"""
    if not GEMINI_AVAILABLE:
        logger.warning("Gemini not available, using fallback")
        return []
    
    try:
        # Organize candidate quest information
        quest_info_list = []
        for quest in candidate_quests[:20]:  # Only top 20 passed to AI
            quest_info = {
                "id": quest.get("id"),
                "name": quest.get("name", ""),
                "category": quest.get("category", ""),
                "district": quest.get("district", ""),
                "latitude": quest.get("latitude"),
                "longitude": quest.get("longitude"),
                "reward_point": quest.get("reward_point", 100),
                "completion_count": quest.get("completion_count", 0),
                "description": quest.get("description", "")[:200]
            }
            quest_info_list.append(quest_info)
        
        # Organize preference information
        # theme 처리 (다중 선택 지원)
        theme = preferences.get("theme") or preferences.get("category") or "Seoul Travel"
        if isinstance(theme, list):
            # 리스트인 경우: ["Culture", "History", "Food"] 등
            theme_list = []
            for t in theme:
                if isinstance(t, dict):
                    theme_list.append(t.get("name", ""))
                elif isinstance(t, str):
                    theme_list.append(t)
            theme_str = ", ".join([t for t in theme_list if t]) or "Seoul Travel"
        elif isinstance(theme, dict):
            theme_str = theme.get("name", "Seoul Travel")
        elif isinstance(theme, str):
            theme_str = theme
        else:
            theme_str = "Seoul Travel"
        
        districts = preferences.get("districts") or []
        if isinstance(districts, list) and districts:
            districts_str = ", ".join(districts)
        else:
            districts_str = "No restriction"
        
        prompt = f"""You are a Seoul travel expert. Recommend an optimal travel itinerary based on user preferences.

[User Preferences]
- Theme: {theme_str}
- Preferred Districts: {districts_str}
- Completed Quests: {len(completed_quest_ids)}

[Candidate Quests]
{json.dumps(quest_info_list, ensure_ascii=False, indent=2)}

[Requirements]
1. Select exactly 4 quests
2. Exclude completed quests (IDs: {list(completed_quest_ids)[:10]})
3. Consider theme and preferred districts
4. Arrange in efficient order considering travel distance and time
5. Consider category diversity

Return in JSON format:
{{
    "selected_quest_ids": [quest ID array, 4 items],
    "reasoning": "Selection reasoning",
    "route_order": "Visit order explanation"
}}"""
        
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # Extract JSON
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        
        result = json.loads(text.strip())
        selected_ids = result.get("selected_quest_ids", [])
        
        # Return selected quests
        selected_quests = []
        quest_dict = {q.get("id"): q for q in candidate_quests}
        
        for quest_id in selected_ids:
            if quest_id in quest_dict:
                selected_quests.append(quest_dict[quest_id])
        
        logger.info(f"AI recommended {len(selected_quests)} quests: {result.get('reasoning', '')[:100]}")
        return selected_quests
    
    except Exception as e:
        logger.error(f"AI route recommendation error: {e}", exc_info=True)
        return []
