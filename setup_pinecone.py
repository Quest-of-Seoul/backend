"""
Pinecone 인덱스 초기화 스크립트
Quest of Seoul - VLM 이미지 벡터 검색용 인덱스 생성
"""

from pinecone import Pinecone, ServerlessSpec
import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()


def create_pinecone_index(
    index_name: str = "quest-of-seoul",
    dimension: int = 512,
    metric: str = "cosine",
    cloud: str = "aws",
    region: str = "us-east-1"
):
    """
    Pinecone 인덱스 생성
    
    Args:
        index_name: 인덱스 이름
        dimension: 벡터 차원 (CLIP은 512)
        metric: 거리 측정 방식 (cosine, euclidean, dotproduct)
        cloud: 클라우드 제공자 (aws, gcp, azure)
        region: 리전
    """
    try:
        print("=" * 60)
        print("🚀 Pinecone Index Setup")
        print("=" * 60)
        
        # Pinecone API 키 확인
        api_key = os.getenv("PINECONE_API_KEY")
        if not api_key:
            raise ValueError("❌ PINECONE_API_KEY not set in .env file")
        
        print(f"✅ API Key found: {api_key[:8]}...")
        
        # Pinecone 클라이언트 초기화
        pc = Pinecone(api_key=api_key)
        print("✅ Pinecone client initialized")
        
        # 기존 인덱스 확인
        existing_indexes = pc.list_indexes()
        index_names = [idx.name for idx in existing_indexes]
        
        if index_name in index_names:
            print(f"⚠️  Index '{index_name}' already exists")
            
            # 기존 인덱스 정보 조회
            index = pc.Index(index_name)
            stats = index.describe_index_stats()
            
            print(f"\n📊 Existing Index Info:")
            print(f"  - Name: {index_name}")
            print(f"  - Dimension: {stats.get('dimension', 'N/A')}")
            print(f"  - Total vectors: {stats.get('total_vector_count', 0)}")
            print(f"  - Index fullness: {stats.get('index_fullness', 0):.2%}")
            
            # 덮어쓸지 물어보기
            response = input("\n🔄 Delete and recreate index? (y/N): ").strip().lower()
            
            if response == 'y':
                print(f"🗑️  Deleting existing index...")
                pc.delete_index(index_name)
                print("✅ Index deleted")
                
                # 삭제 완료 대기 (몇 초 소요)
                import time
                print("⏳ Waiting for deletion to complete...")
                time.sleep(5)
            else:
                print("✅ Keeping existing index")
                return
        
        # 새 인덱스 생성
        print(f"\n📝 Creating new index...")
        print(f"  - Name: {index_name}")
        print(f"  - Dimension: {dimension}")
        print(f"  - Metric: {metric}")
        print(f"  - Cloud: {cloud}")
        print(f"  - Region: {region}")
        
        pc.create_index(
            name=index_name,
            dimension=dimension,
            metric=metric,
            spec=ServerlessSpec(
                cloud=cloud,
                region=region
            )
        )
        
        print("✅ Index created successfully!")
        
        # 인덱스 준비 대기
        print("⏳ Waiting for index to be ready...")
        import time
        time.sleep(10)
        
        # 인덱스 연결 테스트
        index = pc.Index(index_name)
        stats = index.describe_index_stats()
        
        print("\n" + "=" * 60)
        print("🎉 Setup Complete!")
        print("=" * 60)
        print(f"✅ Index '{index_name}' is ready to use")
        print(f"📊 Initial stats:")
        print(f"  - Dimension: {stats.get('dimension')}")
        print(f"  - Total vectors: {stats.get('total_vector_count', 0)}")
        print("=" * 60)
        
        print("\n💡 Next steps:")
        print("  1. Run: python migrate_to_pinecone.py")
        print("  2. Update .env: VECTOR_BACKEND=pinecone")
        print("  3. Test: python test_vlm.py")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


def check_pinecone_status():
    """Pinecone 연결 및 인덱스 상태 확인"""
    try:
        api_key = os.getenv("PINECONE_API_KEY")
        if not api_key:
            print("❌ PINECONE_API_KEY not set")
            return
        
        pc = Pinecone(api_key=api_key)
        
        print("=" * 60)
        print("📊 Pinecone Status Check")
        print("=" * 60)
        
        # 모든 인덱스 목록
        indexes = pc.list_indexes()
        
        if not indexes:
            print("⚠️  No indexes found")
            return
        
        print(f"\n✅ Found {len(indexes)} index(es):\n")
        
        for idx_info in indexes:
            print(f"📌 Index: {idx_info.name}")
            print(f"  - Host: {idx_info.host}")
            print(f"  - Dimension: {idx_info.dimension}")
            print(f"  - Metric: {idx_info.metric}")
            
            # 상세 통계
            try:
                index = pc.Index(idx_info.name)
                stats = index.describe_index_stats()
                
                print(f"  - Total vectors: {stats.get('total_vector_count', 0):,}")
                print(f"  - Index fullness: {stats.get('index_fullness', 0):.2%}")
                
                namespaces = stats.get('namespaces', {})
                if namespaces:
                    print(f"  - Namespaces: {len(namespaces)}")
                    for ns_name, ns_stats in namespaces.items():
                        ns_count = ns_stats.get('vector_count', 0)
                        print(f"    - '{ns_name}': {ns_count:,} vectors")
            
            except Exception as e:
                print(f"  ⚠️  Could not fetch stats: {e}")
            
            print()
        
        print("=" * 60)
    
    except Exception as e:
        print(f"❌ Error: {e}")


def delete_all_vectors(index_name: str = "quest-of-seoul"):
    """인덱스의 모든 벡터 삭제 (초기화)"""
    try:
        api_key = os.getenv("PINECONE_API_KEY")
        if not api_key:
            print("❌ PINECONE_API_KEY not set")
            return
        
        pc = Pinecone(api_key=api_key)
        index = pc.Index(index_name)
        
        print(f"⚠️  WARNING: This will delete ALL vectors in '{index_name}'")
        response = input("Are you sure? (yes/N): ").strip().lower()
        
        if response != 'yes':
            print("❌ Cancelled")
            return
        
        print("🗑️  Deleting all vectors...")
        index.delete(delete_all=True)
        print("✅ All vectors deleted")
    
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "status":
            check_pinecone_status()
        elif command == "delete":
            delete_all_vectors()
        elif command == "create":
            create_pinecone_index()
        else:
            print("Usage:")
            print("  python setup_pinecone.py create   # Create index")
            print("  python setup_pinecone.py status   # Check status")
            print("  python setup_pinecone.py delete   # Delete all vectors")
    else:
        # 기본: 인덱스 생성
        create_pinecone_index()
