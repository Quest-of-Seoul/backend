"""
VLM API 테스트 스크립트
로컬 이미지 파일 또는 URL을 사용하여 VLM 엔드포인트 테스트
"""

import os
import sys
import base64
import requests
import json
from pathlib import Path
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# API 베이스 URL (로컬 또는 프로덕션)
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def load_image_as_base64(image_path: str) -> str:
    """
    로컬 이미지 파일을 base64로 인코딩
    
    Args:
        image_path: 이미지 파일 경로
    
    Returns:
        Base64 인코딩된 문자열
    """
    try:
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        return base64.b64encode(image_bytes).decode('utf-8')
    except Exception as e:
        print(f"❌ Failed to load image: {e}")
        return None


def download_image_as_base64(image_url: str) -> str:
    """
    URL에서 이미지를 다운로드하여 base64로 인코딩
    
    Args:
        image_url: 이미지 URL
    
    Returns:
        Base64 인코딩된 문자열
    """
    try:
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        return base64.b64encode(response.content).decode('utf-8')
    except Exception as e:
        print(f"❌ Failed to download image: {e}")
        return None


def test_vlm_analyze(
    image_base64: str,
    latitude: float = 37.579617,
    longitude: float = 126.977041,
    language: str = "ko",
    enable_tts: bool = False
):
    """
    /vlm/analyze 엔드포인트 테스트
    
    Args:
        image_base64: Base64 인코딩된 이미지
        latitude: 위도 (기본: 경복궁)
        longitude: 경도 (기본: 경복궁)
        language: 언어
        enable_tts: TTS 생성 여부
    """
    print("\n" + "=" * 60)
    print("🧪 Testing /vlm/analyze endpoint")
    print("=" * 60)
    
    url = f"{API_BASE_URL}/vlm/analyze"
    
    payload = {
        "user_id": "test_user_001",
        "image": image_base64,
        "latitude": latitude,
        "longitude": longitude,
        "language": language,
        "prefer_url": True,
        "enable_tts": enable_tts,
        "use_cache": False  # 테스트시 캐싱 비활성화
    }
    
    print(f"📤 Sending request to {url}")
    print(f"📍 GPS: ({latitude}, {longitude})")
    print(f"🔧 Provider: GPT-4V, TTS: {enable_tts}")
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        
        print("\n✅ Response received!")
        print("=" * 60)
        print(f"📝 Description:")
        print(result.get("description", "N/A"))
        print("\n" + "-" * 60)
        print(f"🏛️ Matched Place: {result.get('place', {}).get('name', 'N/A')}")
        print(f"📊 Confidence Score: {result.get('confidence_score', 0.0)}")
        print(f"⏱️ Processing Time: {result.get('processing_time_ms', 0)}ms")
        print(f"🤖 VLM Provider: {result.get('vlm_provider', 'N/A')}")
        
        # 유사 장소
        similar_places = result.get("similar_places", [])
        if similar_places:
            print(f"\n🔍 Similar Places ({len(similar_places)}):")
            for idx, sim in enumerate(similar_places, 1):
                place_name = sim.get("place", {}).get("name", "N/A")
                similarity = sim.get("similarity", 0.0)
                print(f"  {idx}. {place_name} (similarity: {similarity:.2f})")
        
        # TTS
        if enable_tts:
            if result.get("audio_url"):
                print(f"\n🔊 Audio URL: {result.get('audio_url')}")
            elif result.get("audio"):
                print(f"\n🔊 Audio (base64): {len(result.get('audio'))} chars")
        
        print("=" * 60)
        
        return result
    
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Request failed: {e}")
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}")
        return None


def test_vlm_similar(image_base64: str, limit: int = 3, threshold: float = 0.7):
    """
    /vlm/similar 엔드포인트 테스트
    
    Args:
        image_base64: Base64 인코딩된 이미지
        limit: 결과 개수
        threshold: 유사도 임계값
    """
    print("\n" + "=" * 60)
    print("🧪 Testing /vlm/similar endpoint")
    print("=" * 60)
    
    url = f"{API_BASE_URL}/vlm/similar"
    
    payload = {
        "image": image_base64,
        "limit": limit,
        "threshold": threshold
    }
    
    print(f"📤 Sending request to {url}")
    print(f"🔧 Limit: {limit}, Threshold: {threshold}")
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        print("\n✅ Response received!")
        print("=" * 60)
        
        similar_images = result.get("similar_images", [])
        print(f"🔍 Found {len(similar_images)} similar images:")
        
        for idx, sim in enumerate(similar_images, 1):
            place = sim.get("place", {})
            print(f"\n{idx}. {place.get('name', 'N/A')}")
            print(f"   Similarity: {sim.get('similarity', 0.0):.2f}")
            print(f"   Category: {place.get('category', 'N/A')}")
            print(f"   Image URL: {sim.get('image_url', 'N/A')}")
        
        print("=" * 60)
        
        return result
    
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Request failed: {e}")
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}")
        return None


def test_health_check():
    """
    /vlm/health 엔드포인트 테스트
    """
    print("\n" + "=" * 60)
    print("🧪 Testing /vlm/health endpoint")
    print("=" * 60)
    
    url = f"{API_BASE_URL}/vlm/health"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        
        print("\n✅ Response received!")
        print("=" * 60)
        print(f"Status: {result.get('status', 'N/A')}")
        print("\nServices:")
        services = result.get("services", {})
        for service, available in services.items():
            status = "✅" if available else "❌"
            print(f"  {status} {service}: {available}")
        print("=" * 60)
        
        return result
    
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Request failed: {e}")
        return None


def test_nearby_places(latitude: float = 37.579617, longitude: float = 126.977041):
    """
    /vlm/places/nearby 엔드포인트 테스트
    """
    print("\n" + "=" * 60)
    print("🧪 Testing /vlm/places/nearby endpoint")
    print("=" * 60)
    
    url = f"{API_BASE_URL}/vlm/places/nearby"
    
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "radius_km": 1.0,
        "limit": 10
    }
    
    print(f"📤 Sending request to {url}")
    print(f"📍 GPS: ({latitude}, {longitude})")
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        
        print("\n✅ Response received!")
        print("=" * 60)
        
        places = result.get("places", [])
        print(f"📍 Found {len(places)} nearby places:")
        
        for idx, place in enumerate(places, 1):
            print(f"\n{idx}. {place.get('name', 'N/A')}")
            print(f"   Category: {place.get('category', 'N/A')}")
            print(f"   Distance: {place.get('distance_km', 0.0):.2f}km")
            print(f"   Address: {place.get('address', 'N/A')}")
        
        print("=" * 60)
        
        return result
    
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Request failed: {e}")
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}")
        return None


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="VLM API 테스트 스크립트")
    parser.add_argument("--health", action="store_true", help="Health check")
    parser.add_argument("--nearby", action="store_true", help="주변 장소 검색 테스트")
    parser.add_argument("--analyze", type=str, help="이미지 분석 테스트 (이미지 파일 경로 또는 URL)")
    parser.add_argument("--similar", type=str, help="유사 이미지 검색 테스트 (이미지 파일 경로 또는 URL)")
    parser.add_argument("--lat", type=float, default=37.579617, help="위도 (기본: 경복궁)")
    parser.add_argument("--lon", type=float, default=126.977041, help="경도 (기본: 경복궁)")
    parser.add_argument("--tts", action="store_true", help="TTS 생성 활성화")
    parser.add_argument("--base-url", type=str, help="API 베이스 URL")
    
    args = parser.parse_args()
    
    # API 베이스 URL 설정
    if args.base_url:
        API_BASE_URL = args.base_url
    
    print(f"\n🌐 API Base URL: {API_BASE_URL}\n")
    
    if args.health:
        test_health_check()
    
    elif args.nearby:
        test_nearby_places(latitude=args.lat, longitude=args.lon)
    
    elif args.analyze:
        # 이미지 로드
        if args.analyze.startswith("http"):
            print(f"📥 Downloading image from URL: {args.analyze}")
            image_base64 = download_image_as_base64(args.analyze)
        else:
            print(f"📂 Loading image from file: {args.analyze}")
            image_base64 = load_image_as_base64(args.analyze)
        
        if image_base64:
            test_vlm_analyze(
                image_base64=image_base64,
                latitude=args.lat,
                longitude=args.lon,
                enable_tts=args.tts
            )
    
    elif args.similar:
        # 이미지 로드
        if args.similar.startswith("http"):
            print(f"📥 Downloading image from URL: {args.similar}")
            image_base64 = download_image_as_base64(args.similar)
        else:
            print(f"📂 Loading image from file: {args.similar}")
            image_base64 = load_image_as_base64(args.similar)
        
        if image_base64:
            test_vlm_similar(image_base64=image_base64)
    
    else:
        print("사용법:")
        print("  python test_vlm.py --health")
        print("  python test_vlm.py --nearby --lat 37.5796 --lon 126.9770")
        print("  python test_vlm.py --analyze image.jpg --lat 37.5796 --lon 126.9770")
        print("  python test_vlm.py --analyze https://example.com/image.jpg --tts")
        print("  python test_vlm.py --similar image.jpg")
        print("\n옵션:")
        print("  --tts                         # TTS 생성 활성화")
        print("  --base-url http://...         # API 베이스 URL 설정")
