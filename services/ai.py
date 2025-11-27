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
        theme = preferences.get("theme") or preferences.get("category") or "Seoul Travel"
        if isinstance(theme, dict):
            theme = theme.get("name", "Seoul Travel")
        
        districts = preferences.get("districts") or []
        if isinstance(districts, list) and districts:
            districts_str = ", ".join(districts)
        else:
            districts_str = "No restriction"
        
        prompt = f"""You are a Seoul travel expert. Recommend an optimal travel itinerary based on user preferences.

[User Preferences]
- Theme: {theme}
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
