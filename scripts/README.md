# API Test Scripts

## test_api.py

모든 API 엔드포인트를 테스트하는 스크립트

### 사용법

```bash
# 서버 실행 확인
python scripts/test_api.py --health

# 도슨트 채팅 테스트
python scripts/test_api.py --chat

# 퀴즈 생성 테스트
python scripts/test_api.py --quiz

# TTS 테스트
python scripts/test_api.py --tts

# VLM 이미지 분석 (이미지 경로 필요)
python scripts/test_api.py --vlm scripts/test_images/mydo_cathedral1.jpg

# 유사 이미지 검색 (이미지 경로 필요)
python scripts/test_api.py --similar scripts/test_images/mydo_cathedral1.jpg

# 모든 테스트 실행 (이미지 제외)
python scripts/test_api.py --all

# 다른 서버 URL 지정
python scripts/test_api.py --health --url http://production-url.com
```

### 필요 조건

- 서버가 실행 중이어야 함
- VLM 테스트는 이미지 파일 필요
