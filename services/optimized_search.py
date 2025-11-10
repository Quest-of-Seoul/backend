"""
최적화된 이미지 검색 서비스
GPS 필터링 + 벡터 검색 하이브리드
"""

from typing import List, Dict, Optional
from services.db import get_db, search_places_by_radius
from services.pinecone_store import search_similar_pinecone
from services.embedding import generate_image_embedding


def search_with_gps_filter(
    embedding: List[float],
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    radius_km: float = 5.0,
    match_threshold: float = 0.65,
    match_count: int = 5,
    quest_only: bool = False
) -> List[Dict]:
    """
    GPS 필터링 + 벡터 검색
    
    Args:
        embedding: 이미지 임베딩 벡터
        latitude: 위도 (있으면 GPS 필터링)
        longitude: 경도 (있으면 GPS 필터링)
        radius_km: 검색 반경 (km)
        match_threshold: 유사도 임계값
        match_count: 결과 개수
        quest_only: True면 퀘스트 등록 장소만
    
    Returns:
        유사 이미지 리스트
    """
    try:
        # GPS 필터링이 있는 경우
        if latitude and longitude:
            print(f"[Search] 🌍 GPS filtering: {radius_km}km radius")
            
            # 1단계: GPS로 주변 장소 필터링
            nearby_places = search_places_by_radius(
                latitude=latitude,
                longitude=longitude,
                radius_km=radius_km,
                limit_count=100
            )
            
            if not nearby_places:
                print("[Search] ⚠️  No nearby places found")
                return []
            
            nearby_place_ids = [p['id'] for p in nearby_places]
            print(f"[Search] 📍 Found {len(nearby_place_ids)} nearby places")
            
            # 2단계: 퀘스트 필터 (선택)
            if quest_only:
                db = get_db()
                quest_result = db.table("quests") \
                    .select("place_id") \
                    .eq("is_active", True) \
                    .in_("place_id", nearby_place_ids) \
                    .execute()
                
                quest_place_ids = [q['place_id'] for q in quest_result.data]
                print(f"[Search] 🎯 Filtered to {len(quest_place_ids)} quest places")
                
                if not quest_place_ids:
                    print("[Search] ⚠️  No quest places nearby")
                    return []
                
                filter_ids = quest_place_ids
            else:
                filter_ids = nearby_place_ids
            
            # 3단계: Pinecone 벡터 검색 (필터 적용)
            print(f"[Search] 🔍 Vector search with {len(filter_ids)} candidates")
            
            # Pinecone은 $in 필터를 지원하지 않을 수 있으므로
            # 검색 후 필터링
            results = search_similar_pinecone(
                embedding=embedding,
                match_threshold=match_threshold,
                match_count=match_count * 3  # 더 많이 가져와서 필터링
            )
            
            # GPS 범위 내 결과만 필터링
            filtered_results = [
                r for r in results
                if r.get('place', {}).get('id') in filter_ids
            ][:match_count]
            
            print(f"[Search] ✅ Final results: {len(filtered_results)}")
            return filtered_results
        
        else:
            # GPS 없으면 전체 검색
            print(f"[Search] 🔍 Full vector search")
            return search_similar_pinecone(
                embedding=embedding,
                match_threshold=match_threshold,
                match_count=match_count
            )
    
    except Exception as e:
        print(f"[Search] ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return []


def search_similar_with_optimization(
    image_bytes: bytes,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    radius_km: float = 5.0,
    match_threshold: float = 0.65,
    match_count: int = 5,
    quest_only: bool = False
) -> List[Dict]:
    """
    이미지 유사도 검색 (최적화 버전)
    
    Args:
        image_bytes: 이미지 바이트
        latitude: 위도
        longitude: 경도
        radius_km: 검색 반경
        match_threshold: 유사도 임계값
        match_count: 결과 개수
        quest_only: 퀘스트 장소만
    
    Returns:
        유사 장소 리스트
    """
    # 임베딩 생성
    embedding = generate_image_embedding(image_bytes)
    
    if not embedding:
        print("[Search] ❌ Embedding generation failed")
        return []
    
    # GPS 필터링 검색
    return search_with_gps_filter(
        embedding=embedding,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        match_threshold=match_threshold,
        match_count=match_count,
        quest_only=quest_only
    )


def get_quest_places_by_category(category: str, limit: int = 20) -> List[Dict]:
    """
    카테고리별 퀘스트 장소 조회
    
    Args:
        category: 카테고리명
        limit: 최대 개수
    
    Returns:
        장소 리스트
    """
    try:
        db = get_db()
        
        result = db.rpc(
            "get_places_with_quests",
            {
                "category_filter": category,
                "limit_count": limit
            }
        ).execute()
        
        return result.data if result.data else []
    
    except Exception as e:
        print(f"[Search] ❌ Error getting quest places: {e}")
        return []


def search_nearby_quests(
    latitude: float,
    longitude: float,
    radius_km: float = 5.0,
    limit: int = 10
) -> List[Dict]:
    """
    주변 퀘스트 검색
    
    Args:
        latitude: 위도
        longitude: 경도
        radius_km: 검색 반경
        limit: 최대 개수
    
    Returns:
        주변 퀘스트 리스트
    """
    try:
        db = get_db()
        
        result = db.rpc(
            "search_nearby_quests",
            {
                "lat": latitude,
                "lon": longitude,
                "radius_km": radius_km,
                "limit_count": limit
            }
        ).execute()
        
        return result.data if result.data else []
    
    except Exception as e:
        print(f"[Search] ❌ Error searching nearby quests: {e}")
        return []
