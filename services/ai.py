"""AI Service - Google Gemini"""

import google.generativeai as genai
import os
import logging
import json
from typing import Optional

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
    language: str = "ko"
) -> str:
    """Generate AI docent response"""
    
    if language == "ko":
        base_prompt = f"""당신은 '{landmark}'에 대한 친절한 AI 도슨트입니다.

{f'질문: {user_message}' if user_message else '이 장소를 소개해주세요.'}

친근하고 흥미롭게 3-4문장으로 답변해주세요."""
    else:
        base_prompt = f"""You are a friendly AI docent for '{landmark}'.

{f'Question: {user_message}' if user_message else 'Please introduce this place.'}

Provide an engaging response in 3-4 sentences."""

    try:
        response = model.generate_content(base_prompt)
        return response.text
    except Exception as e:
        logger.error(f"Gemini error: {e}", exc_info=True)
        return "응답을 생성할 수 없습니다." if language == "ko" else "Cannot generate response."


def generate_quiz(landmark: str, language: str = "ko") -> dict:
    """Generate quiz about landmark"""
    
    if language == "ko":
        prompt = f"""{landmark}에 대한 퀴즈를 만들어주세요.

다음 JSON 형식으로 반환:
{{
    "question": "퀴즈 질문",
    "options": ["선택지1", "선택지2", "선택지3", "선택지4"],
    "correct_answer": 0,
    "explanation": "정답 설명"
}}"""
    else:
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
            "question": "퀴즈를 생성할 수 없습니다." if language == "ko" else "Cannot generate quiz.",
            "options": ["A", "B", "C", "D"],
            "correct_answer": 0
        }
