#!/usr/bin/env python3
"""Comprehensive API Test Script"""

import requests
import base64
import json
import sys
from pathlib import Path

BASE_URL = "http://localhost:8000"
TEST_USER_ID = "test-user-001"


def test_root():
    print("\n=== Root Endpoint ===")
    response = requests.get(f"{BASE_URL}/")
    print(f"GET / : {response.status_code}")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))


def test_health():
    print("\n=== Health Check ===")
    
    response = requests.get(f"{BASE_URL}/health")
    print(f"GET /health : {response.status_code}")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    
    response = requests.get(f"{BASE_URL}/vlm/health")
    print(f"\nGET /vlm/health : {response.status_code}")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))


def test_docent_chat():
    print("\n=== Docent Chat ===")
    
    payload = {
        "user_id": TEST_USER_ID,
        "landmark": "경복궁",
        "user_message": "근정전에 대해 알려줘",
        "language": "ko",
        "enable_tts": False
    }
    
    response = requests.post(f"{BASE_URL}/docent/chat", json=payload)
    print(f"POST /docent/chat : {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Landmark: {result['landmark']}")
        print(f"Message: {result['message'][:100]}...")
    else:
        print(f"Error: {response.text}")


def test_docent_quiz():
    print("\n=== Docent Quiz ===")
    
    params = {"landmark": "경복궁", "language": "ko"}
    
    response = requests.post(f"{BASE_URL}/docent/quiz", params=params)
    print(f"POST /docent/quiz : {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Question: {result['question']}")
        for i, option in enumerate(result['options']):
            print(f"  {i}. {option}")
    else:
        print(f"Error: {response.text}")


def test_docent_tts():
    print("\n=== Docent TTS ===")
    
    payload = {
        "text": "안녕하세요. 경복궁에 오신 것을 환영합니다.",
        "language_code": "ko-KR",
        "prefer_url": False
    }
    
    response = requests.post(f"{BASE_URL}/docent/tts", json=payload)
    print(f"POST /docent/tts : {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Audio: {len(result.get('audio', ''))} chars (base64)")
    else:
        print(f"Error: {response.text}")


def test_docent_history():
    print("\n=== Docent History ===")
    
    response = requests.get(f"{BASE_URL}/docent/history/{TEST_USER_ID}?limit=5")
    print(f"GET /docent/history/{{user_id}} : {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"History count: {len(result.get('history', []))}")
    else:
        print(f"Error: {response.text}")


def test_quest_list():
    print("\n=== Quest List ===")
    
    response = requests.get(f"{BASE_URL}/quest/list")
    print(f"GET /quest/list : {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Total quests: {len(result.get('quests', []))}")
        if result.get('quests'):
            quest = result['quests'][0]
            print(f"Sample: {quest.get('name')} at ({quest.get('lat')}, {quest.get('lon')})")
    else:
        print(f"Error: {response.text}")


def test_quest_nearby():
    print("\n=== Quest Nearby ===")
    
    payload = {
        "lat": 37.5796,
        "lon": 126.9770,
        "radius_km": 2.0
    }
    
    response = requests.post(f"{BASE_URL}/quest/nearby", json=payload)
    print(f"POST /quest/nearby : {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Nearby quests: {result.get('count', 0)}")
        if result.get('quests'):
            for quest in result['quests'][:3]:
                print(f"  - {quest.get('name')} ({quest.get('distance_km')} km)")
    else:
        print(f"Error: {response.text}")


def test_quest_progress():
    print("\n=== Quest Progress ===")
    
    payload = {
        "user_id": TEST_USER_ID,
        "quest_id": 1,
        "status": "in_progress"
    }
    
    response = requests.post(f"{BASE_URL}/quest/progress", json=payload)
    print(f"POST /quest/progress : {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Status: {result.get('status')}")
        print(f"Message: {result.get('message')}")
    else:
        print(f"Error: {response.text}")


def test_quest_user():
    print("\n=== Quest User ===")
    
    response = requests.get(f"{BASE_URL}/quest/user/{TEST_USER_ID}")
    print(f"GET /quest/user/{{user_id}} : {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"User quests: {len(result.get('quests', []))}")
    else:
        print(f"Error: {response.text}")


def test_quest_detail():
    print("\n=== Quest Detail ===")
    
    response = requests.get(f"{BASE_URL}/quest/1")
    print(f"GET /quest/{{quest_id}} : {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Quest: {result.get('name')}")
        print(f"Reward: {result.get('reward_point')} points")
    else:
        print(f"Error: {response.text}")


def test_reward_points():
    print("\n=== Reward Points ===")
    
    response = requests.get(f"{BASE_URL}/reward/points/{TEST_USER_ID}")
    print(f"GET /reward/points/{{user_id}} : {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Total points: {result.get('total_points', 0)}")
        print(f"Transactions: {len(result.get('transactions', []))}")
    else:
        print(f"Error: {response.text}")


def test_reward_add_points():
    print("\n=== Reward Add Points ===")
    
    payload = {
        "user_id": TEST_USER_ID,
        "points": 50,
        "reason": "Test points"
    }
    
    response = requests.post(f"{BASE_URL}/reward/points/add", json=payload)
    print(f"POST /reward/points/add : {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Status: {result.get('status')}")
        print(f"New balance: {result.get('new_balance')}")
    else:
        print(f"Error: {response.text}")


def test_reward_list():
    print("\n=== Reward List ===")
    
    response = requests.get(f"{BASE_URL}/reward/list")
    print(f"GET /reward/list : {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Available rewards: {len(result.get('rewards', []))}")
        if result.get('rewards'):
            reward = result['rewards'][0]
            print(f"Sample: {reward.get('name')} ({reward.get('point_cost')} points)")
    else:
        print(f"Error: {response.text}")


def test_reward_claimed():
    print("\n=== Reward Claimed ===")
    
    response = requests.get(f"{BASE_URL}/reward/claimed/{TEST_USER_ID}")
    print(f"GET /reward/claimed/{{user_id}} : {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Claimed rewards: {len(result.get('claimed_rewards', []))}")
    else:
        print(f"Error: {response.text}")


def test_reward_claim():
    print("\n=== Reward Claim ===")
    
    payload = {
        "user_id": TEST_USER_ID,
        "reward_id": 1
    }
    
    response = requests.post(f"{BASE_URL}/reward/claim", json=payload)
    print(f"POST /reward/claim : {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Status: {result.get('status')}")
        print(f"Message: {result.get('message')}")
        if result.get('status') == 'success':
            print(f"QR Code: {result.get('qr_code')}")
            print(f"Remaining Points: {result.get('remaining_points')}")
    else:
        print(f"Error: {response.text}")


def test_reward_use():
    print("\n=== Reward Use ===")
    
    params = {"user_id": TEST_USER_ID}
    
    response = requests.post(f"{BASE_URL}/reward/use/1", params=params)
    print(f"POST /reward/use/{{reward_id}} : {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Status: {result.get('status')}")
        print(f"Message: {result.get('message')}")
    else:
        print(f"Error: {response.text}")


def test_vlm_analyze(image_path: str = None):
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
        "user_id": TEST_USER_ID,
        "image": image_base64,
        "latitude": 37.5796,
        "longitude": 126.9770,
        "language": "ko",
        "enable_tts": False,
        "prefer_url": False
    }
    
    print(f"Image: {image_file.name} ({len(image_bytes)} bytes)")
    print("Analyzing...")
    
    response = requests.post(f"{BASE_URL}/vlm/analyze", json=payload, timeout=60)
    print(f"POST /vlm/analyze : {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Description: {result['description'][:100]}...")
        print(f"Confidence: {result.get('confidence_score', 0):.2f}")
        print(f"Processing Time: {result.get('processing_time_ms', 0)}ms")
        if result.get('place'):
            print(f"Matched Place: {result['place'].get('name')}")
    else:
        print(f"Error: {response.text}")


def test_vlm_similar(image_path: str = None):
    print("\n=== VLM Similar ===")
    
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
        "limit": 3,
        "threshold": 0.7
    }
    
    response = requests.post(f"{BASE_URL}/vlm/similar", json=payload)
    print(f"POST /vlm/similar : {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Similar images: {result.get('count', 0)}")
    else:
        print(f"Error: {response.text}")


def test_vlm_nearby_places():
    print("\n=== VLM Nearby Places ===")
    
    params = {
        "latitude": 37.5796,
        "longitude": 126.9770,
        "radius_km": 1.0,
        "limit": 5
    }
    
    response = requests.get(f"{BASE_URL}/vlm/places/nearby", params=params)
    print(f"GET /vlm/places/nearby : {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Nearby places: {result.get('count', 0)}")
    else:
        print(f"Error: {response.text}")


def test_recommend_similar_places(image_path: str = None):
    print("\n=== Recommend Similar Places ===")
    
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
        "user_id": TEST_USER_ID,
        "image": image_base64,
        "latitude": 37.5796,
        "longitude": 126.9770,
        "radius_km": 5.0,
        "limit": 5,
        "quest_only": True
    }
    
    print(f"Image: {image_file.name}")
    
    response = requests.post(f"{BASE_URL}/recommend/similar-places", json=payload, timeout=30)
    print(f"POST /recommend/similar-places : {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Recommendations: {result.get('count', 0)}")
    else:
        print(f"Error: {response.text}")


def test_recommend_nearby_quests():
    print("\n=== Recommend Nearby Quests ===")
    
    params = {
        "latitude": 37.5796,
        "longitude": 126.9770,
        "radius_km": 5.0,
        "limit": 10
    }
    
    response = requests.get(f"{BASE_URL}/recommend/nearby-quests", params=params)
    print(f"GET /recommend/nearby-quests : {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Nearby quests: {result.get('count', 0)}")
    else:
        print(f"Error: {response.text}")


def test_recommend_category():
    print("\n=== Recommend Category ===")
    
    response = requests.get(f"{BASE_URL}/recommend/quests/category/역사유적?limit=10")
    print(f"GET /recommend/quests/category/{{category}} : {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Places in category: {result.get('count', 0)}")
    else:
        print(f"Error: {response.text}")


def test_recommend_stats():
    print("\n=== Recommend Stats ===")
    
    response = requests.get(f"{BASE_URL}/recommend/stats")
    print(f"GET /recommend/stats : {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Total places: {result.get('total_places', 0)}")
        print(f"Total quests: {result.get('total_quests', 0)}")
        print(f"Total vectors: {result.get('total_vectors', 0)}")
    else:
        print(f"Error: {response.text}")


def test_recommend_quest_detail():
    print("\n=== Recommend Quest Detail ===")
    
    quest_id = "1"
    
    response = requests.get(f"{BASE_URL}/recommend/quests/{quest_id}")
    print(f"GET /recommend/quests/{{quest_id}} : {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Success: {result.get('success')}")
        if result.get('quest'):
            print(f"Quest: {result['quest'].get('name')}")
        if result.get('quizzes'):
            print(f"Quizzes: {len(result['quizzes'])}")
    else:
        print(f"Error: {response.text}")


def test_recommend_submit():
    print("\n=== Recommend Quiz Submit ===")
    
    quest_id = "1"
    params = {
        "user_id": TEST_USER_ID,
        "quiz_id": "1",
        "answer": 1
    }
    
    response = requests.post(f"{BASE_URL}/recommend/quests/{quest_id}/submit", params=params)
    print(f"POST /recommend/quests/{{quest_id}}/submit : {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Success: {result.get('success')}")
        print(f"Is Correct: {result.get('is_correct')}")
        if result.get('explanation'):
            print(f"Explanation: {result['explanation'][:50]}...")
    else:
        print(f"Error: {response.text}")


def test_vlm_health():
    print("\n=== VLM Health ===")
    
    response = requests.get(f"{BASE_URL}/vlm/health")
    print(f"GET /vlm/health : {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Status: {result.get('status')}")
        if result.get('services'):
            print(f"Services: {result['services']}")
    else:
        print(f"Error: {response.text}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="API Test Script")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL")
    parser.add_argument("--image", type=str, help="Image path for image-based tests")
    
    parser.add_argument("--root", action="store_true", help="Test root endpoint")
    parser.add_argument("--health", action="store_true", help="Test health endpoints")
    
    parser.add_argument("--docent", action="store_true", help="Test all docent endpoints")
    parser.add_argument("--docent-chat", action="store_true", help="Test docent chat")
    parser.add_argument("--docent-quiz", action="store_true", help="Test docent quiz")
    parser.add_argument("--docent-tts", action="store_true", help="Test docent TTS")
    parser.add_argument("--docent-history", action="store_true", help="Test docent history")
    
    parser.add_argument("--quest", action="store_true", help="Test all quest endpoints")
    parser.add_argument("--quest-list", action="store_true", help="Test quest list")
    parser.add_argument("--quest-nearby", action="store_true", help="Test quest nearby")
    parser.add_argument("--quest-progress", action="store_true", help="Test quest progress")
    parser.add_argument("--quest-user", action="store_true", help="Test quest user")
    parser.add_argument("--quest-detail", action="store_true", help="Test quest detail")
    
    parser.add_argument("--reward", action="store_true", help="Test all reward endpoints")
    parser.add_argument("--reward-points", action="store_true", help="Test reward points")
    parser.add_argument("--reward-add", action="store_true", help="Test reward add points")
    parser.add_argument("--reward-list", action="store_true", help="Test reward list")
    parser.add_argument("--reward-claimed", action="store_true", help="Test reward claimed")
    parser.add_argument("--reward-claim", action="store_true", help="Test reward claim")
    parser.add_argument("--reward-use", action="store_true", help="Test reward use")
    
    parser.add_argument("--vlm", action="store_true", help="Test all VLM endpoints (requires --image)")
    parser.add_argument("--vlm-analyze", action="store_true", help="Test VLM analyze")
    parser.add_argument("--vlm-similar", action="store_true", help="Test VLM similar")
    parser.add_argument("--vlm-nearby", action="store_true", help="Test VLM nearby places")
    parser.add_argument("--vlm-health", action="store_true", help="Test VLM health")
    
    parser.add_argument("--recommend", action="store_true", help="Test all recommend endpoints")
    parser.add_argument("--recommend-places", action="store_true", help="Test recommend places")
    parser.add_argument("--recommend-quests", action="store_true", help="Test recommend quests")
    parser.add_argument("--recommend-category", action="store_true", help="Test recommend category")
    parser.add_argument("--recommend-quest-detail", action="store_true", help="Test recommend quest detail")
    parser.add_argument("--recommend-submit", action="store_true", help="Test recommend quiz submit")
    parser.add_argument("--recommend-stats", action="store_true", help="Test recommend stats")
    
    parser.add_argument("--all", action="store_true", help="Run all non-image tests")
    parser.add_argument("--full", action="store_true", help="Run ALL tests (requires --image)")
    
    args = parser.parse_args()
    
    global BASE_URL
    BASE_URL = args.url
    
    print(f"Testing API at: {BASE_URL}")
    print(f"Test User ID: {TEST_USER_ID}\n")
    
    try:
        if args.full:
            if not args.image:
                print("Error: --full requires --image parameter")
                sys.exit(1)
            test_root()
            test_health()
            test_docent_chat()
            test_docent_quiz()
            test_docent_tts()
            test_docent_history()
            test_quest_list()
            test_quest_nearby()
            test_quest_progress()
            test_quest_user()
            test_quest_detail()
            test_reward_points()
            test_reward_add_points()
            test_reward_list()
            test_reward_claimed()
            test_reward_claim()
            test_reward_use()
            test_vlm_analyze(args.image)
            test_vlm_similar(args.image)
            test_vlm_nearby_places()
            test_vlm_health()
            test_recommend_similar_places(args.image)
            test_recommend_nearby_quests()
            test_recommend_category()
            test_recommend_quest_detail()
            test_recommend_submit()
            test_recommend_stats()
        elif args.all:
            test_root()
            test_health()
            test_docent_chat()
            test_docent_quiz()
            test_docent_tts()
            test_docent_history()
            test_quest_list()
            test_quest_nearby()
            test_quest_progress()
            test_quest_user()
            test_quest_detail()
            test_reward_points()
            test_reward_add_points()
            test_reward_list()
            test_reward_claimed()
            test_reward_claim()
            test_reward_use()
            test_vlm_nearby_places()
            test_vlm_health()
            test_recommend_nearby_quests()
            test_recommend_category()
            test_recommend_quest_detail()
            test_recommend_submit()
            test_recommend_stats()
        else:
            if args.root:
                test_root()
            if args.health:
                test_health()
            
            if args.docent:
                test_docent_chat()
                test_docent_quiz()
                test_docent_tts()
                test_docent_history()
            else:
                if args.docent_chat:
                    test_docent_chat()
                if args.docent_quiz:
                    test_docent_quiz()
                if args.docent_tts:
                    test_docent_tts()
                if args.docent_history:
                    test_docent_history()
            
            if args.quest:
                test_quest_list()
                test_quest_nearby()
                test_quest_progress()
                test_quest_user()
                test_quest_detail()
            else:
                if args.quest_list:
                    test_quest_list()
                if args.quest_nearby:
                    test_quest_nearby()
                if args.quest_progress:
                    test_quest_progress()
                if args.quest_user:
                    test_quest_user()
                if args.quest_detail:
                    test_quest_detail()
            
            if args.reward:
                test_reward_points()
                test_reward_add_points()
                test_reward_list()
                test_reward_claimed()
                test_reward_claim()
                test_reward_use()
            else:
                if args.reward_points:
                    test_reward_points()
                if args.reward_add:
                    test_reward_add_points()
                if args.reward_list:
                    test_reward_list()
                if args.reward_claimed:
                    test_reward_claimed()
                if args.reward_claim:
                    test_reward_claim()
                if args.reward_use:
                    test_reward_use()
            
            if args.vlm:
                if not args.image:
                    print("Error: --vlm requires --image parameter")
                    sys.exit(1)
                test_vlm_analyze(args.image)
                test_vlm_similar(args.image)
                test_vlm_nearby_places()
                test_vlm_health()
            else:
                if args.vlm_analyze:
                    test_vlm_analyze(args.image)
                if args.vlm_similar:
                    test_vlm_similar(args.image)
                if args.vlm_nearby:
                    test_vlm_nearby_places()
                if args.vlm_health:
                    test_vlm_health()
            
            if args.recommend:
                test_recommend_nearby_quests()
                test_recommend_category()
                test_recommend_quest_detail()
                test_recommend_submit()
                test_recommend_stats()
                if args.image:
                    test_recommend_similar_places(args.image)
            else:
                if args.recommend_places:
                    test_recommend_similar_places(args.image)
                if args.recommend_quests:
                    test_recommend_nearby_quests()
                if args.recommend_category:
                    test_recommend_category()
                if args.recommend_quest_detail:
                    test_recommend_quest_detail()
                if args.recommend_submit:
                    test_recommend_submit()
                if args.recommend_stats:
                    test_recommend_stats()
            
            if not any(vars(args).values()):
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
