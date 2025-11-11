# API Documentation

Quest of Seoul AI Service API Reference

## Base URL

```
http://localhost:8000
```

Production: `https://your-domain.com`

## Authentication

현재 인증 없음 (향후 API Key 또는 JWT 추가 예정)

## Endpoints

### VLM - Image Analysis

#### POST /vlm/analyze

이미지를 분석하여 장소 정보 반환

**Request Body:**

```json
{
  "image": "base64_encoded_image_string",
  "language": "ko"
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| image | string | ✅ | Base64 인코딩된 이미지 |
| language | string | ⚪ | 언어 코드 (ko/en, 기본: ko) |

**Response:**

```json
{
  "vlm_response": "경복궁은 조선시대...",
  "image_hash": "a3f2b1c4d5e6...",
  "vector_matches": [
    {
      "id": "vec-place-001",
      "place_id": "place-001",
      "similarity": 0.92,
      "metadata": {
        "place_name": "경복궁",
        "category": "역사유적",
        "latitude": 37.5796,
        "longitude": 126.9770
      }
    }
  ],
  "confidence_score": 0.92,
  "processing_time_ms": 1250
}
```

**Status Codes:**

- 200: 성공
- 400: 잘못된 이미지 형식
- 500: 서버 오류
- 503: AI 서비스 불가

---

#### POST /vlm/similar

유사 이미지 검색

**Request Body:**

```json
{
  "image": "base64_encoded_image",
  "top_k": 5,
  "threshold": 0.7
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| image | string | ✅ | Base64 인코딩된 이미지 |
| top_k | integer | ⚪ | 반환 결과 수 (기본: 5) |
| threshold | float | ⚪ | 최소 유사도 (기본: 0.7) |

**Response:**

```json
{
  "success": true,
  "count": 3,
  "matches": [
    {
      "id": "vec-001",
      "place_id": "place-001",
      "similarity": 0.95,
      "metadata": {...}
    }
  ]
}
```

---

#### POST /vlm/embed

이미지 임베딩 생성 및 Pinecone 저장 (관리자용)

**Request Body:**

```json
{
  "image": "base64_encoded_image",
  "place_id": "place-001",
  "metadata": {
    "image_url": "https://...",
    "category": "역사유적"
  }
}
```

**Response:**

```json
{
  "success": true,
  "vector_id": "vec-550e8400-...",
  "place_id": "place-001",
  "image_hash": "a3f2b1c4...",
  "dimension": 512
}
```

---

#### POST /vlm/tts

텍스트를 음성으로 변환

**Request Body:**

```json
{
  "text": "경복궁은 조선시대 법궁입니다.",
  "language_code": "ko-KR"
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| text | string | ✅ | 변환할 텍스트 |
| language_code | string | ⚪ | 언어 코드 (기본: ko-KR) |

**Response:**

```json
{
  "audio": "base64_encoded_audio_mp3",
  "format": "mp3",
  "size_bytes": 45678
}
```

---

#### GET /vlm/health

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
    "dimension": 512
  }
}
```

---

### Docent - AI Tour Guide

#### POST /docent/chat

AI 도슨트와 대화

**Request Body:**

```json
{
  "landmark": "경복궁",
  "user_message": "근정전에 대해 알려줘",
  "language": "ko"
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| landmark | string | ✅ | 장소명 |
| user_message | string | ⚪ | 사용자 질문 (null이면 기본 설명) |
| language | string | ⚪ | 언어 (ko/en, 기본: ko) |

**Response:**

```json
{
  "message": "근정전은 경복궁의 정전으로...",
  "landmark": "경복궁",
  "language": "ko"
}
```

---

#### POST /docent/quiz

퀴즈 생성

**Request Body:**

```json
{
  "landmark": "경복궁",
  "language": "ko"
}
```

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

#### POST /docent/tts

텍스트를 음성으로 변환

**Request Body:**

```json
{
  "text": "안녕하세요",
  "language_code": "ko-KR"
}
```

**Response:**

```json
{
  "audio": "base64_encoded_audio",
  "format": "mp3",
  "size_bytes": 12345
}
```

---

#### GET /docent/health

도슨트 서비스 상태

**Response:**

```json
{
  "status": "healthy",
  "services": {
    "gemini": true,
    "tts": true
  }
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

**Status Codes:**

- 400: Bad Request (잘못된 입력)
- 404: Not Found (리소스 없음)
- 500: Internal Server Error (서버 오류)
- 503: Service Unavailable (AI 서비스 불가)

## Rate Limiting

현재 제한 없음 (프로덕션에서는 구현 필요)

## Swagger UI

대화형 API 문서: http://localhost:8000/docs

## Notes

- 이미지는 Base64 인코딩 필요
- 최대 이미지 크기: 20MB (권장: 5MB 이하)
- TTS 텍스트 길이 제한: 5000자
- Pinecone 검색 결과: place_id만 반환 (상세 정보는 별도 조회 필요)
