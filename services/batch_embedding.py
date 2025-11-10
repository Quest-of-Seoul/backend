"""
비동기 배치 임베딩 처리 서비스
대량 이미지 처리 시 성능 최적화
"""

import asyncio
import aiohttp
from typing import List, Dict, Optional, Tuple
from io import BytesIO
import time

from services.embedding import generate_embeddings_batch, hash_image
from services.pinecone_store import upsert_batch_pinecone


async def download_image_async(url: str, session: aiohttp.ClientSession) -> Optional[bytes]:
    """
    비동기 이미지 다운로드
    
    Args:
        url: 이미지 URL
        session: aiohttp 세션
    
    Returns:
        이미지 바이트 또는 None
    """
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
            if response.status == 200:
                return await response.read()
            else:
                print(f"⚠️  Failed to download {url}: Status {response.status}")
                return None
    
    except Exception as e:
        print(f"⚠️  Download error for {url}: {e}")
        return None


async def download_images_batch(
    urls: List[str],
    max_concurrent: int = 10
) -> List[Optional[bytes]]:
    """
    여러 이미지를 병렬로 다운로드
    
    Args:
        urls: 이미지 URL 리스트
        max_concurrent: 최대 동시 다운로드 수
    
    Returns:
        이미지 바이트 리스트
    """
    connector = aiohttp.TCPConnector(limit=max_concurrent)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [download_image_async(url, session) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Exception을 None으로 변환
        images = []
        for result in results:
            if isinstance(result, Exception):
                images.append(None)
            else:
                images.append(result)
        
        return images


def process_places_batch(
    places: List[Dict],
    batch_size: int = 10,
    max_concurrent_downloads: int = 5
) -> Tuple[int, int]:
    """
    여러 장소의 이미지를 배치로 처리하여 Pinecone에 저장
    
    Args:
        places: 장소 정보 리스트 (id, name, image_url 포함)
        batch_size: 임베딩 배치 크기
        max_concurrent_downloads: 최대 동시 다운로드
    
    Returns:
        (성공 수, 실패 수)
    """
    print(f"\n🚀 Batch Embedding Process")
    print(f"Total places: {len(places)}")
    print(f"Batch size: {batch_size}")
    print(f"Max concurrent downloads: {max_concurrent_downloads}")
    
    success_count = 0
    fail_count = 0
    
    start_time = time.time()
    
    for batch_idx in range(0, len(places), batch_size):
        batch = places[batch_idx:batch_idx + batch_size]
        batch_num = batch_idx // batch_size + 1
        total_batches = (len(places) + batch_size - 1) // batch_size
        
        print(f"\n[Batch {batch_num}/{total_batches}]")
        
        # 1. 비동기 이미지 다운로드
        urls = [p.get("image_url") for p in batch if p.get("image_url")]
        
        if not urls:
            print("⚠️  No valid URLs in batch")
            fail_count += len(batch)
            continue
        
        print(f"📥 Downloading {len(urls)} images...")
        images = asyncio.run(download_images_batch(urls, max_concurrent_downloads))
        
        downloaded_count = sum(1 for img in images if img is not None)
        print(f"✅ Downloaded: {downloaded_count}/{len(urls)}")
        
        # 2. CLIP 배치 임베딩 생성
        print(f"🧠 Generating embeddings...")
        
        valid_images = [img for img in images if img is not None]
        
        if not valid_images:
            print("❌ No valid images to process")
            fail_count += len(batch)
            continue
        
        embeddings = generate_embeddings_batch(valid_images, batch_size=batch_size)
        
        # 3. Pinecone 업로드 준비
        pinecone_vectors = []
        
        for place, image_bytes, embedding in zip(batch, images, embeddings):
            if image_bytes is None or embedding is None:
                fail_count += 1
                continue
            
            import uuid
            vector_id = str(uuid.uuid4())
            img_hash = hash_image(image_bytes)
            
            pinecone_vectors.append((
                vector_id,
                embedding,
                {
                    "place_id": place["id"],
                    "place_name": place.get("name", ""),
                    "image_url": place.get("image_url", ""),
                    "image_hash": img_hash,
                    "category": place.get("category", ""),
                    "source": place.get("source", "tour_api")
                }
            ))
        
        # 4. Pinecone 업로드
        if pinecone_vectors:
            print(f"💾 Uploading to Pinecone...")
            uploaded = upsert_batch_pinecone(pinecone_vectors, batch_size=100)
            success_count += uploaded
            print(f"✅ Uploaded: {uploaded}")
        
        # API rate limit 방지
        time.sleep(0.5)
    
    elapsed_time = time.time() - start_time
    
    # 결과 출력
    print("\n" + "=" * 60)
    print("🎉 Batch Process Complete")
    print("=" * 60)
    print(f"✅ Success: {success_count}/{len(places)}")
    print(f"❌ Failed: {fail_count}/{len(places)}")
    print(f"⏱️  Time: {elapsed_time:.1f}s")
    print(f"📊 Speed: {len(places)/elapsed_time:.1f} images/sec")
    print("=" * 60)
    
    return success_count, fail_count


def process_tour_api_places():
    """
    TourAPI로 수집한 장소들의 임베딩 생성
    """
    from services.db import get_db
    
    print("=" * 60)
    print("🔄 Processing TourAPI Places")
    print("=" * 60)
    
    try:
        db = get_db()
        
        # TourAPI 장소만 조회 (아직 임베딩 안된 것)
        result = db.table("places") \
            .select("id, name, category, image_url, source") \
            .eq("source", "tour_api") \
            .eq("is_active", True) \
            .execute()
        
        places = result.data
        
        if not places:
            print("⚠️  No TourAPI places found")
            print("Run: python scripts/fetch_tour_api.py --all")
            return
        
        print(f"📊 Found {len(places)} TourAPI places")
        
        # 배치 처리
        process_places_batch(
            places=places,
            batch_size=10,
            max_concurrent_downloads=5
        )
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="비동기 배치 임베딩 처리")
    parser.add_argument("--tour-api", action="store_true", help="TourAPI 장소만 처리")
    
    args = parser.parse_args()
    
    if args.tour_api:
        process_tour_api_places()
    else:
        print("Usage:")
        print("  python -m services.batch_embedding --tour-api")
