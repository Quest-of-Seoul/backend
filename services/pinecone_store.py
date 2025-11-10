"""
Pinecone Vector Store Service
벡터 저장 및 유사도 검색 전용
"""

from pinecone import Pinecone, ServerlessSpec
import os
from typing import List, Dict, Optional
from services.db import get_place_by_id

# 전역 클라이언트 (싱글톤 패턴)
_pinecone_client = None
_index = None

def get_pinecone_client():
    """Pinecone 클라이언트 가져오기 (싱글톤)"""
    global _pinecone_client
    
    if _pinecone_client is None:
        api_key = os.getenv("PINECONE_API_KEY")
        if not api_key:
            raise ValueError("PINECONE_API_KEY not set in environment")
        
        _pinecone_client = Pinecone(api_key=api_key)
        print("[Pinecone] ✅ Client initialized")
    
    return _pinecone_client


def get_pinecone_index(index_name: str = "quest-of-seoul"):
    """Pinecone 인덱스 가져오기 (싱글톤)"""
    global _index
    
    if _index is None:
        pc = get_pinecone_client()
        _index = pc.Index(index_name)
        print(f"[Pinecone] ✅ Connected to index: {index_name}")
    
    return _index


def search_similar_pinecone(
    embedding: List[float],
    match_threshold: float = 0.7,
    match_count: int = 5,
    filter_dict: Optional[Dict] = None
) -> List[Dict]:
    """
    Pinecone 벡터 유사도 검색
        
    Args:
        embedding: 쿼리 이미지 임베딩 (512차원)
        match_threshold: 최소 유사도 임계값 (0.0-1.0)
        match_count: 반환할 최대 결과 수
        filter_dict: 메타데이터 필터 (예: {"is_active": True})
    
    Returns:
        유사 이미지 리스트 (장소 정보 포함)
    """
    try:
        index = get_pinecone_index()
        
        # Pinecone 쿼리
        query_params = {
            "vector": embedding,
            "top_k": match_count,
            "include_metadata": True
        }
        
        if filter_dict:
            query_params["filter"] = filter_dict
        
        results = index.query(**query_params)
        
        if not results or not results.get('matches'):
            print("[Pinecone] No similar images found")
            return []
        
        # 결과 변환 및 임계값 필터링
        similar_images = []
        for match in results['matches']:
            score = match.get('score', 0.0)
            
            if score >= match_threshold:
                place_id = match['metadata'].get('place_id')
                
                # Supabase에서 장소 상세 정보 조회
                place = None
                if place_id:
                    place = get_place_by_id(place_id)
                
                similar_images.append({
                    "id": match['id'],
                    "place_id": place_id,
                    "image_url": match['metadata'].get('image_url'),
                    "similarity": score,
                    "place": place
                })
        
        print(f"[Pinecone] ✅ Found {len(similar_images)} similar images (threshold: {match_threshold})")
        return similar_images
    
    except Exception as e:
        print(f"[Pinecone] ❌ Search error: {e}")
        import traceback
        traceback.print_exc()
        return []


def upsert_pinecone(
    vector_id: str,
    embedding: List[float],
    metadata: Dict
) -> Optional[str]:
    """
    Pinecone에 벡터 저장
        
    Args:
        vector_id: 고유 ID (UUID 문자열 권장)
        embedding: 512차원 벡터
        metadata: 메타데이터 딕셔너리
            - place_id: 장소 UUID (필수)
            - image_url: 이미지 URL (필수)
            - image_hash: 이미지 해시 (선택)
            - place_name: 장소명 (선택)
            - source: 출처 (선택)
            - created_at: 생성 시간 (선택)
    
    Returns:
        성공 시 vector_id, 실패 시 None
    """
    try:
        index = get_pinecone_index()
        
        # 필수 필드 검증
        if not metadata.get('place_id'):
            print("[Pinecone] ⚠️ Warning: place_id not provided in metadata")
        
        if not metadata.get('image_url'):
            print("[Pinecone] ⚠️ Warning: image_url not provided in metadata")
        
        # Pinecone upsert (insert or update)
        index.upsert(
            vectors=[(
                vector_id,
                embedding,
                metadata
            )],
            namespace=""  # 기본 namespace 사용
        )
        
        print(f"[Pinecone] ✅ Vector saved: {vector_id[:8]}...")
        return vector_id
    
    except Exception as e:
        print(f"[Pinecone] ❌ Upsert error: {e}")
        import traceback
        traceback.print_exc()
        return None


def upsert_batch_pinecone(
    vectors: List[tuple],
    batch_size: int = 100
) -> int:
    """
    여러 벡터를 배치로 저장 (효율적)
    
    Args:
        vectors: [(vector_id, embedding, metadata), ...] 형식의 리스트
        batch_size: 배치 크기
    
    Returns:
        성공적으로 저장된 벡터 수
    """
    try:
        index = get_pinecone_index()
        total = len(vectors)
        success_count = 0
        
        # 배치로 나누어 처리
        for i in range(0, total, batch_size):
            batch = vectors[i:i+batch_size]
            
            try:
                index.upsert(vectors=batch, namespace="")
                success_count += len(batch)
                print(f"[Pinecone] ✅ Batch {i//batch_size + 1}: {len(batch)} vectors upserted")
            
            except Exception as batch_error:
                print(f"[Pinecone] ❌ Batch {i//batch_size + 1} failed: {batch_error}")
        
        print(f"[Pinecone] 🎉 Total upserted: {success_count}/{total}")
        return success_count
    
    except Exception as e:
        print(f"[Pinecone] ❌ Batch upsert error: {e}")
        return 0


def delete_vector_pinecone(vector_id: str) -> bool:
    """
    벡터 삭제
    
    Args:
        vector_id: 삭제할 벡터 ID
    
    Returns:
        성공 여부
    """
    try:
        index = get_pinecone_index()
        index.delete(ids=[vector_id], namespace="")
        print(f"[Pinecone] ✅ Vector deleted: {vector_id}")
        return True
    
    except Exception as e:
        print(f"[Pinecone] ❌ Delete error: {e}")
        return False


def delete_by_metadata_pinecone(filter_dict: Dict) -> bool:
    """
    메타데이터 조건으로 벡터 삭제
    
    Args:
        filter_dict: 삭제 조건 (예: {"place_id": "xxx"})
    
    Returns:
        성공 여부
    """
    try:
        index = get_pinecone_index()
        index.delete(filter=filter_dict, namespace="")
        print(f"[Pinecone] ✅ Vectors deleted by filter: {filter_dict}")
        return True
    
    except Exception as e:
        print(f"[Pinecone] ❌ Delete by filter error: {e}")
        return False


def get_index_stats() -> Dict:
    """
    Pinecone 인덱스 통계 조회
    
    Returns:
        통계 정보 딕셔너리 (JSON 직렬화 가능)
    """
    try:
        index = get_pinecone_index()
        stats = index.describe_index_stats()
        
        # JSON 직렬화 가능한 값만 추출
        result = {
            "total_vectors": int(stats.get('total_vector_count', 0)),
            "dimension": int(stats.get('dimension', 512)),
            "index_fullness": float(stats.get('index_fullness', 0.0))
        }
        
        print(f"[Pinecone] 📊 Stats: {result['total_vectors']} vectors, {result['dimension']}D")
        return result
    
    except Exception as e:
        print(f"[Pinecone] ❌ Stats error: {e}")
        return {
            "total_vectors": 0,
            "dimension": 512,
            "index_fullness": 0.0
        }


def fetch_vector_by_id(vector_id: str) -> Optional[Dict]:
    """
    ID로 벡터 조회
    
    Args:
        vector_id: 벡터 ID
    
    Returns:
        벡터 정보 (embedding + metadata)
    """
    try:
        index = get_pinecone_index()
        result = index.fetch(ids=[vector_id], namespace="")
        
        if result and result.get('vectors') and vector_id in result['vectors']:
            vector_data = result['vectors'][vector_id]
            return {
                "id": vector_id,
                "values": vector_data.get('values'),
                "metadata": vector_data.get('metadata', {})
            }
        
        print(f"[Pinecone] ⚠️ Vector not found: {vector_id}")
        return None
    
    except Exception as e:
        print(f"[Pinecone] ❌ Fetch error: {e}")
        return None


# 환경 변수로 자동 연결 테스트
if os.getenv("PINECONE_AUTO_CONNECT", "false").lower() == "true":
    try:
        get_pinecone_index()
        print("[Pinecone] 🚀 Auto-connect successful")
    except Exception as e:
        print(f"[Pinecone] ⚠️ Auto-connect failed: {e}")
