"""Place Matcher Service"""

import logging
import math
from typing import Dict, Optional, List, Tuple
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    두 좌표 간 거리 계산 (Haversine formula, km 단위)
    
    Args:
        lat1, lon1: 첫 번째 좌표
        lat2, lon2: 두 번째 좌표
    
    Returns:
        거리 (km)
    """
    if not all([lat1, lon1, lat2, lon2]):
        return float('inf')
    
    R = 6371  # 지구 반경 (km)
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) *
         math.sin(delta_lon / 2) ** 2)
    c = 2 * math.asin(math.sqrt(a))
    
    distance = R * c
    return round(distance, 2)


def calculate_name_similarity(name1: str, name2: str) -> float:
    """
    두 장소명의 유사도 계산 (0.0 ~ 1.0)
    
    Args:
        name1: 첫 번째 장소명
        name2: 두 번째 장소명
    
    Returns:
        유사도 (0.0 ~ 1.0)
    """
    if not name1 or not name2:
        return 0.0
    
    name1_clean = name1.strip().lower()
    name2_clean = name2.strip().lower()
    
    if name1_clean == name2_clean:
        return 1.0
    
    similarity = SequenceMatcher(None, name1_clean, name2_clean).ratio()
    
    # 부분 문자열 포함 여부 확인
    if name1_clean in name2_clean or name2_clean in name1_clean:
        # 포함된 경우 유사도 보정
        similarity = max(similarity, 0.8)
    
    return round(similarity, 3)


def normalize_place_name(name: str) -> str:
    """
    장소명 정규화 (비교를 위해)
    
    Args:
        name: 원본 장소명
    
    Returns:
        정규화된 장소명
    """
    if not name:
        return ""
    
    # 공통 제거 단어
    remove_words = ["서울", "Seoul", "서울시", "서울특별시", "서울시청", "시청"]
    
    normalized = name.strip()
    for word in remove_words:
        normalized = normalized.replace(word, "").strip()
    
    return normalized


def match_places(
    tour_place: Dict,
    visit_seoul_places: List[Dict],
    max_distance_km: float = 1.0,
    min_name_similarity: float = 0.6
) -> Optional[Tuple[Dict, float, float]]:
    """
    TourAPI 장소와 VISIT SEOUL 장소 매칭
    
    Args:
        tour_place: TourAPI 장소 데이터
        visit_seoul_places: VISIT SEOUL 장소 리스트
        max_distance_km: 최대 거리 (km)
        min_name_similarity: 최소 이름 유사도
    
    Returns:
        (매칭된 VISIT SEOUL 장소, 거리, 이름 유사도) 또는 None
    """
    tour_name = tour_place.get("name") or ""
    tour_lat = tour_place.get("latitude")
    tour_lon = tour_place.get("longitude")
    
    if not tour_name:
        logger.warning("Tour place has no name")
        return None
    
    best_match = None
    best_score = 0.0
    best_distance = float('inf')
    best_similarity = 0.0
    
    tour_name_normalized = normalize_place_name(tour_name)
    
    for vs_place in visit_seoul_places:
        vs_name = vs_place.get("name") or ""
        vs_lat = vs_place.get("latitude")
        vs_lon = vs_place.get("longitude")
        
        if not vs_name:
            continue
        
        # 이름 유사도 계산
        name_similarity = calculate_name_similarity(tour_name, vs_name)
        
        if name_similarity < min_name_similarity:
            continue
        
        # 좌표 거리 계산
        distance = float('inf')
        if tour_lat and tour_lon and vs_lat and vs_lon:
            distance = calculate_distance(tour_lat, tour_lon, vs_lat, vs_lon)
            
            # 거리가 너무 멀면 제외
            if distance > max_distance_km:
                continue
        
        # 종합 점수 계산 (이름 유사도 70%, 거리 30%)
        if distance < float('inf'):
            # 거리가 가까울수록 높은 점수 (1km = 1.0, 0km = 1.0)
            distance_score = max(0.0, 1.0 - (distance / max_distance_km))
            combined_score = (name_similarity * 0.7) + (distance_score * 0.3)
        else:
            # 좌표가 없으면 이름 유사도만 사용
            combined_score = name_similarity
        
        # 최고 점수 업데이트
        if combined_score > best_score:
            best_match = vs_place
            best_score = combined_score
            best_distance = distance
            best_similarity = name_similarity
    
    if best_match and best_score >= min_name_similarity:
        logger.info(
            f"Matched: '{tour_name}' <-> '{best_match.get('name')}' "
            f"(similarity: {best_similarity:.3f}, distance: {best_distance:.2f}km, score: {best_score:.3f})"
        )
        return (best_match, best_distance, best_similarity)
    
    return None


def find_best_matches(
    tour_places: List[Dict],
    visit_seoul_places: List[Dict],
    max_distance_km: float = 1.0,
    min_name_similarity: float = 0.6
) -> List[Tuple[Dict, Dict, float, float]]:
    """
    TourAPI 장소 리스트와 VISIT SEOUL 장소 리스트 간 최적 매칭 찾기
    
    Args:
        tour_places: TourAPI 장소 리스트
        visit_seoul_places: VISIT SEOUL 장소 리스트
        max_distance_km: 최대 거리 (km)
        min_name_similarity: 최소 이름 유사도
    
    Returns:
        [(tour_place, visit_seoul_place, distance, similarity), ...] 리스트
    """
    matches = []
    used_vs_indices = set()
    
    # TourAPI 장소별로 최적 매칭 찾기
    for tour_place in tour_places:
        # 이미 매칭된 VISIT SEOUL 장소 제외
        available_vs_places = [
            vs for idx, vs in enumerate(visit_seoul_places)
            if idx not in used_vs_indices
        ]
        
        match_result = match_places(
            tour_place=tour_place,
            visit_seoul_places=available_vs_places,
            max_distance_km=max_distance_km,
            min_name_similarity=min_name_similarity
        )
        
        if match_result:
            vs_place, distance, similarity = match_result
            
            # 사용된 VISIT SEOUL 장소 인덱스 찾기
            vs_idx = next(
                (idx for idx, vs in enumerate(visit_seoul_places) if vs == vs_place),
                None
            )
            
            if vs_idx is not None:
                used_vs_indices.add(vs_idx)
                matches.append((tour_place, vs_place, distance, similarity))
    
    logger.info(f"Found {len(matches)} matches out of {len(tour_places)} TourAPI places")
    return matches
