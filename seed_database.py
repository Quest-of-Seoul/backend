"""
Seed database with sample quests and rewards
"""
import os
from dotenv import load_dotenv
from services.db import get_db

# Load environment variables
load_dotenv()

print("[*] Connecting to Supabase...")
db = get_db()

# Sample quests data
quests_data = [
    {
        "name": "경복궁 (Gyeongbokgung Palace)",
        "description": "조선왕조의 법궁으로, 서울의 대표적인 역사 유적지입니다.",
        "lat": 37.5796,
        "lon": 126.9770,
        "reward_point": 100
    },
    {
        "name": "남산타워 (N Seoul Tower)",
        "description": "서울의 상징적인 랜드마크로, 도시 전경을 한눈에 볼 수 있습니다.",
        "lat": 37.5512,
        "lon": 126.9882,
        "reward_point": 150
    },
    {
        "name": "명동 (Myeongdong)",
        "description": "서울의 쇼핑과 먹거리의 중심지입니다.",
        "lat": 37.5636,
        "lon": 126.9865,
        "reward_point": 80
    },
    {
        "name": "인사동 (Insadong)",
        "description": "전통 문화와 예술이 살아있는 거리입니다.",
        "lat": 37.5730,
        "lon": 126.9856,
        "reward_point": 90
    },
    {
        "name": "홍대 (Hongdae)",
        "description": "젊음과 문화가 넘치는 예술의 거리입니다.",
        "lat": 37.5563,
        "lon": 126.9236,
        "reward_point": 70
    }
]

# Sample rewards data
rewards_data = [
    {
        "name": "서울 여행 뱃지",
        "type": "badge",
        "point_cost": 50,
        "description": "첫 퀘스트 완료 기념 뱃지",
        "is_active": True
    },
    {
        "name": "카페 할인 쿠폰",
        "type": "coupon",
        "point_cost": 100,
        "description": "서울 내 제휴 카페 20% 할인",
        "is_active": True
    },
    {
        "name": "경복궁 입장권",
        "type": "coupon",
        "point_cost": 200,
        "description": "경복궁 무료 입장권",
        "is_active": True
    },
    {
        "name": "서울 투어 마스터 뱃지",
        "type": "badge",
        "point_cost": 500,
        "description": "모든 퀘스트 완료 기념 뱃지",
        "is_active": True
    },
    {
        "name": "한복 체험 쿠폰",
        "type": "coupon",
        "point_cost": 300,
        "description": "한복 대여 50% 할인",
        "is_active": True
    }
]

try:
    # Check if quests already exist
    existing_quests = db.table("quests").select("id").execute()
    if existing_quests.data:
        print(f"[INFO] Found {len(existing_quests.data)} existing quests. Skipping quest insertion.")
    else:
        print("[*] Inserting sample quests...")
        result = db.table("quests").insert(quests_data).execute()
        print(f"[OK] Inserted {len(result.data)} quests successfully!")

    # Check if rewards already exist
    existing_rewards = db.table("rewards").select("id").execute()
    if existing_rewards.data:
        print(f"[INFO] Found {len(existing_rewards.data)} existing rewards. Skipping reward insertion.")
    else:
        print("[*] Inserting sample rewards...")
        result = db.table("rewards").insert(rewards_data).execute()
        print(f"[OK] Inserted {len(result.data)} rewards successfully!")

    # Verify data
    print("\n[TEST] Verifying inserted data...")
    all_quests = db.table("quests").select("*").execute()
    all_rewards = db.table("rewards").select("*").execute()

    print(f"[OK] Total quests in database: {len(all_quests.data)}")
    print(f"[OK] Total rewards in database: {len(all_rewards.data)}")

    print("\n[DONE] Database seeding completed!")
    print("You can now use the app to see quests on the map!")

except Exception as e:
    print(f"[ERROR] Error seeding database: {e}")
    import traceback
    traceback.print_exc()
