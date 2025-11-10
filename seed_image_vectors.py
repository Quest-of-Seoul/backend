"""
이미지 임베딩 배치 생성 스크립트
Supabase DB의 places 테이블에서 이미지를 가져와 임베딩 생성 후 Pinecone에 저장
"""

import os
import sys
import uuid
from dotenv import load_dotenv
import requests
from io import BytesIO
from typing import List, Dict

# 환경 변수 로드
load_dotenv()

# 서비스 import
from services.db import get_db
from services.pinecone_store import upsert_pinecone
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
    
    # Pinecone에 저장
    print(f"💾 Saving to Pinecone...")
    vector_id = str(uuid.uuid4())
    success = upsert_pinecone(
        vector_id=vector_id,
        embedding=embedding,
        metadata={
            "place_id": place_id,
            "image_url": image_url,
            "image_hash": img_hash,
            "place_name": place_name,
            "category": place.get("category"),
            "source": "dataset"
        }
    )
    
    if success:
        print(f"✅ Saved to Pinecone: {vector_id}")
    else:
        print(f"❌ Failed to save to Pinecone")


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
    임베딩 생성 상태 확인 (Pinecone)
    """
    try:
        from services.pinecone_store import get_index_stats
        
        db = get_db()
        
        # 전체 장소 수 (Supabase)
        places_result = db.table("places").select("id", count="exact").execute()
        total_places = places_result.count
        
        # Pinecone 통계
        pinecone_stats = get_index_stats()
        total_vectors = pinecone_stats.get("total_vectors", 0)
        
        print("=" * 60)
        print("📊 Embedding Status Report (Pinecone)")
        print("=" * 60)
        print(f"Total places (Supabase): {total_places}")
        print(f"Total vectors (Pinecone): {total_vectors}")
        print(f"Dimension: {pinecone_stats.get('dimension', 512)}")
        print(f"Index fullness: {pinecone_stats.get('index_fullness', 0):.2%}")
        print("=" * 60)
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


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
