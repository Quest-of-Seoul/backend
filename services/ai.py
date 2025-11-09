"""
AI service - Google Gemini LLM integration
"""

import google.generativeai as genai
import os
from typing import Optional

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Initialize model - using gemini-2.5-flash (latest stable model)
model = genai.GenerativeModel('gemini-2.5-flash')

def generate_docent_message(
    landmark: str,
    user_message: Optional[str] = None,
    language: str = "ko"
) -> str:
    """
    Generate AI docent response about a landmark

    Args:
        landmark: Name of the landmark
        user_message: Optional user question
        language: Response language (ko/en)

    Returns:
        AI-generated docent message
    """

    # Build prompt based on language
    if language == "ko":
        base_prompt = f"""
당신은 서울을 안내하는 친근한 AI 도슨트입니다.

랜드마크: {landmark}

다음 형식으로 응답해주세요:
1. 간단한 인사와 랜드마크 소개 (2-3문장)
2. 흥미로운 역사적 사실이나 재미있는 이야기 (2-3문장)
3. 방문 팁이나 추천 사항 (1-2문장)

친근하고 대화하는 듯한 톤으로 작성해주세요.
"""
        if user_message:
            base_prompt += f"\n\n사용자 질문: {user_message}\n위 질문에 대해서도 답변해주세요."
    else:  # English
        base_prompt = f"""
You are a friendly AI docent guiding visitors through Seoul.

Landmark: {landmark}

Please respond in this format:
1. Brief greeting and landmark introduction (2-3 sentences)
2. Interesting historical fact or fun story (2-3 sentences)
3. Visiting tips or recommendations (1-2 sentences)

Use a friendly, conversational tone.
"""
        if user_message:
            base_prompt += f"\n\nUser question: {user_message}\nPlease also answer this question."

    try:
        response = model.generate_content(base_prompt)
        return response.text
    except Exception as e:
        print(f"Error generating AI response: {e}")
        return "죄송합니다. 지금은 응답을 생성할 수 없습니다." if language == "ko" else "Sorry, I cannot generate a response right now."


def generate_quiz(landmark: str, language: str = "ko") -> dict:
    """
    Generate a quiz question about the landmark

    Args:
        landmark: Name of the landmark
        language: Quiz language (ko/en)

    Returns:
        Dict with question, options, and correct answer
    """

    prompt = f"""
Generate a multiple choice quiz question about {landmark} in Seoul.

Return ONLY a JSON object in this exact format (no markdown, no extra text):
{{
    "question": "quiz question here",
    "options": ["option A", "option B", "option C", "option D"],
    "correct_answer": 0
}}

Where correct_answer is the index (0-3) of the correct option.
Language: {"Korean" if language == "ko" else "English"}
"""

    try:
        response = model.generate_content(prompt)
        # Parse response as JSON
        import json
        # Remove markdown code blocks if present
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())
    except Exception as e:
        print(f"Error generating quiz: {e}")
        return {
            "question": "퀴즈를 생성할 수 없습니다." if language == "ko" else "Cannot generate quiz.",
            "options": ["A", "B", "C", "D"],
            "correct_answer": 0
        }
