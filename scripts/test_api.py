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
            if len(sys.argv) > 2:
                print("\nNote: VLM tests require image path (use --vlm or --similar)")
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
