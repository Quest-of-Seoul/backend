"""
Test docent API
"""
import requests
import json

url = "http://localhost:8000/docent/chat"
data = {
    "user_id": "9f88bbf5-4c6f-47f7-88dd-12fb03d2e90f",  # Valid UUID
    "landmark": "경복궁",
    "user_message": "안녕하세요",
    "language": "ko"
}

print("Testing docent chat API...")
print(f"URL: {url}")
print(f"Request data: {json.dumps(data, ensure_ascii=False)}")

try:
    response = requests.post(url, json=data, timeout=30)
    print(f"\nStatus code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
