"""
수동 장소 데이터 import 스크립트
TourAPI 대신 JSON/CSV 파일에서 장소 데이터 로드
"""

import os
import sys
import json
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.db import get_db


# 서울 주요 관광지 데이터 (샘플)
SEOUL_PLACES = [
    # 역사유적 (20개)
    {
        "name": "경복궁",
        "name_en": "Gyeongbokgung Palace",
        "description": "조선시대 대표 궁궐로, 1395년에 창건되었습니다. 근정전, 경회루 등 아름다운 전통 건축물을 감상할 수 있습니다.",
        "category": "역사유적",
        "address": "서울특별시 종로구 사직로 161",
        "latitude": 37.579617,
        "longitude": 126.977041,
        "image_url": "https://korean.visitkorea.or.kr/uploadImgs/thumb/big/detail_76509_b.jpg",
        "metadata": {"opening_hours": "09:00-18:00", "admission_fee": "3000원"}
    },
    {
        "name": "창덕궁",
        "name_en": "Changdeokgung Palace",
        "description": "1405년 창건된 조선 궁궐로 유네스코 세계문화유산입니다.",
        "category": "역사유적",
        "address": "서울특별시 종로구 율곡로 99",
        "latitude": 37.579231,
        "longitude": 126.991090,
        "image_url": "https://korean.visitkorea.or.kr/uploadImgs/thumb/big/detail_76540_b.jpg",
        "metadata": {"opening_hours": "09:00-18:00", "admission_fee": "3000원"}
    },
    {
        "name": "덕수궁",
        "name_en": "Deoksugung Palace",
        "description": "서양식 건축물이 있는 독특한 조선 궁궐입니다.",
        "category": "역사유적",
        "address": "서울특별시 중구 세종대로 99",
        "latitude": 37.565891,
        "longitude": 126.975025,
        "image_url": "https://korean.visitkorea.or.kr/uploadImgs/thumb/big/detail_76517_b.jpg",
        "metadata": {"opening_hours": "09:00-21:00", "admission_fee": "1000원"}
    },
    
    # 문화시설 (5개 예시)
    {
        "name": "국립중앙박물관",
        "name_en": "National Museum of Korea",
        "description": "한국의 대표 박물관으로 다양한 문화재를 소장하고 있습니다.",
        "category": "문화시설",
        "address": "서울특별시 용산구 서빙고로 137",
        "latitude": 37.523918,
        "longitude": 126.980241,
        "image_url": "https://korean.visitkorea.or.kr/uploadImgs/thumb/big/detail_128339_b.jpg",
        "metadata": {"opening_hours": "10:00-18:00", "admission_fee": "무료"}
    },
    {
        "name": "국립고궁박물관",
        "name_en": "National Palace Museum",
        "description": "조선 왕실의 문화유산을 전시하는 박물관입니다.",
        "category": "문화시설",
        "address": "서울특별시 종로구 효자로 12",
        "latitude": 37.575823,
        "longitude": 126.975372,
        "image_url": "https://korean.visitkorea.or.kr/uploadImgs/thumb/big/detail_128373_b.jpg",
        "metadata": {"opening_hours": "10:00-18:00", "admission_fee": "무료"}
    },
    
    # 자연/공원 (5개 예시)
    {
        "name": "남산공원",
        "name_en": "Namsan Park",
        "description": "서울 중심부의 대표 도심 공원입니다.",
        "category": "자연관광",
        "address": "서울특별시 중구 삼일대로 231",
        "latitude": 37.550901,
        "longitude": 126.990921,
        "image_url": "https://korean.visitkorea.or.kr/uploadImgs/thumb/big/detail_264877_b.jpg",
        "metadata": {"opening_hours": "24시간", "admission_fee": "무료"}
    },
    {
        "name": "한강공원",
        "name_en": "Hangang Park",
        "description": "한강변을 따라 조성된 시민 공원입니다.",
        "category": "자연관광",
        "address": "서울특별시 영등포구 여의동로 330",
        "latitude": 37.529223,
        "longitude": 126.932913,
        "image_url": "https://korean.visitkorea.or.kr/uploadImgs/thumb/big/detail_128437_b.jpg",
        "metadata": {"opening_hours": "24시간", "admission_fee": "무료"}
    },
    
    # 쇼핑 (5개 예시)
    {
        "name": "명동",
        "name_en": "Myeongdong",
        "description": "서울의 대표 쇼핑 거리입니다.",
        "category": "쇼핑",
        "address": "서울특별시 중구 명동길",
        "latitude": 37.563692,
        "longitude": 126.986072,
        "image_url": "https://korean.visitkorea.or.kr/uploadImgs/thumb/big/detail_264869_b.jpg",
        "metadata": {"opening_hours": "10:00-22:00"}
    },
    {
        "name": "동대문시장",
        "name_en": "Dongdaemun Market",
        "description": "24시간 운영되는 패션 쇼핑몰 단지입니다.",
        "category": "쇼핑",
        "address": "서울특별시 중구 을지로 281",
        "latitude": 37.566419,
        "longitude": 127.007981,
        "image_url": "https://korean.visitkorea.or.kr/uploadImgs/thumb/big/detail_264841_b.jpg",
        "metadata": {"opening_hours": "24시간"}
    },
]


def load_places_from_json(json_file: str) -> List[Dict]:
    """
    JSON 파일에서 장소 데이터 로드
    
    Args:
        json_file: JSON 파일 경로
    
    Returns:
        장소 데이터 리스트
    """
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"✅ Loaded {len(data)} places from {json_file}")
        return data
    
    except Exception as e:
        print(f"❌ Error loading JSON: {e}")
        return []


def save_places_to_db(places: List[Dict]) -> int:
    """
    장소 데이터를 Supabase에 저장
    """
    try:
        db = get_db()
        
        if not places:
            return 0
        
        print(f"\n💾 Saving {len(places)} places...")
        
        # 데이터 변환
        transformed = []
        for place in places:
            transformed.append({
                "name": place["name"],
                "name_en": place.get("name_en"),
                "description": place.get("description", ""),
                "category": place["category"],
                "address": place.get("address", ""),
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "image_url": place.get("image_url", ""),
                "metadata": place.get("metadata", {}),
                "source": "manual",
                "is_active": True
            })
        
        result = db.table("places").insert(transformed).execute()
        
        saved = len(result.data) if result.data else 0
        print(f"✅ Saved {saved} places")
        
        return saved
    
    except Exception as e:
        print(f"❌ Error saving: {e}")
        import traceback
        traceback.print_exc()
        return 0


def import_sample_data():
    """샘플 데이터 import"""
    print("=" * 60)
    print("📍 Manual Places Import")
    print("=" * 60)
    
    saved = save_places_to_db(SEOUL_PLACES)
    
    print("\n" + "=" * 60)
    print(f"✅ Complete: {saved} places")
    print("=" * 60)
    print("\n💡 Next steps:")
    print("  1. python seed_image_vectors.py --all")
    print("  2. python scripts/generate_quizzes_gpt.py --all")


def export_template():
    """
    places.json 템플릿 생성
    """
    template = [
        {
            "name": "장소명",
            "name_en": "Place Name",
            "description": "장소 설명",
            "category": "역사유적",
            "address": "서울특별시 종로구...",
            "latitude": 37.5796,
            "longitude": 126.9770,
            "image_url": "https://...",
            "metadata": {
                "opening_hours": "09:00-18:00",
                "admission_fee": "3000원"
            }
        }
    ]
    
    with open("data/places_template.json", "w", encoding="utf-8") as f:
        json.dump(template, f, ensure_ascii=False, indent=2)
    
    print("✅ Template created: data/places_template.json")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="수동 장소 데이터 import")
    parser.add_argument("--sample", action="store_true", help="샘플 데이터 import")
    parser.add_argument("--json", type=str, help="JSON 파일에서 import")
    parser.add_argument("--template", action="store_true", help="템플릿 생성")
    
    args = parser.parse_args()
    
    if args.sample:
        import_sample_data()
    elif args.json:
        places = load_places_from_json(args.json)
        if places:
            save_places_to_db(places)
    elif args.template:
        os.makedirs("data", exist_ok=True)
        export_template()
    else:
        print("Usage:")
        print("  python scripts/import_manual_places.py --sample")
        print("  python scripts/import_manual_places.py --json data/places.json")
        print("  python scripts/import_manual_places.py --template")
