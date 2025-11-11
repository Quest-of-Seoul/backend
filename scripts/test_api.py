#!/usr/bin/env python3
"""API Test Script"""

import requests
import base64
import json
import sys
from pathlib import Path

BASE_URL = "http://localhost:8000"


def test_health():
    """Test health endpoints"""
    print("\n=== Health Check ===")
    
    response = requests.get(f"{BASE_URL}/")
    print(f"GET / : {response.status_code}")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    
    response = requests.get(f"{BASE_URL}/health")
    print(f"\nGET /health : {response.status_code}")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    
    response = requests.get(f"{BASE_URL}/vlm/health")
    print(f"\nGET /vlm/health : {response.status_code}")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    
    response = requests.get(f"{BASE_URL}/docent/health")
    print(f"\nGET /docent/health : {response.status_code}")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))


def test_vlm_analyze(image_path: str = None):
    """Test VLM analyze endpoint"""
    print("\n=== VLM Analyze ===")
    
    if not image_path:
        print("Image path required for this test")
        return
    
    image_file = Path(image_path)
    if not image_file.exists():
        print(f"Image not found: {image_path}")
        return
    
    with open(image_file, 'rb') as f:
        image_bytes = f.read()
    
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
    
    payload = {
        "image": image_base64,
        "language": "ko"
    }
    
    print(f"Image: {image_file.name} ({len(image_bytes)} bytes)")
    print("Sending request...")
    
    response = requests.post(f"{BASE_URL}/vlm/analyze", json=payload)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"\nVLM Response: {result['vlm_response'][:200]}...")
        print(f"Image Hash: {result['image_hash'][:16]}...")
        print(f"Vector Matches: {len(result['vector_matches'])}")
        print(f"Confidence: {result['confidence_score']:.2f}")
        print(f"Processing Time: {result['processing_time_ms']}ms")
    else:
        print(f"Error: {response.text}")


def test_vlm_similar(image_path: str = None):
    """Test similar image search"""
    print("\n=== Similar Image Search ===")
    
    if not image_path:
        print("Image path required for this test")
        return
    
    image_file = Path(image_path)
    if not image_file.exists():
        print(f"Image not found: {image_path}")
        return
    
    with open(image_file, 'rb') as f:
        image_bytes = f.read()
    
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
    
    payload = {
        "image": image_base64,
        "top_k": 3,
        "threshold": 0.7
    }
    
    print(f"Image: {image_file.name}")
    response = requests.post(f"{BASE_URL}/vlm/similar", json=payload)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"\nMatches: {result['count']}")
        for i, match in enumerate(result['matches'], 1):
            print(f"{i}. {match['metadata'].get('place_name')} (similarity: {match['similarity']:.2f})")
    else:
        print(f"Error: {response.text}")


def test_docent_chat():
    """Test docent chat"""
    print("\n=== Docent Chat ===")
    
    payload = {
        "landmark": "경복궁",
        "user_message": "근정전에 대해 알려줘",
        "language": "ko"
    }
    
    response = requests.post(f"{BASE_URL}/docent/chat", json=payload)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"\nLandmark: {result['landmark']}")
        print(f"Message: {result['message']}")
    else:
        print(f"Error: {response.text}")


def test_docent_quiz():
    """Test quiz generation"""
    print("\n=== Docent Quiz ===")
    
    payload = {
        "landmark": "경복궁",
        "language": "ko"
    }
    
    response = requests.post(f"{BASE_URL}/docent/quiz", json=payload)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"\nQuestion: {result['question']}")
        for i, option in enumerate(result['options']):
            marker = "✓" if i == result.get('correct_answer') else " "
            print(f"  [{marker}] {i}. {option}")
        if 'explanation' in result:
            print(f"Explanation: {result['explanation']}")
    else:
        print(f"Error: {response.text}")


def test_tts():
    """Test TTS generation"""
    print("\n=== TTS ===")
    
    payload = {
        "text": "안녕하세요. 경복궁에 오신 것을 환영합니다.",
        "language_code": "ko-KR"
    }
    
    response = requests.post(f"{BASE_URL}/docent/tts", json=payload)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"\nFormat: {result['format']}")
        print(f"Size: {result['size_bytes']} bytes")
        print(f"Audio: {result['audio'][:50]}... (base64)")
    else:
        print(f"Error: {response.text}")


def test_recommend_health():
    """Test recommendation service health"""
    print("\n=== Recommendation Health ===")
    
    response = requests.get(f"{BASE_URL}/recommend/health")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"\nService Status: {result['status']}")
        print(f"CLIP Embedding: {'✓' if result['services']['clip_embedding'] else '✗'}")
        print(f"Pinecone: {'✓' if result['services']['pinecone'] else '✗'}")
        
        if result.get('pinecone_stats'):
            stats = result['pinecone_stats']
            print(f"\nPinecone Stats:")
            print(f"  - Total Vectors: {stats['total_vectors']}")
            print(f"  - Dimension: {stats['dimension']}")
    else:
        print(f"Error: {response.text}")


def test_recommend_categories():
    """Test get categories"""
    print("\n=== Recommendation Categories ===")
    
    response = requests.get(f"{BASE_URL}/recommend/categories")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n사용 가능한 카테고리: {result['count']}개")
        for cat in result['categories']:
            print(f"  - {cat['name']} ({cat['name_en']})")
            print(f"    유사: {', '.join(cat['similar_to'])}")
    else:
        print(f"Error: {response.text}")


def test_recommend_places(image_path: str = None, category: str = "역사유적"):
    """Test place recommendation"""
    print("\n=== Place Recommendation ===")
    
    if not image_path:
        print("Image path required for this test")
        return
    
    image_file = Path(image_path)
    if not image_file.exists():
        print(f"Image not found: {image_path}")
        return
    
    with open(image_file, 'rb') as f:
        image_bytes = f.read()
    
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
    
    payload = {
        "image": image_base64,
        "category": category,
        "top_k": 5,
        "threshold": 0.7,
        "context": "search",
        "gps": {
            "latitude": 37.5665,
            "longitude": 126.9780
        }
    }
    
    print(f"Image: {image_file.name} ({len(image_bytes)} bytes)")
    print(f"Category: {category}")
    print("Sending request...")
    
    response = requests.post(f"{BASE_URL}/recommend/recommend", json=payload, timeout=30)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        
        if not result.get('success'):
            print(f"\n{result.get('message', 'Recommendation failed')}")
            return
        
        print(f"\n✓ Found {result['count']} recommendations")
        print(f"Processing Time: {result.get('processing_time_ms', 0)}ms\n")
        
        for i, rec in enumerate(result['recommendations'], 1):
            print(f"{i}. {rec['name']} ({rec.get('name_en', '')})")
            print(f"   - Category: {rec['category']}")
            print(f"   - Image Similarity: {rec['image_similarity']:.3f}")
            print(f"   - Category Match: {rec['category_match']:.3f}")
            print(f"   - Final Score: {rec['final_score']:.3f}")
            
            if 'distance_km' in rec:
                print(f"   - Distance: {rec['distance_km']} km")
            
            location = rec['location']
            print(f"   - Location: ({location['latitude']}, {location['longitude']})")
            print()
    else:
        print(f"Error: {response.text}")


def test_recommend_similar(place_id: str = "place-001-gyeongbokgung"):
    """Test similar places recommendation"""
    print("\n=== Similar Places ===")
    
    payload = {
        "place_id": place_id,
        "top_k": 3,
        "threshold": 0.7
    }
    
    print(f"Place ID: {place_id}")
    
    response = requests.post(f"{BASE_URL}/recommend/similar", json=payload, timeout=10)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        
        if not result.get('success'):
            print(f"\nError: {result.get('error', 'Unknown error')}")
            return
        
        source = result['source_place']
        print(f"\n✓ Source: {source['name']} ({source['category']})")
        print(f"Processing Time: {result.get('processing_time_ms', 0)}ms\n")
        
        print(f"Similar Places ({result['count']}):")
        for i, rec in enumerate(result['recommendations'], 1):
            print(f"{i}. {rec['name']} ({rec.get('name_en', '')})")
            print(f"   - Category: {rec['category']}")
            print(f"   - Similarity: {rec['similarity']:.3f}")
            location = rec['location']
            print(f"   - Location: ({location['latitude']}, {location['longitude']})")
            print()
    elif response.status_code == 404:
        print(f"\nError: Place not found")
    else:
        print(f"Error: {response.text}")


def main():
    """Run all tests"""
    import argparse
    
    parser = argparse.ArgumentParser(description="API Test Script")
    parser.add_argument("--health", action="store_true", help="Test health endpoints")
    parser.add_argument("--vlm", type=str, help="Test VLM analyze (provide image path)")
    parser.add_argument("--similar", type=str, help="Test similar search (provide image path)")
    parser.add_argument("--chat", action="store_true", help="Test docent chat")
    parser.add_argument("--quiz", action="store_true", help="Test quiz generation")
    parser.add_argument("--tts", action="store_true", help="Test TTS")
    parser.add_argument("--recommend-health", action="store_true", help="Test recommendation health")
    parser.add_argument("--recommend-categories", action="store_true", help="Test recommendation categories")
    parser.add_argument("--recommend", type=str, help="Test place recommendation (provide image path)")
    parser.add_argument("--recommend-category", default="역사유적", help="Category for recommendation (default: 역사유적)")
    parser.add_argument("--recommend-similar", type=str, help="Test similar places (provide place_id)")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL")
    
    args = parser.parse_args()
    
    global BASE_URL
    BASE_URL = args.url
    
    print(f"Testing API at: {BASE_URL}")
    
    try:
        if args.all:
            test_health()
            test_docent_chat()
            test_docent_quiz()
            test_tts()
            test_recommend_health()
            test_recommend_categories()
            print("\nNote: Image-based tests require image path (use --vlm, --similar, --recommend)")
        elif args.health:
            test_health()
        elif args.vlm:
            test_vlm_analyze(args.vlm)
        elif args.similar:
            test_vlm_similar(args.similar)
        elif args.chat:
            test_docent_chat()
        elif args.quiz:
            test_docent_quiz()
        elif args.tts:
            test_tts()
        elif args.recommend_health:
            test_recommend_health()
        elif args.recommend_categories:
            test_recommend_categories()
        elif args.recommend:
            test_recommend_places(args.recommend, args.recommend_category)
        elif args.recommend_similar:
            test_recommend_similar(args.recommend_similar)
        else:
            parser.print_help()
    
    except requests.exceptions.ConnectionError:
        print(f"\nError: Cannot connect to {BASE_URL}")
        print("Make sure the server is running: python main.py")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted")
        sys.exit(0)


if __name__ == "__main__":
    main()
