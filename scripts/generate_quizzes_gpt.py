"""
ChatGPT 기반 퀴즈 자동 생성 스크립트
장소 정보를 바탕으로 객관식 퀴즈 + 힌트를 자동 생성
"""

import os
import sys
import json
import time
from typing import List, Dict, Optional
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.db import get_db


# OpenAI 클라이언트
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# 퀴즈 생성 프롬프트
QUIZ_GENERATION_PROMPT = """
다음 서울 관광지 정보를 바탕으로 객관식 퀴즈를 생성하세요.

장소 정보:
- 이름: {name}
- 카테고리: {category}
- 설명: {description}
- 주소: {address}

요구사항:
1. 난이도: 쉬움 (일반 관광객이 알 수 있는 수준)
2. 형식: 4지선다 객관식
3. 정답: 1개
4. 힌트: 간접적으로 정답을 유도하는 힌트 문장
5. 설명: 정답에 대한 간단한 설명

퀴즈 주제 예시:
- 역사적 배경
- 건축 양식
- 대표 특징
- 위치/접근성
- 문화적 의미

응답 형식 (JSON만):
{{
  "question": "질문 문장 (명확하고 간결하게)",
  "options": ["선택지1", "선택지2", "선택지3 (정답)", "선택지4"],
  "correct_answer": 2,
  "hint": "힌트 문장 (정답을 직접 말하지 않음)",
  "explanation": "정답에 대한 설명 (1-2문장)"
}}

중요: 정답은 options 배열의 인덱스 (0부터 시작)
"""


def generate_quiz_with_gpt(
    place: Dict,
    model: str = "gpt-4o-mini"
) -> Optional[Dict]:
    """
    ChatGPT로 퀴즈 생성
    
    Args:
        place: 장소 정보 딕셔너리
        model: OpenAI 모델명
    
    Returns:
        생성된 퀴즈 데이터
    """
    try:
        prompt = QUIZ_GENERATION_PROMPT.format(
            name=place.get("name", ""),
            category=place.get("category", ""),
            description=place.get("description", "")[:300],  # 길이 제한
            address=place.get("address", "")
        )
        
        print(f"  🤖 Generating quiz for: {place.get('name')}")
        
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.7,
            max_tokens=500
        )
        
        quiz_data = json.loads(response.choices[0].message.content)
        
        # 검증
        required_keys = ["question", "options", "correct_answer", "hint", "explanation"]
        if not all(k in quiz_data for k in required_keys):
            print(f"  ⚠️  Invalid quiz format")
            return None
        
        if len(quiz_data["options"]) != 4:
            print(f"  ⚠️  Options must be 4, got {len(quiz_data['options'])}")
            return None
        
        if not (0 <= quiz_data["correct_answer"] < 4):
            print(f"  ⚠️  Invalid correct_answer: {quiz_data['correct_answer']}")
            return None
        
        print(f"  ✅ Quiz generated")
        return quiz_data
    
    except Exception as e:
        print(f"  ❌ Error generating quiz: {e}")
        return None


def save_quest_to_db(place_id: str, place_name: str, category: str, latitude: float, longitude: float) -> Optional[str]:
    """
    퀘스트 생성 (quest 테이블)
    
    Args:
        place_id: 장소 UUID
        place_name: 장소 이름
        category: 카테고리
        latitude: 위도
        longitude: 경도
    
    Returns:
        생성된 quest_id
    """
    try:
        db = get_db()
        
        quest_data = {
            "place_id": place_id,
            "name": place_name,  # 필수 필드
            "title": f"{category} 퀘스트",
            "description": "장소를 방문하고 퀴즈를 풀어보세요",
            "lat": latitude,  # 필수 필드
            "lon": longitude,  # 필수 필드
            "category": category,
            "difficulty": "easy",
            "points": 10,
            "is_active": True
        }
        
        result = db.table("quests").insert(quest_data).execute()
        
        if result.data and len(result.data) > 0:
            quest_id = result.data[0].get("id")
            return quest_id
        
        return None
    
    except Exception as e:
        print(f"  ❌ Error saving quest: {e}")
        return None


def save_quiz_to_db(quest_id: str, quiz_data: Dict) -> bool:
    """
    퀴즈 저장 (quest_quizzes 테이블)
    
    Args:
        quest_id: 퀘스트 UUID
        quiz_data: 퀴즈 데이터
    
    Returns:
        성공 여부
    """
    try:
        db = get_db()
        
        quiz_record = {
            "quest_id": quest_id,
            "question": quiz_data["question"],
            "options": quiz_data["options"],
            "correct_answer": quiz_data["correct_answer"],
            "hint": quiz_data["hint"],
            "explanation": quiz_data.get("explanation", ""),
            "difficulty": "easy"
        }
        
        result = db.table("quest_quizzes").insert(quiz_record).execute()
        
        return result.data is not None and len(result.data) > 0
    
    except Exception as e:
        print(f"  ❌ Error saving quiz: {e}")
        return False


def generate_quizzes_for_all_places(limit: Optional[int] = None, dry_run: bool = False):
    """
    모든 장소에 대해 퀴즈 생성
    
    Args:
        limit: 처리할 최대 개수 (None이면 전체)
        dry_run: True면 저장하지 않고 출력만
    """
    print("=" * 60)
    print("🎯 Quiz Generation with ChatGPT")
    print("=" * 60)
    
    if dry_run:
        print("⚠️  DRY RUN MODE")
    
    try:
        # TourAPI에서 가져온 장소만 (source='tour_api')
        db = get_db()
        query = db.table("places").select("*").eq("source", "tour_api").eq("is_active", True)
        
        if limit:
            query = query.limit(limit)
        
        result = query.execute()
        places = result.data
        
        print(f"\n📊 Found {len(places)} places from TourAPI")
        
        if not places:
            print("⚠️  No places found. Run fetch_tour_api.py first!")
            return
        
        success_count = 0
        fail_count = 0
        
        for idx, place in enumerate(places, 1):
            print(f"\n[{idx}/{len(places)}] {place['name']}")
            
            # 이미 퀘스트가 있는지 확인
            existing_quest = db.table("quests").select("id").eq("place_id", place["id"]).execute()
            
            if existing_quest.data:
                print(f"  ⚠️  Quest already exists, skipping")
                continue
            
            # 퀴즈 생성
            quiz_data = generate_quiz_with_gpt(place)
            
            if not quiz_data:
                fail_count += 1
                continue
            
            if dry_run:
                print(f"  📝 Quiz preview:")
                print(f"     Q: {quiz_data['question']}")
                print(f"     Hint: {quiz_data['hint']}")
                success_count += 1
                continue
            
            # DB 저장
            quest_id = save_quest_to_db(
                place["id"], 
                place["name"], 
                place["category"],
                place["latitude"],
                place["longitude"]
            )
            
            if not quest_id:
                fail_count += 1
                continue
            
            quiz_saved = save_quiz_to_db(quest_id, quiz_data)
            
            if quiz_saved:
                success_count += 1
                print(f"  ✅ Quest + Quiz saved")
            else:
                fail_count += 1
            
            # API rate limit
            time.sleep(0.5)
        
        # 결과
        print("\n" + "=" * 60)
        print("🎉 Generation Complete")
        print("=" * 60)
        print(f"✅ Success: {success_count}")
        print(f"❌ Failed: {fail_count}")
        print("=" * 60)
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


def generate_sql_file():
    """
    생성된 퀘스트/퀴즈를 SQL 파일로 내보내기 (백업용)
    """
    try:
        db = get_db()
        
        print("📝 Exporting to SQL file...")
        
        # 모든 퀘스트 조회
        quests = db.table("quests").select("*").execute()
        
        sql_lines = ["-- Quest of Seoul - Auto-generated Quizzes\n"]
        
        for quest in quests.data:
            quest_id = quest['id']
            
            # 퀴즈 조회
            quizzes = db.table("quest_quizzes").select("*").eq("quest_id", quest_id).execute()
            
            for quiz in quizzes.data:
                options_str = "{" + ",".join([f'"{opt}"' for opt in quiz['options']]) + "}"
                
                sql = f"""
INSERT INTO quest_quizzes (quest_id, question, options, correct_answer, hint, explanation, difficulty)
VALUES (
    '{quest_id}',
    '{quiz['question'].replace("'", "''")}',
    ARRAY{options_str},
    {quiz['correct_answer']},
    '{quiz['hint'].replace("'", "''")}',
    '{quiz.get('explanation', '').replace("'", "''")}',
    'easy'
);
"""
                sql_lines.append(sql)
        
        # 파일 저장
        output_path = "sql/generated_quizzes.sql"
        with open(output_path, "w", encoding="utf-8") as f:
            f.writelines(sql_lines)
        
        print(f"✅ SQL exported: {output_path}")
    
    except Exception as e:
        print(f"❌ Export failed: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="ChatGPT 퀴즈 자동 생성")
    parser.add_argument("--all", action="store_true", help="모든 장소에 대해 생성")
    parser.add_argument("--limit", type=int, help="처리 개수 제한")
    parser.add_argument("--dry-run", action="store_true", help="테스트 모드")
    parser.add_argument("--export-sql", action="store_true", help="SQL 파일로 내보내기")
    
    args = parser.parse_args()
    
    if args.export_sql:
        generate_sql_file()
    elif args.all:
        generate_quizzes_for_all_places(
            limit=args.limit,
            dry_run=args.dry_run
        )
    else:
        print("Usage:")
        print("  python scripts/generate_quizzes_gpt.py --all")
        print("  python scripts/generate_quizzes_gpt.py --all --limit 10")
        print("  python scripts/generate_quizzes_gpt.py --all --dry-run")
        print("  python scripts/generate_quizzes_gpt.py --export-sql")
