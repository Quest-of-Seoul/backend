"""
이미지 임베딩 배치 생성 스크립트
Supabase DB의 places 테이블에서 이미지를 가져와 임베딩 생성 후 image_vectors 테이블에 저장
"""

import os
import sys
from dotenv import load_dotenv
import requests
from io import BytesIO
from typing import List, Dict

# 환경 변수 로드
load_dotenv()

# 서비스 import
from services.db import get_db, save_image_vector
from services.embedding import generate_image_embedding, hash_image


def download_image(url: str) -> bytes:
    """
    URL에서 이미지 다운로드
    
    Args:
        url: 이미지 URL
    
    Returns:
        이미지 바이트 데이터
    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.content
    except Exception as e:
        print(f"❌ Failed to download {url}: {e}")
        return None


def process_place_images(place: Dict, batch_mode: bool = False):
    """
    장소의 이미지들을 처리하여 임베딩 생성
    
    Args:
        place: 장소 정보 딕셔너리
        batch_mode: 배치 모드 여부
    """
    place_id = place.get("id")
    place_name = place.get("name")
    image_url = place.get("image_url")
    
    print(f"\n📍 Processing: {place_name} ({place_id})")
    
    if not image_url:
        print("⚠️ No image URL, skipping...")
        return
    
    # 이미지 다운로드
    print(f"📥 Downloading image: {image_url}")
    image_bytes = download_image(image_url)
    
    if not image_bytes:
        return
    
    print(f"✅ Downloaded {len(image_bytes)} bytes")
    
    # 이미지 해시 생성
    img_hash = hash_image(image_bytes)
    print(f"🔑 Hash: {img_hash[:16]}...")
    
    # 임베딩 생성
    print(f"🧠 Generating embedding...")
    embedding = generate_image_embedding(image_bytes)
    
    if not embedding:
        print("❌ Embedding generation failed")
        return
    
    print(f"✅ Embedding generated: {len(embedding)} dimensions")
    
    # DB 저장
    print(f"💾 Saving to database...")
    vector_id = save_image_vector(
        place_id=place_id,
        image_url=image_url,
        embedding=embedding,
        image_hash=img_hash,
        source="dataset",
        metadata={
            "place_name": place_name,
            "category": place.get("category")
        }
    )
    
    if vector_id:
        print(f"✅ Saved with ID: {vector_id}")
    else:
        print(f"❌ Failed to save to database")


def seed_all_places():
    """
    모든 장소의 이미지 임베딩 생성
    """
    print("=" * 60)
    print("🚀 Starting image embedding batch process")
    print("=" * 60)
    
    try:
        # Supabase에서 모든 장소 조회
        db = get_db()
        result = db.table("places").select("*").eq("is_active", True).execute()
        
        places = result.data
        total = len(places)
        
        print(f"\n📊 Found {total} active places")
        
        if total == 0:
            print("⚠️ No places found. Run seed_database.py first!")
            return
        
        # 각 장소 처리
        success_count = 0
        fail_count = 0
        
        for idx, place in enumerate(places, 1):
            print(f"\n{'='*60}")
            print(f"Progress: {idx}/{total}")
            
            try:
                process_place_images(place)
                success_count += 1
            except Exception as e:
                print(f"❌ Error processing place: {e}")
                fail_count += 1
                continue
        
        # 결과 출력
        print("\n" + "=" * 60)
        print("🎉 Batch process complete!")
        print("=" * 60)
        print(f"✅ Success: {success_count}/{total}")
        print(f"❌ Failed: {fail_count}/{total}")
        print("=" * 60)
    
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()


def seed_specific_place(place_name: str):
    """
    특정 장소만 처리
    
    Args:
        place_name: 장소명
    """
    try:
        db = get_db()
        result = db.table("places").select("*").ilike("name", f"%{place_name}%").limit(1).execute()
        
        if not result.data:
            print(f"❌ Place not found: {place_name}")
            return
        
        place = result.data[0]
        process_place_images(place)
    
    except Exception as e:
        print(f"❌ Error: {e}")


def check_embedding_status():
    """
    임베딩 생성 상태 확인
    """
    try:
        db = get_db()
        
        # 전체 장소 수
        places_result = db.table("places").select("id", count="exact").execute()
        total_places = places_result.count
        
        # 임베딩이 있는 장소 수
        vectors_result = db.table("image_vectors").select("place_id", count="exact").execute()
        total_vectors = vectors_result.count
        
        # 고유한 place_id 수 (중복 제거)
        unique_places_result = db.table("image_vectors").select("place_id").execute()
        unique_place_ids = set([v.get("place_id") for v in unique_places_result.data])
        places_with_embeddings = len(unique_place_ids)
        
        print("=" * 60)
        print("📊 Embedding Status Report")
        print("=" * 60)
        print(f"Total places: {total_places}")
        print(f"Places with embeddings: {places_with_embeddings}")
        print(f"Total embeddings: {total_vectors}")
        print(f"Coverage: {places_with_embeddings}/{total_places} ({places_with_embeddings/total_places*100:.1f}%)")
        print("=" * 60)
    
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="이미지 임베딩 배치 생성 스크립트")
    parser.add_argument("--all", action="store_true", help="모든 장소 처리")
    parser.add_argument("--place", type=str, help="특정 장소만 처리 (장소명)")
    parser.add_argument("--status", action="store_true", help="임베딩 상태 확인")
    
    args = parser.parse_args()
    
    if args.status:
        check_embedding_status()
    elif args.all:
        seed_all_places()
    elif args.place:
        seed_specific_place(args.place)
    else:
        print("사용법:")
        print("  python seed_image_vectors.py --all          # 모든 장소 처리")
        print("  python seed_image_vectors.py --place 경복궁  # 특정 장소만 처리")
        print("  python seed_image_vectors.py --status       # 상태 확인")
