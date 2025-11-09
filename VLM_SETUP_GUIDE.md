# VLM 이미지 분석 시스템 설정 가이드

## 환경 설정

### 필수 패키지 설치

```bash
pip install -r requirements.txt
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

### 환경 변수 (.env)

```bash
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-key

# OpenAI GPT-4V (필수)
OPENAI_API_KEY=sk-...

# Google Gemini (설명 보강용)
GEMINI_API_KEY=your-gemini-api-key

# Google Cloud TTS
GOOGLE_APPLICATION_CREDENTIALS=./google-tts-credentials.json

# 선택 사항
PRELOAD_CLIP_MODEL=false
```

---

## 데이터베이스 설정

### 1. SQL 스키마 실행

Supabase Dashboard → SQL Editor에서 `sql/setup_vlm_schema.sql` 실행

### 2. 이미지 임베딩 생성

```bash
# 모든 장소의 이미지 임베딩 생성
python seed_image_vectors.py --all

# 상태 확인
python seed_image_vectors.py --status
```

---

## API 엔드포인트

### POST /vlm/analyze

AR 카메라 이미지 분석

**요청:**
```json
{
  "user_id": "user123",
  "image": "base64_encoded_string",
  "latitude": 37.5665,
  "longitude": 126.9780,
  "language": "ko",
  "prefer_url": true,
  "enable_tts": true,
  "use_cache": true
}
```

**응답:**
```json
{
  "success": true,
  "description": "이곳은 경복궁의 근정전입니다...",
  "place": {
    "id": "uuid",
    "name": "경복궁",
    "category": "역사유적"
  },
  "similar_places": [...],
  "confidence_score": 0.85,
  "audio_url": "https://..."
}
```

### POST /vlm/similar

유사 이미지 검색

```json
{
  "image": "base64_encoded_string",
  "limit": 3,
  "threshold": 0.7
}
```

### GET /vlm/places/nearby

GPS 기반 주변 장소 조회

```
GET /vlm/places/nearby?latitude=37.5665&longitude=126.9780&radius_km=1.0
```

### GET /vlm/health

서비스 상태 확인

```json
{
  "status": "healthy",
  "services": {
    "gpt4v": true,
    "clip": true
  }
}
```

---

## 테스트

```bash
# Health check
python test_vlm.py --health

# 이미지 분석
python test_vlm.py --analyze image.jpg --lat 37.5796 --lon 126.9770 --tts

# 유사 이미지 검색
python test_vlm.py --similar image.jpg
```
