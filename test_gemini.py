"""
Test Gemini API directly
"""
import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
print(f"API Key: {api_key[:20]}..." if api_key else "No API key found")

try:
    print("\n[*] Configuring Gemini...")
    genai.configure(api_key=api_key)

    print("[*] Listing available models...")
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"  - {m.name}")

    print("\n[*] Trying gemini-2.5-flash model...")
    model = genai.GenerativeModel('gemini-2.5-flash')

    print("[*] Generating test response...")
    response = model.generate_content("안녕하세요, 경복궁에 대해 간단히 설명해주세요.")

    print(f"\n[OK] Response received:")
    print(response.text)

except Exception as e:
    print(f"\n[ERROR] Failed: {e}")
    import traceback
    traceback.print_exc()
