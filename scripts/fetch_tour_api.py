"""
한국관광공사 TourAPI 데이터 수집 스크립트
카테고리별 서울 주요 관광지 데이터 자동 수집
"""

import os
import sys
import requests
import time
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

# 프로젝트 루트 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.db import get_db


# TourAPI 설정
TOUR_API_KEY = os.getenv("TOUR_API_KEY")
BASE_URL = "http://apis.data.go.kr/B551011/KorService2"
AREA_CODE_SEOUL = "1"


# 카테고리 정의 (contentTypeId 기반)
CATEGORIES = {
    "관광지": {"content_type": "12", "count": 30},    # 관광지
    "문화시설": {"content_type": "14", "count": 30},  # 문화시설
    "축제공연": {"content_type": "15", "count": 20},  # 행사/공연/축제
    "레저스포츠": {"content_type": "28", "count": 20}, # 레포츠
    "쇼핑": {"content_type": "38", "count": 20},      # 쇼핑
    "음식점": {"content_type": "39", "count": 20}     # 음식점
}


def fetch_places_by_category(
    category_name: str,
    content_type: str,
    count: int = 20
) -> List[Dict]:
    """
    카테고리별 장소 데이터 수집
    
    Args:
        category_name: 카테고리명
        content_type: TourAPI contentTypeId (12=관광지, 14=문화시설, 등)
        count: 수집 개수
    
    Returns:
        장소 데이터 리스트
    """
    try:
        print(f"\n📍 Fetching {category_name} (contentTypeId={content_type}, count={count})...")
        
        if not TOUR_API_KEY:
            raise ValueError("TOUR_API_KEY not set in .env")
        
        # 파라미터 구성 (TourAPI 표준 형식)
        params = {
            "serviceKey": TOUR_API_KEY,
            "numOfRows": str(count * 2),
            "pageNo": "1",
            "MobileOS": "ETC",
            "MobileApp": "QuestOfSeoul",
            "areaCode": AREA_CODE_SEOUL,
            "contentTypeId": content_type,
            "arrange": "O",  # O=대표이미지있는콘텐츠우선+제목순 (KorService2 기준)
            "_type": "json"
        }
        
        url = f"{BASE_URL}/areaBasedList2"
        
        print(f"  Request URL: {url}")
        print(f"  Params: {params}")
        
        response = requests.get(url, params=params, timeout=30)
        
        # 응답 확인
        print(f"  Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"  Response text: {response.text[:500]}")
            response.raise_for_status()
        
        data = response.json()
        
        # 응답 파싱
        if "response" not in data or "body" not in data["response"]:
            print(f"❌ Invalid response format")
            return []
        
        body = data["response"]["body"]
        
        if "items" not in body or "item" not in body["items"]:
            print(f"⚠️  No items found")
            return []
        
        items = body["items"]["item"]
        
        # 리스트가 아닌 경우 처리
        if not isinstance(items, list):
            items = [items]
        
        # 필수 필드 있는 것만 필터링
        valid_places = []
        for item in items:
            if (item.get("title") and 
                item.get("mapy") and 
                item.get("mapx") and
                item.get("firstimage")):
                valid_places.append(item)
        
        # count 개수만큼만 반환
        places = valid_places[:count]
        
        print(f"✅ Fetched {len(places)} valid places")
        return places
    
    except Exception as e:
        print(f"❌ Error fetching {category_name}: {e}")
        import traceback
        traceback.print_exc()
        return []


def transform_tour_api_data(tour_data: Dict, category_name: str) -> Dict:
    """
    TourAPI 데이터를 Supabase places 스키마로 변환
    
    Args:
        tour_data: TourAPI 원본 데이터
        category_name: 카테고리명
    
    Returns:
        places 테이블 형식 딕셔너리
    """
    return {
        "name": tour_data.get("title", "").strip(),
        "name_en": tour_data.get("title", "").strip(),  # TourAPI에 영문명 없으면 한글로
        "description": tour_data.get("overview", "")[:500],  # 길이 제한
        "category": category_name,
        "address": tour_data.get("addr1", ""),
        "latitude": float(tour_data.get("mapy", 0)),
        "longitude": float(tour_data.get("mapx", 0)),
        "image_url": tour_data.get("firstimage", ""),
        "images": [tour_data.get("firstimage2")] if tour_data.get("firstimage2") else [],
        "metadata": {
            "tel": tour_data.get("tel", ""),
            "homepage": tour_data.get("homepage", ""),
            "content_type_id": tour_data.get("contenttypeid", ""),
            "content_id": tour_data.get("contentid", ""),
            "zipcode": tour_data.get("zipcode", ""),
            "mlevel": tour_data.get("mlevel", ""),
            "sigungucode": tour_data.get("sigungucode", "")
        },
        "source": "tour_api",
        "is_active": True,
        "view_count": 0
    }


def save_places_to_db(places: List[Dict]) -> int:
    """
    장소 데이터를 Supabase에 저장
    
    Args:
        places: 장소 데이터 리스트
    
    Returns:
        저장된 개수
    """
    try:
        db = get_db()
        
        if not places:
            print("⚠️  No places to save")
            return 0
        
        print(f"\n💾 Saving {len(places)} places to database...")
        
        # 배치 insert
        result = db.table("places").insert(places).execute()
        
        saved_count = len(result.data) if result.data else 0
        
        print(f"✅ Saved {saved_count} places")
        return saved_count
    
    except Exception as e:
        print(f"❌ Error saving to database: {e}")
        import traceback
        traceback.print_exc()
        return 0


def fetch_all_categories(dry_run: bool = False):
    """
    모든 카테고리의 장소 데이터 수집
    
    Args:
        dry_run: True면 저장하지 않고 출력만
    """
    print("=" * 60)
    print("🏛️  TourAPI Data Collection")
    print("=" * 60)
    print(f"\nCategories: {len(CATEGORIES)}")
    print(f"Target: {sum(c['count'] for c in CATEGORIES.values())} places")
    
    if dry_run:
        print("\n⚠️  DRY RUN MODE - No database writes")
    
    all_places = []
    success_count = 0
    fail_count = 0
    
    for category_name, category_info in CATEGORIES.items():
        print("\n" + "-" * 60)
        
        # API 요청
        raw_places = fetch_places_by_category(
            category_name=category_name,
            content_type=category_info["content_type"],
            count=category_info["count"]
        )
        
        if raw_places:
            # 데이터 변환
            transformed = [
                transform_tour_api_data(p, category_name)
                for p in raw_places
            ]
            
            all_places.extend(transformed)
            success_count += len(transformed)
            
            print(f"✅ {category_name}: {len(transformed)} places ready")
        else:
            fail_count += 1
            print(f"❌ {category_name}: Failed")
        
        # API rate limit 방지
        time.sleep(1)
    
    # 결과 출력
    print("\n" + "=" * 60)
    print("📊 Collection Summary")
    print("=" * 60)
    print(f"Total collected: {len(all_places)} places")
    print(f"Success: {success_count}")
    print(f"Failed: {fail_count}")
    
    if dry_run:
        print("\n📋 Sample data (first 3):")
        for place in all_places[:3]:
            print(f"\n  - {place['name']}")
            print(f"    Category: {place['category']}")
            print(f"    GPS: ({place['latitude']}, {place['longitude']})")
            print(f"    Image: {place['image_url'][:60]}...")
    else:
        # DB 저장
        if all_places:
            saved = save_places_to_db(all_places)
            print(f"\n✅ Saved to database: {saved}/{len(all_places)}")
            
            print("\n💡 Next steps:")
            print("  1. python seed_image_vectors.py --all")
            print("  2. python scripts/generate_quizzes_gpt.py")
        else:
            print("\n❌ No places to save")


def fetch_single_category(category_name: str):
    """특정 카테고리만 수집"""
    if category_name not in CATEGORIES:
        print(f"❌ Unknown category: {category_name}")
        print(f"Available: {list(CATEGORIES.keys())}")
        return
    
    category_info = CATEGORIES[category_name]
    
    raw_places = fetch_places_by_category(
        category_name=category_name,
        content_type=category_info["content_type"],
        count=category_info["count"]
    )
    
    if not raw_places:
        return
    
    transformed = [
        transform_tour_api_data(p, category_name)
        for p in raw_places
    ]
    
    saved = save_places_to_db(transformed)
    print(f"\n✅ {category_name}: {saved} places saved")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="TourAPI 데이터 수집")
    parser.add_argument("--all", action="store_true", help="모든 카테고리 수집")
    parser.add_argument("--category", type=str, help="특정 카테고리만 수집")
    parser.add_argument("--dry-run", action="store_true", help="테스트 모드 (저장 안함)")
    
    args = parser.parse_args()
    
    if args.all:
        fetch_all_categories(dry_run=args.dry_run)
    elif args.category:
        fetch_single_category(args.category)
    else:
        print("Usage:")
        print("  python scripts/fetch_tour_api.py --all")
        print("  python scripts/fetch_tour_api.py --all --dry-run")
        print("  python scripts/fetch_tour_api.py --category 역사유적")
        print("\nCategories:")
        for cat in CATEGORIES.keys():
            print(f"  - {cat}")
