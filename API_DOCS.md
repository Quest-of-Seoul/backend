# API Documentation

Quest of Seoul Backend API Reference

## Base URL

```
http://localhost:8000
```

Production: `https://your-domain.com`

## Authentication

현재 인증 없음 (향후 API Key 또는 JWT 추가 예정)

---

## Endpoints Overview

### Docent (AI 도슨트)
- POST `/docent/chat` - AI 도슨트 대화
- POST `/docent/quiz` - 퀴즈 생성
- POST `/docent/tts` - TTS 생성
- GET `/docent/history/{user_id}` - 대화 기록 조회
- WebSocket `/docent/ws/tts` - TTS 스트리밍
- WebSocket `/docent/ws/chat` - 채팅 스트리밍

### Quest (퀘스트 관리)
- GET `/quest/list` - 퀘스트 목록
- POST `/quest/nearby` - 주변 퀘스트 검색
- POST `/quest/progress` - 진행 상황 업데이트
- GET `/quest/user/{user_id}` - 사용자 퀘스트 조회
- GET `/quest/{quest_id}` - 퀘스트 상세 정보

### Reward (리워드 시스템)
- GET `/reward/points/{user_id}` - 포인트 조회
- POST `/reward/points/add` - 포인트 추가
- GET `/reward/list` - 리워드 목록
- POST `/reward/claim` - 리워드 획득
- GET `/reward/claimed/{user_id}` - 획득한 리워드 조회
- POST `/reward/use/{reward_id}` - 리워드 사용

### VLM (이미지 분석)
- POST `/vlm/analyze` - 이미지 분석
- POST `/vlm/analyze-multipart` - 멀티파트 이미지 분석
- POST `/vlm/similar` - 유사 이미지 검색
- POST `/vlm/embed` - 임베딩 생성 (관리자)
- GET `/vlm/places/nearby` - 주변 장소 조회
- GET `/vlm/health` - 서비스 상태 확인

### Recommend (추천 시스템)
- POST `/recommend/similar-places` - 장소 추천
- GET `/recommend/nearby-quests` - 주변 퀘스트 추천
- GET `/recommend/quests/category/{category}` - 카테고리별 퀘스트
- GET `/recommend/quests/{quest_id}` - 퀘스트 상세
- POST `/recommend/quests/{quest_id}/submit` - 퀴즈 제출
- GET `/recommend/stats` - 추천 시스템 통계

---

## Docent Endpoints

### POST /docent/chat

AI 도슨트와 대화

**Request Body:**

```json
{
  "user_id": "user-123",
  "landmark": "경복궁",
  "user_message": "근정전에 대해 알려줘",
  "language": "ko",
  "prefer_url": false,
  "enable_tts": true
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| user_id | string | 필수 | 사용자 ID |
| landmark | string | 필수 | 장소명 |
| user_message | string | 선택 | 사용자 질문 |
| language | string | 선택 | 언어 (ko/en, 기본: ko) |
| prefer_url | boolean | 선택 | 오디오 URL 선호 (기본: false) |
| enable_tts | boolean | 선택 | TTS 활성화 (기본: true) |

**Response:**

```json
{
  "message": "근정전은 경복궁의 정전으로...",
  "landmark": "경복궁",
  "audio": "base64_encoded_audio_or_null",
  "audio_url": "https://storage.url/audio.mp3_or_null"
}
```

**Status Codes:**
- 200: 성공
- 500: 서버 오류

---

### POST /docent/quiz

장소에 대한 퀴즈 생성

**Query Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| landmark | string | 필수 | 장소명 |
| language | string | 선택 | 언어 (ko/en, 기본: ko) |

**Response:**

```json
{
  "question": "경복궁은 몇 년에 창건되었나요?",
  "options": ["1392년", "1395년", "1400년", "1405년"],
  "correct_answer": 1,
  "explanation": "경복궁은 1395년에 창건되었습니다."
}
```

---

### POST /docent/tts

텍스트를 음성으로 변환

**Request Body:**

```json
{
  "text": "안녕하세요. 경복궁에 오신 것을 환영합니다.",
  "language_code": "ko-KR",
  "prefer_url": false
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| text | string | 필수 | 변환할 텍스트 |
| language_code | string | 선택 | 언어 코드 (기본: ko-KR) |
| prefer_url | boolean | 선택 | URL 반환 여부 (기본: false) |

**Response:**

```json
{
  "audio": "base64_encoded_audio",
  "audio_url": "https://storage.url/audio.mp3_or_null",
  "text": "안녕하세요. 경복궁에 오신 것을 환영합니다."
}
```

---

### GET /docent/history/{user_id}

사용자 대화 기록 조회

**Path Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| user_id | string | 필수 | 사용자 ID |

**Query Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| limit | integer | 선택 | 결과 개수 (기본: 10) |

**Response:**

```json
{
  "history": [
    {
      "id": 1,
      "user_id": "user-123",
      "landmark": "경복궁",
      "user_message": "근정전에 대해 알려줘",
      "ai_response": "근정전은...",
      "created_at": "2024-01-01T12:00:00Z"
    }
  ]
}
```

---

### WebSocket /docent/ws/tts

TTS 스트리밍

**Send Message:**

```json
{
  "text": "경복궁은 조선시대 법궁입니다.",
  "language_code": "ko-KR"
}
```

**Receive:** Binary audio chunks followed by "DONE" message

---

### WebSocket /docent/ws/chat

채팅 + TTS 스트리밍

**Send Message:**

```json
{
  "user_id": "user-123",
  "landmark": "경복궁",
  "user_message": "근정전에 대해 알려줘",
  "language": "ko",
  "enable_tts": true
}
```

**Receive:**
1. JSON message with text
2. Binary audio chunks (if TTS enabled)
3. "DONE" message

---

## Quest Endpoints

### GET /quest/list

모든 퀘스트 조회

**Response:**

```json
{
  "quests": [
    {
      "id": 1,
      "place_id": "13ac5471-b78b-4640-b3ff-e2e63d9055ed",
      "name": "Gyeongbokgung Palace",
      "title": null,
      "description": "The main royal palace of the Joseon Dynasty, built in 1395. You can admire beautiful traditional architecture including Geunjeongjeon Hall and Gyeonghoeru Pavilion.",
      "category": "Historic Site",
      "latitude": 37.579617,
      "longitude": 126.977041,
      "reward_point": 100,
      "points": 10,
      "difficulty": "easy",
      "is_active": true,
      "completion_count": 0,
      "created_at": "2025-11-22T10:14:30.222474",
      "district": "Jongno-gu",
      "place_image_url": "https://ak-d.tripcdn.com/images/0104p120008ars39uB986.webp"
    }
  ]
}
```

---

### POST /quest/nearby

주변 퀘스트 검색

**Request Body:**

```json
{
  "lat": 37.5665,
  "lon": 126.9780,
  "radius_km": 50.0
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| lat | float | 필수 | 위도 |
| lon | float | 필수 | 경도 |
| radius_km | float | 선택 | 검색 반경 (기본: 1.0) |

**Response:**

```json
{
  "quests": [
    {
      "quest_id": 1,
      "title": "경복궁",
      "latitude": 37.5796,
      "longitude": 126.9770,
      "category": "Heritage",
      "distance_km": 2.0,
      "reward_point": 500,
      "address": "서울특별시 종로구",
      "description": "..."
    }
  ],
  "count": 3
}
```

---

### POST /quest/progress

퀘스트 진행 상황 업데이트

**Request Body:**

```json
{
  "user_id": "user-123",
  "quest_id": 1,
  "status": "completed"
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| user_id | string | 필수 | 사용자 ID |
| quest_id | integer | 필수 | 퀘스트 ID |
| status | string | 필수 | 상태 (in_progress/completed/failed) |

**Response (완료 시):**

```json
{
  "status": "success",
  "message": "Quest completed!",
  "points_earned": 100
}
```

**Response (진행 중):**

```json
{
  "status": "success",
  "message": "Quest status updated to in_progress"
}
```

---

### GET /quest/user/{user_id}

사용자 퀘스트 조회

**Path Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| user_id | string | 필수 | 사용자 ID |

**Query Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| status | string | 선택 | 상태 필터 (in_progress/completed/failed) |

**Response:**

```json
{
  "quests": [
    {
      "id": 1,
      "user_id": "user-123",
      "quest_id": 1,
      "status": "completed",
      "started_at": "2024-01-01T10:00:00Z",
      "completed_at": "2024-01-01T11:00:00Z",
      "quests": {
        "name": "경복궁",
        "reward_point": 100
      }
    }
  ]
}
```

---

### GET /quest/{quest_id}

퀘스트 상세 정보

**Path Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| quest_id | integer | 필수 | 퀘스트 ID |

**Response:**

```json
{
  "id": 1,
  "name": "경복궁 (Gyeongbokgung Palace)",
  "description": "조선왕조의 법궁으로...",
  "lat": 37.5796,
  "lon": 126.9770,
  "reward_point": 100,
  "difficulty": "easy"
}
```

---

## Reward Endpoints

### GET /reward/points/{user_id}

사용자 포인트 조회

**Path Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| user_id | string | 필수 | 사용자 ID |

**Response:**

```json
{
  "total_points": 350,
  "transactions": [
    {
      "id": 1,
      "user_id": "user-123",
      "value": 100,
      "reason": "Completed quest: 경복궁",
      "created_at": "2024-01-01T12:00:00Z"
    }
  ]
}
```

---

### POST /reward/points/add

포인트 추가

**Request Body:**

```json
{
  "user_id": "user-123",
  "points": 50,
  "reason": "Quest completion"
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| user_id | string | 필수 | 사용자 ID |
| points | integer | 필수 | 포인트 (양수) |
| reason | string | 선택 | 사유 (기본: "Quest completion") |

**Response:**

```json
{
  "status": "success",
  "message": "Successfully added 50 points",
  "points_added": 50,
  "previous_balance": 300,
  "new_balance": 350,
  "reason": "Quest completion"
}
```

---

### GET /reward/list

사용 가능한 리워드 목록

**Response:**

```json
{
  "rewards": [
    {
      "id": 1,
      "name": "서울 여행 뱃지",
      "type": "badge",
      "point_cost": 50,
      "description": "첫 퀘스트 완료 기념 뱃지",
      "image_url": "https://...",
      "is_active": true
    }
  ]
}
```

---

### POST /reward/claim

리워드 획득

**Request Body:**

```json
{
  "user_id": "user-123",
  "reward_id": 1
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| user_id | string | 필수 | 사용자 ID |
| reward_id | integer | 필수 | 리워드 ID |

**Response (성공):**

```json
{
  "status": "success",
  "message": "Reward claimed successfully!",
  "reward": "서울 여행 뱃지",
  "qr_code": "abc123token",
  "remaining_points": 250
}
```

**Response (포인트 부족):**

```json
{
  "status": "fail",
  "message": "Not enough points",
  "required": 100,
  "current": 50,
  "shortage": 50
}
```

---

### GET /reward/claimed/{user_id}

획득한 리워드 조회

**Path Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| user_id | string | 필수 | 사용자 ID |

**Response:**

```json
{
  "claimed_rewards": [
    {
      "id": 1,
      "user_id": "user-123",
      "reward_id": 1,
      "claimed_at": "2024-01-01T12:00:00Z",
      "used_at": null,
      "qr_code": "abc123token",
      "rewards": {
        "name": "서울 여행 뱃지",
        "type": "badge"
      }
    }
  ]
}
```

---

### POST /reward/use/{reward_id}

리워드 사용 처리

**Path Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| reward_id | integer | 필수 | 리워드 ID |

**Query Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| user_id | string | 필수 | 사용자 ID |

**Response:**

```json
{
  "status": "success",
  "message": "Reward marked as used"
}
```

---

## VLM Endpoints

### POST /vlm/analyze

이미지 분석 및 장소 인식

**Request Body:**

```json
{
  "user_id": "user-123",
  "image": "base64_encoded_image",
  "latitude": 37.5796,
  "longitude": 126.9770,
  "language": "ko",
  "prefer_url": true,
  "enable_tts": true,
  "use_cache": true
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| user_id | string | 필수 | 사용자 ID |
| image | string | 필수 | Base64 인코딩 이미지 |
| latitude | float | 선택 | 위도 |
| longitude | float | 선택 | 경도 |
| language | string | 선택 | 언어 (ko/en, 기본: ko) |
| prefer_url | boolean | 선택 | 오디오 URL 선호 (기본: true) |
| enable_tts | boolean | 선택 | TTS 활성화 (기본: true) |
| use_cache | boolean | 선택 | 캐시 사용 (기본: true) |

**Response:**

```json
{
  "success": true,
  "description": "경복궁은 조선시대 법궁으로...",
  "place": {
    "id": "place-001",
    "name": "경복궁",
    "category": "역사유적",
    "address": "서울특별시 종로구 사직로 161"
  },
  "vlm_analysis": "Place Name: 경복궁...",
  "similar_places": [
    {
      "place_id": "place-001",
      "similarity": 0.95,
      "image_url": "https://..."
    }
  ],
  "confidence_score": 0.92,
  "processing_time_ms": 1250,
  "vlm_provider": "gpt4v",
  "audio_url": "https://storage.url/audio.mp3"
}
```

**Status Codes:**
- 200: 성공
- 400: 잘못된 이미지 형식
- 500: 서버 오류
- 503: AI 서비스 불가

---

### POST /vlm/analyze-multipart

멀티파트 폼 데이터로 이미지 분석

**Form Data:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| user_id | string | 필수 | 사용자 ID |
| image | file | 필수 | 이미지 파일 |
| latitude | float | 선택 | 위도 |
| longitude | float | 선택 | 경도 |
| language | string | 선택 | 언어 (기본: ko) |
| prefer_url | boolean | 선택 | 오디오 URL 선호 |
| enable_tts | boolean | 선택 | TTS 활성화 |

**Response:** `/vlm/analyze`와 동일

---

### POST /vlm/similar

유사 이미지 검색

**Request Body:**

```json
{
  "image": "base64_encoded_image",
  "limit": 3,
  "threshold": 0.7
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| image | string | 필수 | Base64 인코딩 이미지 |
| limit | integer | 선택 | 결과 개수 (기본: 3) |
| threshold | float | 선택 | 최소 유사도 (기본: 0.7) |

**Response:**

```json
{
  "success": true,
  "count": 3,
  "similar_images": [
    {
      "id": "vec-001",
      "place_id": "place-001",
      "image_url": "https://...",
      "similarity": 0.95,
      "place": {
        "id": "place-001",
        "name": "경복궁"
      }
    }
  ]
}
```

---

### POST /vlm/embed

이미지 임베딩 생성 및 저장 (관리자)

**Form Data:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| place_id | string | 필수 | 장소 ID |
| image | file | 필수 | 이미지 파일 |

**Response:**

```json
{
  "success": true,
  "vector_id": "550e8400-e29b-41d4-a716-446655440000",
  "place_id": "place-001",
  "image_url": "https://storage.url/image.jpg",
  "embedding_dimension": 512
}
```

---

### GET /vlm/places/nearby

주변 장소 조회

**Query Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| latitude | float | 필수 | 위도 |
| longitude | float | 필수 | 경도 |
| radius_km | float | 선택 | 검색 반경 (기본: 1.0) |
| limit | integer | 선택 | 결과 개수 (기본: 10) |

**Response:**

```json
{
  "success": true,
  "count": 5,
  "places": [
    {
      "id": "place-001",
      "name": "경복궁",
      "category": "역사유적",
      "distance_km": 0.15
    }
  ]
}
```

---

### GET /vlm/health

VLM 서비스 상태 확인

**Response:**

```json
{
  "status": "healthy",
  "services": {
    "gpt4v": true,
    "clip": true,
    "pinecone": true
  },
  "pinecone_stats": {
    "total_vectors": 150,
    "dimension": 512,
    "index_fullness": 0.05
  }
}
```

---

## Recommend Endpoints

### POST /recommend/similar-places

이미지 기반 장소 추천

**Request Body:**

```json
{
  "user_id": "user-123",
  "image": "base64_encoded_image",
  "latitude": 37.5796,
  "longitude": 126.9770,
  "radius_km": 5.0,
  "limit": 5,
  "quest_only": true
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| user_id | string | 필수 | 사용자 ID |
| image | string | 필수 | Base64 인코딩 이미지 |
| latitude | float | 선택 | 위도 |
| longitude | float | 선택 | 경도 |
| radius_km | float | 선택 | 검색 반경 (기본: 5.0) |
| limit | integer | 선택 | 결과 개수 (기본: 5) |
| quest_only | boolean | 선택 | 퀘스트 장소만 (기본: true) |

**Response:**

```json
{
  "success": true,
  "count": 3,
  "recommendations": [
    {
      "place_id": "place-001",
      "similarity": 0.92,
      "place": {
        "name": "경복궁",
        "category": "역사유적"
      }
    }
  ],
  "filter": {
    "gps_enabled": true,
    "radius_km": 5.0,
    "quest_only": true
  }
}
```

---

### GET /recommend/nearby-quests

주변 퀘스트 추천

**Query Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| latitude | float | 필수 | 위도 |
| longitude | float | 필수 | 경도 |
| radius_km | float | 선택 | 검색 반경 (기본: 5.0) |
| limit | integer | 선택 | 결과 개수 (기본: 10) |

**Response:**

```json
{
  "success": true,
  "count": 5,
  "quests": [
    {
      "place_id": "place-001",
      "place_name": "경복궁",
      "category": "역사유적",
      "distance_km": 0.5,
      "quest_id": 1,
      "quest_points": 100
    }
  ]
}
```

---

### GET /recommend/quests/category/{category}

카테고리별 퀘스트 조회

**Path Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| category | string | 필수 | 카테고리 (역사유적/관광지/문화마을 등) |

**Query Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| limit | integer | 선택 | 결과 개수 (기본: 20) |

**Response:**

```json
{
  "success": true,
  "category": "역사유적",
  "count": 10,
  "places": [
    {
      "id": "place-001",
      "name": "경복궁",
      "category": "역사유적"
    }
  ]
}
```

---

### GET /recommend/quests/{quest_id}

퀘스트 상세 정보 (장소 + 퀴즈 포함)

**Path Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| quest_id | string | 필수 | 퀘스트 ID |

**Response:**

```json
{
  "success": true,
  "quest": {
    "id": "quest-001",
    "place_id": "place-001",
    "name": "경복궁 탐험",
    "description": "경복궁의 역사를 알아보세요"
  },
  "place": {
    "id": "place-001",
    "name": "경복궁",
    "category": "역사유적"
  },
  "quizzes": [
    {
      "id": 1,
      "question": "경복궁은 몇 년에 창건되었나요?",
      "options": ["1392년", "1395년", "1400년", "1405년"],
      "correct_answer": 1,
      "hint": "조선 건국 후 3년",
      "points": 60,
      "explanation": "1395년에 창건되었습니다."
    }
  ]
}
```

---

### POST /recommend/quests/{quest_id}/submit

퀴즈 답안 제출

**Path Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| quest_id | string | 필수 | 퀘스트 ID |

**Query Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| user_id | string | 필수 | 사용자 ID |
| quiz_id | string | 필수 | 퀴즈 ID |
| answer | integer | 필수 | 답안 (0-3) |

**Response (정답):**

```json
{
  "success": true,
  "is_correct": true,
  "explanation": "정답입니다! 경복궁은 1395년에 창건되었습니다."
}
```

**Response (오답):**

```json
{
  "success": true,
  "is_correct": false
}
```

---

### GET /recommend/stats

추천 시스템 통계

**Response:**

```json
{
  "total_places": 150,
  "total_quests": 50,
  "total_vectors": 450,
  "vector_dimension": 512,
  "index_fullness": 0.05
}
```

---

## Error Responses

모든 에러는 다음 형식으로 반환:

```json
{
  "detail": "Error message here"
}
```

**Common Status Codes:**

- 200: 성공
- 400: 잘못된 요청 (Bad Request)
- 404: 리소스 없음 (Not Found)
- 500: 서버 내부 오류 (Internal Server Error)
- 503: 서비스 사용 불가 (Service Unavailable)

---

## Notes

### 이미지 처리
- 이미지는 Base64 인코딩 필요
- 최대 이미지 크기: 20MB
- 권장 크기: 5MB 이하
- 지원 형식: JPEG, PNG, WebP

### TTS
- 최대 텍스트 길이: 5000자
- 지원 언어: ko-KR, en-US
- 출력 형식: MP3 (24kHz)

### 벡터 검색
- 임베딩 차원: 512
- 유사도 메트릭: Cosine Similarity
- 임계값 범위: 0.0 ~ 1.0

### WebSocket
- 연결 후 JSON 메시지 전송
- 스트리밍 완료 시 "DONE" 메시지 수신
- 에러 시 JSON 에러 메시지 수신

---

## Swagger UI

대화형 API 문서: **http://localhost:8000/docs**

ReDoc: **http://localhost:8000/redoc**
