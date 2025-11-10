"""
Supabase pgvector → Pinecone 마이그레이션 스크립트
기존 image_vectors 테이블의 모든 벡터를 Pinecone으로 이전
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 서비스 import
from services.db import get_db
from services.pinecone_store import (
    upsert_batch_pinecone,
    get_index_stats,
    get_pinecone_index
)


def migrate_all_vectors(batch_size: int = 100, dry_run: bool = False):
    """
    모든 벡터를 Pinecone으로 마이그레이션
    
    Args:
        batch_size: 배치 크기
        dry_run: True면 실제 업로드 없이 테스트만
    """
    print("=" * 60)
    print("🚀 Pinecone Migration - pgvector → Pinecone")
    print("=" * 60)
    
    if dry_run:
        print("⚠️  DRY RUN MODE - No actual upload will occur")
    
    try:
        # 1. Supabase에서 모든 벡터 조회
        print("\n📊 Step 1: Fetching vectors from Supabase...")
        db = get_db()
        
        result = db.table("image_vectors").select("*").execute()
        
        if not result.data:
            print("❌ No vectors found in image_vectors table")
            print("\n💡 Tip: Run 'python seed_image_vectors.py --all' first")
            return
        
        vectors = result.data
        total = len(vectors)
        
        print(f"✅ Found {total} vectors to migrate")
        
        # 2. 데이터 검증
        print("\n🔍 Step 2: Validating data...")
        valid_vectors = []
        invalid_count = 0
        
        for vec in vectors:
            vector_id = vec.get('id')
            embedding = vec.get('embedding')
            place_id = vec.get('place_id')
            
            # 필수 필드 검증
            if not vector_id or not embedding or not place_id:
                print(f"⚠️  Skipping invalid vector: {vector_id}")
                invalid_count += 1
                continue
            
            # 벡터 차원 검증
            if len(embedding) != 512:
                print(f"⚠️  Skipping vector with wrong dimension: {vector_id} ({len(embedding)}D)")
                invalid_count += 1
                continue
            
            valid_vectors.append(vec)
        
        if invalid_count > 0:
            print(f"⚠️  {invalid_count} invalid vectors skipped")
        
        print(f"✅ {len(valid_vectors)} valid vectors ready")
        
        if len(valid_vectors) == 0:
            print("❌ No valid vectors to migrate")
            return
        
        # 3. Pinecone 연결 테스트
        print("\n🔌 Step 3: Testing Pinecone connection...")
        
        try:
            index = get_pinecone_index()
            initial_stats = get_index_stats()
            print(f"✅ Connected to Pinecone")
            print(f"   Current vectors: {initial_stats.get('total_vectors', 0)}")
            print(f"   Dimension: {initial_stats.get('dimension', 512)}")
        except Exception as e:
            print(f"❌ Failed to connect to Pinecone: {e}")
            print("\n💡 Tip: Run 'python setup_pinecone.py' first")
            return
        
        # 4. 마이그레이션 확인
        if not dry_run:
            print(f"\n⚠️  About to upload {len(valid_vectors)} vectors to Pinecone")
            response = input("Continue? (y/N): ").strip().lower()
            
            if response != 'y':
                print("❌ Migration cancelled")
                return
        
        # 5. 배치 업로드
        print(f"\n📤 Step 4: Uploading to Pinecone (batch size: {batch_size})...")
        
        # Pinecone 형식으로 변환
        pinecone_vectors = []
        for vec in valid_vectors:
            vector_tuple = (
                str(vec['id']),  # vector ID
                vec['embedding'],  # 512차원 벡터
                {
                    'place_id': vec['place_id'],
                    'image_url': vec.get('image_url', ''),
                    'image_hash': vec.get('image_hash', ''),
                    'source': vec.get('source', 'dataset'),
                    'created_at': vec.get('created_at', datetime.now().isoformat())
                }
            )
            pinecone_vectors.append(vector_tuple)
        
        if dry_run:
            print(f"✅ DRY RUN: Would upload {len(pinecone_vectors)} vectors")
            print("\nSample vector:")
            if pinecone_vectors:
                sample = pinecone_vectors[0]
                print(f"  ID: {sample[0]}")
                print(f"  Embedding dim: {len(sample[1])}")
                print(f"  Metadata: {sample[2]}")
        else:
            # 실제 업로드
            success_count = upsert_batch_pinecone(
                vectors=pinecone_vectors,
                batch_size=batch_size
            )
            
            print(f"\n✅ Upload complete: {success_count}/{len(valid_vectors)}")
        
        # 6. 결과 확인
        if not dry_run:
            print("\n📊 Step 5: Verifying migration...")
            
            import time
            time.sleep(2)  # Pinecone 인덱싱 대기
            
            final_stats = get_index_stats()
            initial_count = initial_stats.get('total_vectors', 0)
            final_count = final_stats.get('total_vectors', 0)
            added = final_count - initial_count
            
            print(f"   Before: {initial_count} vectors")
            print(f"   After: {final_count} vectors")
            print(f"   Added: {added} vectors")
        
        # 7. 완료
        print("\n" + "=" * 60)
        print("🎉 Migration Complete!")
        print("=" * 60)
        
        if not dry_run:
            print("\n✅ Next steps:")
            print("  1. Test the migration:")
            print("     python -c 'from services.pinecone_store import get_index_stats; print(get_index_stats())'")
            print("\n  2. Update your code to use Pinecone:")
            print("     - services/db.py → services/pinecone_store.py")
            print("\n  3. Optional: Backup and drop image_vectors table")
            print("     (Keep places and vlm_logs tables!)")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()


def verify_migration():
    """마이그레이션 검증 - 샘플 데이터 비교"""
    print("=" * 60)
    print("🔍 Migration Verification")
    print("=" * 60)
    
    try:
        # Supabase에서 샘플 조회
        print("\n1️⃣ Checking Supabase...")
        db = get_db()
        supabase_result = db.table("image_vectors").select("id, place_id").limit(5).execute()
        
        if not supabase_result.data:
            print("⚠️  No data in Supabase")
            return
        
        print(f"✅ Found {len(supabase_result.data)} sample vectors in Supabase")
        
        # Pinecone에서 확인
        print("\n2️⃣ Checking Pinecone...")
        from services.pinecone_store import fetch_vector_by_id
        
        matched = 0
        missing = []
        
        for vec in supabase_result.data:
            vec_id = str(vec['id'])
            pinecone_vec = fetch_vector_by_id(vec_id)
            
            if pinecone_vec:
                matched += 1
                print(f"✅ {vec_id[:8]}... - Found in Pinecone")
            else:
                missing.append(vec_id)
                print(f"❌ {vec_id[:8]}... - Missing in Pinecone")
        
        # 결과
        print("\n" + "=" * 60)
        print(f"📊 Verification Result:")
        print(f"   Matched: {matched}/{len(supabase_result.data)}")
        
        if missing:
            print(f"   Missing: {len(missing)}")
            print(f"   IDs: {missing}")
        else:
            print("   ✅ All sample vectors found in Pinecone!")
        print("=" * 60)
    
    except Exception as e:
        print(f"❌ Verification failed: {e}")


def compare_search_results():
    """검색 결과 비교 - pgvector vs Pinecone"""
    print("=" * 60)
    print("🔍 Search Comparison - pgvector vs Pinecone")
    print("=" * 60)
    
    try:
        # 테스트용 벡터 가져오기
        db = get_db()
        result = db.table("image_vectors").select("embedding").limit(1).execute()
        
        if not result.data or not result.data[0].get('embedding'):
            print("❌ No test vector found")
            return
        
        test_embedding = result.data[0]['embedding']
        print(f"✅ Using test vector (dim: {len(test_embedding)})")
        
        # pgvector 검색
        print("\n1️⃣ pgvector search...")
        from services.db import search_similar_images as search_pgvector
        
        pgvector_results = search_pgvector(
            embedding=test_embedding,
            match_threshold=0.7,
            match_count=5
        )
        
        print(f"✅ pgvector found: {len(pgvector_results)} results")
        
        # Pinecone 검색
        print("\n2️⃣ Pinecone search...")
        from services.pinecone_store import search_similar_pinecone
        
        pinecone_results = search_similar_pinecone(
            embedding=test_embedding,
            match_threshold=0.7,
            match_count=5
        )
        
        print(f"✅ Pinecone found: {len(pinecone_results)} results")
        
        # 비교
        print("\n" + "=" * 60)
        print("📊 Comparison:")
        print(f"   pgvector: {len(pgvector_results)} results")
        print(f"   Pinecone: {len(pinecone_results)} results")
        
        if len(pgvector_results) > 0 and len(pinecone_results) > 0:
            print("\n   Top result comparison:")
            print(f"   pgvector similarity: {pgvector_results[0].get('similarity', 0):.4f}")
            print(f"   Pinecone similarity: {pinecone_results[0].get('similarity', 0):.4f}")
        
        print("=" * 60)
    
    except Exception as e:
        print(f"❌ Comparison failed: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate vectors from pgvector to Pinecone")
    parser.add_argument("--dry-run", action="store_true", help="Test without uploading")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size for upload")
    parser.add_argument("--verify", action="store_true", help="Verify migration")
    parser.add_argument("--compare", action="store_true", help="Compare search results")
    
    args = parser.parse_args()
    
    if args.verify:
        verify_migration()
    elif args.compare:
        compare_search_results()
    else:
        migrate_all_vectors(
            batch_size=args.batch_size,
            dry_run=args.dry_run
        )
