# API Documentation

Quest of Seoul Backend API Reference

## Base URL

```
http://localhost:8000
```

Production: `https://your-domain.com`

## Authentication

JWT Bearer 토큰 기반 인증을 사용합니다.

### 인증 방법

1. **회원가입** (`POST /auth/signup`) 또는 **로그인** (`POST /auth/login`)을 통해 `access_token`을 받습니다.
2. 인증이 필요한 API 요청 시 `Authorization` 헤더에 토큰을 포함합니다:
   ```
   Authorization: Bearer <access_token>
   ```

### 인증 엔드포인트

- `POST /auth/signup` - 회원가입
- `POST /auth/login` - 로그인
- `GET /auth/me` - 현재 사용자 정보 조회
- `POST /auth/refresh` - 토큰 갱신

자세한 내용은 아래 "Authentication Endpoints" 섹션을 참조하세요.

---

## Endpoints Overview

### Authentication (인증)
- POST `/auth/signup` - 회원가입
- POST `/auth/login` - 로그인
- GET `/auth/me` - 현재 사용자 정보 조회
- POST `/auth/refresh` - 토큰 갱신

### Docent (AI 도슨트)
- POST `/docent/chat` - AI 도슨트 대화 (인증 필요)
- POST `/docent/quiz` - 퀴즈 생성
- POST `/docent/tts` - TTS 생성
- GET `/docent/history` - 대화 기록 조회 (인증 필요)
- WebSocket `/docent/ws/tts` - TTS 스트리밍
- WebSocket `/docent/ws/chat` - 채팅 스트리밍

### Quest (퀘스트 관리)
- GET `/quest/list` - 퀘스트 목록
- POST `/quest/nearby` - 주변 퀘스트 검색
- POST `/quest/start` - 퀘스트 시작/재개 (인증 필요)
- POST `/quest/progress` - 진행 상황 업데이트 (인증 필요)
- GET `/quest/user` - 사용자 퀘스트 조회 (인증 필요)
- GET `/quest/{quest_id}` - 퀘스트 상세 정보 (+ 사용자 포인트/상태, 선택적 인증)
- GET `/quest/{quest_id}/quizzes` - 퀘스트 연동 퀴즈 조회
- POST `/quest/{quest_id}/quizzes/{quiz_id}/submit` - 퀴즈 제출 및 포인트 적립 (인증 필요)

### Reward (리워드 시스템)
- GET `/reward/points` - 포인트 조회 (인증 필요)
- POST `/reward/points/add` - 포인트 추가 (인증 필요)
- GET `/reward/list` - 리워드 목록
- POST `/reward/claim` - 리워드 획득 (인증 필요)
- GET `/reward/claimed` - 획득한 리워드 조회 (인증 필요)
- POST `/reward/use/{reward_id}` - 리워드 사용 (인증 필요)

### VLM (이미지 분석)
- POST `/vlm/analyze` - 이미지 분석 (인증 필요)
- POST `/vlm/analyze-multipart` - 멀티파트 이미지 분석 (인증 필요)
- POST `/vlm/similar` - 유사 이미지 검색
- POST `/vlm/embed` - 임베딩 생성 (관리자)
- GET `/vlm/places/nearby` - 주변 장소 조회
- GET `/vlm/health` - 서비스 상태 확인

### Recommend (추천 시스템)
- POST `/recommend/similar-places` - 장소 추천 (인증 필요)
- GET `/recommend/nearby-quests` - 주변 퀘스트 추천
- GET `/recommend/quests/category/{category}` - 카테고리별 퀘스트
- GET `/recommend/quests/high-reward` - 포인트가 높은 퀘스트 추천
- GET `/recommend/quests/newest` - 최신 퀘스트 추천
- GET `/recommend/quests/{quest_id}` - 퀘스트 상세
- POST `/recommend/quests/{quest_id}/submit` - 퀴즈 제출
- GET `/recommend/stats` - 추천 시스템 통계

### Map (맵 검색 및 필터)
- POST `/map/search` - 장소명으로 퀘스트/장소 검색
- POST `/map/filter` - 필터 조건으로 퀘스트/장소 검색
- GET `/map/stats` - 맵 헤더 통계 조회 (인증 필요)
- POST `/map/stats/walk-distance` - 선택한 퀘스트 루트의 총 거리 계산 (인증 필요)

### AI Station (AI Station 통합 기능)
- GET `/ai-station/chat-list` - 채팅 리스트 조회 (인증 필요)
- GET `/ai-station/chat-session/{session_id}` - 특정 세션의 채팅 내역 조회 (인증 필요)
- POST `/ai-station/explore/rag-chat` - 일반 채팅 (인증 필요)
- POST `/ai-station/quest/rag-chat` - 퀘스트 모드 채팅 (인증 필요)
- POST `/ai-station/quest/vlm-chat` - 퀘스트 모드 VLM 채팅 (인증 필요)
- POST `/ai-station/stt-tts` - STT + TTS 통합 (인증 필요)
- POST `/ai-station/route-recommend` - 여행 일정 추천 (인증 필요)

### Analytics (분석 및 통계)
- GET `/analytics/location-stats/district` - 지자체별 위치 정보 통계 (인증 필요)
- GET `/analytics/location-stats/quest` - 퀘스트별 방문 통계 (인증 필요)
- GET `/analytics/location-stats/time` - 시간대별 통계 (인증 필요)
- GET `/analytics/location-stats/summary` - 전체 요약 통계 (인증 필요)

---

## Authentication Endpoints

### POST /auth/signup

회원가입

**Request Body:**

```json
{
  "email": "user@example.com",
  "password": "securepassword",
  "nickname": "사용자"
}
```

**Response:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_id": "uuid-here",
  "email": "user@example.com",
  "nickname": "사용자"
}
```

---

### POST /auth/login

로그인

**Request Body:**

```json
{
  "email": "user@example.com",
  "password": "securepassword"
}
```

**Response:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_id": "uuid-here",
  "email": "user@example.com",
  "nickname": "사용자"
}
```

---

### GET /auth/me

현재 로그인한 사용자 정보 조회

**Headers:**
- `Authorization: Bearer <token>`

**Response:**

```json
{
  "user_id": "uuid-here",
  "email": "user@example.com",
  "nickname": "사용자",
  "joined_at": "2024-01-01T12:00:00Z"
}
```

---

### POST /auth/refresh

토큰 갱신

**Headers:**
- `Authorization: Bearer <token>`

**Response:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_id": "uuid-here",
  "email": "user@example.com",
  "nickname": "사용자"
}
```

---

## Docent Endpoints

### POST /docent/chat

AI 도슨트와 대화

**Headers:**
- `Authorization: Bearer <token>` (필수)

**Request Body:**

```json
{
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

### GET /docent/history

사용자 대화 기록 조회

**Headers:**
- `Authorization: Bearer <token>` (필수)

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

**Note:** WebSocket은 현재 메시지에 `user_id`를 포함하는 방식을 사용합니다. 향후 토큰 기반 인증으로 업그레이드 예정입니다.

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

### POST /quest/start

사용자가 특정 장소 1km 이내에서 퀘스트를 시작(또는 재개)할 때 호출합니다. `user_quests`와 `user_quest_progress`가 동시에 초기화되고, 이후 퀘스트 챗/퀴즈 API에서 재사용할 `quest_id`와 `place_id`를 돌려줍니다.

**Headers:**
- `Authorization: Bearer <token>` (필수)

**Request Body:**

```json
{
  "quest_id": 1,
  "latitude": 37.5665,
  "longitude": 126.9780,
  "start_latitude": 37.5665,
  "start_longitude": 126.9780
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| quest_id | integer | 필수 | 퀘스트 ID |
| latitude | float | 선택 | 사용자 현재 위치 위도 (위치 정보 수집용) |
| longitude | float | 선택 | 사용자 현재 위치 경도 (위치 정보 수집용) |
| start_latitude | float | 선택 | 출발 위치 위도 (위치 정보 수집용) |
| start_longitude | float | 선택 | 출발 위치 경도 (위치 정보 수집용) |

**Response:**

```json
{
  "quest": {
    "id": 1,
    "name": "경복궁",
    "description": "조선 왕조의 법궁...",
    "reward_point": 300,
    "place_id": "13ac5471-b78b-4640-b3ff-e2e63d9055ed",
    "place": {
      "address": "서울 종로구 사직로 161",
      "district": "종로구",
      "images": ["https://.../main.jpg"]
    }
  },
  "place": {
    "address": "서울 종로구 사직로 161",
    "district": "종로구"
  },
  "place_id": "13ac5471-b78b-4640-b3ff-e2e63d9055ed",
  "status": "in_progress",
  "message": "Quest started"
}
```

**Notes:**
- 최초 호출 시 `user_quests` 레코드를 생성하고, 이후에는 기존 상태(예: completed)를 그대로 반환합니다.
- 모든 FK 제약을 맞추기 위해 사용자 레코드가 없으면 자동으로 guest 사용자로 생성됩니다.

---

### POST /quest/progress

퀘스트 진행 상황 업데이트

**Headers:**
- `Authorization: Bearer <token>` (필수)

**Request Body:**

```json
{
  "quest_id": 1,
  "status": "completed"
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
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

**Notes:**
- `completed` 상태에서 다시 `completed`를 호출해도 추가 포인트가 적립되지 않습니다.
- 퀘스트 포인트는 퀴즈 정답 제출 (`/quest/{quest_id}/quizzes/{quiz_id}/submit`)과 `update_quest_progress` 중 하나만 사용하세요.

---

### GET /quest/user

사용자 퀘스트 조회

**Headers:**
- `Authorization: Bearer <token>` (필수)

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
  "quest": {
    "id": 1,
    "name": "경복궁 (Gyeongbokgung Palace)",
    "description": "조선왕조의 법궁으로...",
    "latitude": 37.5796,
    "longitude": 126.9770,
    "reward_point": 300,
    "place_id": "13ac5471-b78b-4640-b3ff-e2e63d9055ed",
    "place": {
      "address": "서울 종로구 사직로 161",
      "image_url": "https://.../main.jpg"
    }
  },
  "user_status": {
    "status": "completed",
    "started_at": "2025-11-20T10:12:00",
    "completed_at": "2025-11-20T10:20:00"
  },
  "user_points": 1240
}
```

**Notes:**
- `user_id` 쿼리 파라미터를 전달하면 해당 유저의 진행 상태(`user_status`)와 현재 포인트(`user_points`)가 포함됩니다.
- `user_id`가 없으면 `quest` 필드만 반환됩니다.

---

### GET /quest/{quest_id}/quizzes

퀘스트 시작 이후 place_id에 연동된 퀴즈 세트를 조회합니다.

**Response:**

```json
{
  "quest": {
    "id": 1,
    "name": "경복궁",
    "reward_point": 300
  },
  "quizzes": [
    {
      "id": 77,
      "question": "경복궁의 정전 이름은?",
      "options": ["근정전", "중화전", "명정전", "진전"],
      "hint": "왕이 공식 업무를 보던 전각",
      "difficulty": "easy"
    }
  ],
  "count": 1
}
```

---

### POST /quest/{quest_id}/quizzes/{quiz_id}/submit

퀘스트와 연결된 퀴즈를 제출하고 포인트를 적립합니다. 정답일 때만 `user_quests` 상태가 `completed`로 바뀌고 퀘스트 포인트가 `points` 테이블에 적립됩니다.

**Headers:**
- `Authorization: Bearer <token>` (필수)

**Request Body:**

```json
{
  "answer": 0,
  "is_last_quiz": false
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| answer | integer | 필수 | 답안 (0-3) |
| is_last_quiz | boolean | 선택 | 마지막 퀴즈 여부 (기본: false) |

**Response (정답 - 첫 시도):**

```json
{
  "success": true,
  "is_correct": true,
  "earned": 20,
  "total_score": 20,
  "retry_allowed": false,
  "hint": null,
  "completed": false,
  "points_awarded": 0,
  "already_completed": false,
  "new_balance": null,
  "explanation": "근정전은 조선의 공식 의례가 치러지던 정전입니다."
}
```

**Response (오답 - 첫 시도):**

```json
{
  "success": true,
  "is_correct": false,
  "earned": 0,
  "total_score": 0,
  "retry_allowed": true,
  "hint": "왕이 공식 업무를 보던 전각",
  "completed": false,
  "points_awarded": 0,
  "already_completed": false,
  "new_balance": null,
  "explanation": null
}
```

**Response (정답 - 힌트 후 재시도):**

```json
{
  "success": true,
  "is_correct": true,
  "earned": 10,
  "total_score": 10,
  "retry_allowed": false,
  "hint": null,
  "completed": false,
  "points_awarded": 0,
  "already_completed": false,
  "new_balance": null,
  "explanation": "근정전은 조선의 공식 의례가 치러지던 정전입니다."
}
```

**Response (퀘스트 완료 - 마지막 퀴즈 정답):**

```json
{
  "success": true,
  "is_correct": true,
  "earned": 20,
  "total_score": 100,
  "retry_allowed": false,
  "hint": null,
  "completed": true,
  "points_awarded": 100,
  "already_completed": false,
  "new_balance": 1540,
  "explanation": "근정전은 조선의 공식 의례가 치러지던 정전입니다."
}
```

**Notes:**
- **점수 시스템**: 첫 시도 정답 20점, 힌트 후 재시도 정답 10점
- **퀘스트 완료**: `is_last_quiz`가 true이고 정답일 때 퀘스트가 완료되며 총 점수가 포인트로 적립됩니다
- **재시도**: 첫 시도 오답 시 `retry_allowed`가 true이고 `hint`가 제공됩니다
- 동일 퀘스트에 대해 이미 `completed` 상태라면 `points_awarded`는 0이고 `already_completed`가 true로 반환됩니다
- 모든 시도 횟수는 `user_quest_progress.quiz_attempts`에 누적됩니다

---

## Reward Endpoints

### GET /reward/points

사용자 포인트 조회

**Headers:**
- `Authorization: Bearer <token>` (필수)

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

**Headers:**
- `Authorization: Bearer <token>` (필수)

**Request Body:**

```json
{
  "points": 50,
  "reason": "Quest completion"
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
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

**Query Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| type | string | 선택 | 리워드 타입 필터 (food, cafe, shopping, ticket, activity, entertainment, beauty, wellness) |
| search | string | 선택 | 리워드 이름 검색 |

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

**Headers:**
- `Authorization: Bearer <token>` (필수)

**Request Body:**

```json
{
  "reward_id": 1
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
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

### GET /reward/claimed

획득한 리워드 조회

**Headers:**
- `Authorization: Bearer <token>` (필수)

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

**Headers:**
- `Authorization: Bearer <token>` (필수)

**Path Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| reward_id | integer | 필수 | 리워드 ID |

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

**Headers:**
- `Authorization: Bearer <token>` (필수)

**Request Body:**

```json
{
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

**Headers:**
- `Authorization: Bearer <token>` (필수)

**Form Data:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
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

이미지 기반 장소 추천 (다중 이미지 지원: 1개 또는 3개)

**Headers:**
- `Authorization: Bearer <token>` (필수)

**Request Body (단일 이미지):**

```json
{
  "image": "base64_encoded_image",
  "latitude": 37.5796,
  "longitude": 126.9770,
  "start_latitude": 37.5665,
  "start_longitude": 126.9780,
  "radius_km": 5.0,
  "limit": 3,
  "quest_only": true
}
```

**Request Body (다중 이미지):**

```json
{
  "images": [
    "base64_encoded_image_1",
    "base64_encoded_image_2",
    "base64_encoded_image_3"
  ],
  "latitude": 37.5796,
  "longitude": 126.9770,
  "start_latitude": 37.5665,
  "start_longitude": 126.9780,
  "radius_km": 5.0,
  "limit": 3,
  "quest_only": true
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| image | string | 선택* | Base64 인코딩 단일 이미지 (`images`가 없을 때 필수) |
| images | array[string] | 선택* | Base64 인코딩 이미지 배열 (1개 또는 3개, `image`가 없을 때 필수) |
| latitude | float | 선택 | 현재 위치 위도 (거리 계산용) |
| longitude | float | 선택 | 현재 위치 경도 (거리 계산용) |
| start_latitude | float | 선택 | 출발 위치 위도 (정렬 기준, 없으면 latitude 사용) |
| start_longitude | float | 선택 | 출발 위치 경도 (정렬 기준, 없으면 longitude 사용) |
| radius_km | float | 선택 | 검색 반경 (기본: 5.0, 현재 사용 안 함) |
| limit | integer | 선택 | 결과 개수 (기본: 3, 상위 3개 추천) |
| quest_only | boolean | 선택 | 퀘스트 장소만 (기본: true) |

**Note:** `image` 또는 `images` 중 하나는 반드시 제공해야 합니다.

**Response:**

```json
{
  "success": true,
  "count": 3,
  "recommendations": [
    {
      "quest_id": 1,
      "place_id": "place-001",
      "similarity": 0.92,
      "name": "Gyeongbokgung Palace",
      "description": "The main royal palace of the Joseon Dynasty, built in 1395.",
      "category": "Historic Site",
      "latitude": 37.579617,
      "longitude": 126.977041,
      "reward_point": 100,
      "district": "Jongno-gu",
      "place_image_url": "https://ak-d.tripcdn.com/images/0104p120008ars39uB986.webp",
      "distance_km": 3.5,
      "place": {
        "id": "place-001",
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

**Notes:**
- `quest_id`는 해당 place에 연결된 활성 quest가 있을 때만 포함됩니다
- `distance_km`는 `latitude`와 `longitude`가 제공될 때만 계산됩니다
- **정렬 기준**: `start_latitude`와 `start_longitude`가 지정되면 출발 위치 기준으로 가까운 순 정렬, 없으면 `latitude`와 `longitude` 사용
- Quest 정보가 없으면 Place 정보만 사용됩니다
- **다중 이미지 지원**: `images` 배열에 1개 또는 최대 3개 이미지를 제공할 수 있습니다. 3개 이미지일 경우 평균 임베딩을 사용하여 더 정확한 추천을 제공합니다.
- **DB 검증**: Pinecone에서 반환된 결과가 실제 DB에 존재하는지 검증하여, 누락된 장소는 제외하고 실제 존재하는 장소만 추천합니다.
- **임계값**: 유사도 임계값이 0.2로 낮춰져 상위 3개 추천에 최적화되었습니다.

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
      "id": 1,
      "place_id": "13ac5471-b78b-4640-b3ff-e2e63d9055ed",
      "name": "Gyeongbokgung Palace",
      "title": null,
      "description": "The main royal palace of the Joseon Dynasty, built in 1395.",
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
      "place_image_url": "https://ak-d.tripcdn.com/images/0104p120008ars39uB986.webp",
      "distance_km": 0.5
    }
  ]
}
```

**Notes:**
- 거리순으로 정렬됩니다 (`distance_km` 오름차순)
- `distance_km`는 사용자 위치와 퀘스트 위치 간의 거리입니다 (km 단위)

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

### GET /recommend/quests/high-reward

포인트가 높은 퀘스트 추천 (Wanna Get Some Mint? 섹션용)

**Query Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| latitude | float | 선택 | 사용자 현재 위도 (거리 계산용) |
| longitude | float | 선택 | 사용자 현재 경도 (거리 계산용) |
| limit | integer | 선택 | 결과 개수 (기본: 3) |
| min_reward_point | integer | 선택 | 최소 포인트 (기본: 100) |

**Response:**

```json
{
  "success": true,
  "count": 3,
  "quests": [
    {
      "id": 1,
      "place_id": "13ac5471-b78b-4640-b3ff-e2e63d9055ed",
      "name": "Gyeongbokgung Palace",
      "title": null,
      "description": "The main royal palace of the Joseon Dynasty, built in 1395.",
      "category": "Historic Site",
      "latitude": 37.579617,
      "longitude": 126.977041,
      "reward_point": 500,
      "points": 10,
      "difficulty": "easy",
      "is_active": true,
      "completion_count": 0,
      "created_at": "2025-11-22T10:14:30.222474",
      "district": "Jongno-gu",
      "place_image_url": "https://ak-d.tripcdn.com/images/0104p120008ars39uB986.webp",
      "distance_km": 3.5
    }
  ]
}
```

**Notes:**
- `reward_point` 내림차순으로 정렬됩니다
- `is_active = TRUE`인 퀘스트만 반환됩니다
- `distance_km`는 `latitude`와 `longitude`가 제공될 때만 계산됩니다

---

### GET /recommend/quests/newest

최신 퀘스트 추천 (See What's New in Seoul 섹션용)

**Query Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| latitude | float | 선택 | 사용자 현재 위도 (거리 계산용) |
| longitude | float | 선택 | 사용자 현재 경도 (거리 계산용) |
| limit | integer | 선택 | 결과 개수 (기본: 3) |
| days | integer | 선택 | 최근 N일 이내 (기본: 30) |

**Response:**

```json
{
  "success": true,
  "count": 3,
  "quests": [
    {
      "id": 1,
      "place_id": "13ac5471-b78b-4640-b3ff-e2e63d9055ed",
      "name": "Gyeongbokgung Palace",
      "title": null,
      "description": "The main royal palace of the Joseon Dynasty, built in 1395.",
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
      "place_image_url": "https://ak-d.tripcdn.com/images/0104p120008ars39uB986.webp",
      "distance_km": 3.5
    }
  ]
}
```

**Notes:**
- `created_at` 내림차순으로 정렬됩니다
- `is_active = TRUE`인 퀘스트만 반환됩니다
- `days` 파라미터로 최근 N일 이내 퀘스트만 필터링됩니다
- `distance_km`는 `latitude`와 `longitude`가 제공될 때만 계산됩니다

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

**Headers:**
- `Authorization: Bearer <token>` (필수)

**Path Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| quest_id | string | 필수 | 퀘스트 ID |

**Query Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| quiz_id | string | 필수 | 퀴즈 ID |
| answer | integer | 필수 | 답안 (0-3) |

**Note:** 이 엔드포인트는 `/quest/{quest_id}/quizzes/{quiz_id}/submit`을 사용하는 것을 권장합니다.

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
  "is_correct": false,
  "explanation": null
}
```

**Status Codes:**
- 200: 성공
- 404: 퀴즈를 찾을 수 없음
- 500: 서버 오류

**Notes:**
- 정답일 경우에만 `explanation`이 포함됩니다
- 정답 시 퀘스트 완료 카운트가 증가합니다

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

## Map Endpoints

### POST /map/search

장소명으로 퀘스트/장소 검색

**Request Body:**

```json
{
  "query": "경복궁",
  "latitude": 37.5665,
  "longitude": 126.9780,
  "radius_km": 50.0,
  "limit": 20
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| query | string | 필수 | 검색어 (장소명) |
| latitude | float | 선택 | 사용자 현재 위도 (거리 계산용) |
| longitude | float | 선택 | 사용자 현재 경도 (거리 계산용) |
| radius_km | float | 선택 | 검색 반경 (기본: 50.0) |
| limit | integer | 선택 | 결과 개수 (기본: 20) |

**Response:**

```json
{
  "success": true,
  "count": 5,
  "quests": [
    {
      "id": 1,
      "place_id": "13ac5471-b78b-4640-b3ff-e2e63d9055ed",
      "name": "Gyeongbokgung Palace",
      "title": null,
      "description": "The main royal palace of the Joseon Dynasty, built in 1395.",
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
      "place_image_url": "https://ak-d.tripcdn.com/images/0104p120008ars39uB986.webp",
      "distance_km": 3.5
    }
  ]
}
```

**Notes:**
- 검색어는 `quests.name`, `places.name`, `places.metadata->>'rag_text'`에서 검색됩니다
- 거리 순으로 정렬됩니다 (위도/경도 제공 시)
- 반경 필터링은 위도/경도가 제공될 때만 적용됩니다

---

### POST /map/filter

필터 조건으로 퀘스트/장소 검색

**Request Body:**

```json
{
  "categories": ["Attractions", "History"],
  "districts": ["Jongno-gu", "Jung-gu"],
  "sort_by": "nearest",
  "latitude": 37.5665,
  "longitude": 126.9780,
  "radius_km": 50.0,
  "limit": 20
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| categories | array[string] | 선택 | 카테고리 필터 (빈 배열이면 전체) |
| districts | array[string] | 선택 | 자치구 필터 (빈 배열이면 전체) |
| sort_by | string | 선택 | 정렬 기준 ("nearest", "rewarded", "newest", 기본: "nearest") |
| latitude | float | 선택 | 사용자 현재 위도 |
| longitude | float | 선택 | 사용자 현재 경도 |
| radius_km | float | 선택 | 검색 반경 (기본: 50.0) |
| limit | integer | 선택 | 결과 개수 (기본: 20) |

**Response:**

```json
{
  "success": true,
  "count": 5,
  "quests": [
    {
      "id": 1,
      "place_id": "13ac5471-b78b-4640-b3ff-e2e63d9055ed",
      "name": "Gyeongbokgung Palace",
      "title": null,
      "description": "The main royal palace of the Joseon Dynasty, built in 1395.",
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
      "place_image_url": "https://ak-d.tripcdn.com/images/0104p120008ars39uB986.webp",
      "distance_km": 3.5
    }
  ],
  "filters_applied": {
    "categories": ["Attractions", "History"],
    "districts": ["Jongno-gu", "Jung-gu"],
    "sort_by": "nearest"
  }
}
```

**Notes:**
- `sort_by`:
  - `"nearest"`: 거리순 (위도/경도 제공 시), 없으면 reward_point 내림차순
  - `"rewarded"`: reward_point 내림차순
  - `"newest"`: created_at 내림차순

---

### GET /map/stats

맵 헤더에 표시할 사용자 통계 조회

**Headers:**
- `Authorization: Bearer <token>` (필수)

**Query Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| quest_ids | array[integer] | 선택 | 선택한 퀘스트 ID 목록 (walk 거리 계산용) |
| user_latitude | float | 선택 | 사용자 현재 위도 (walk 거리 계산용) |
| user_longitude | float | 선택 | 사용자 현재 경도 (walk 거리 계산용) |

**Response:**

```json
{
  "success": true,
  "walk_distance_km": 2.5,
  "mint_points": 350,
  "walk_calculation": {
    "type": "selected_quests_route",
    "total_distance_km": 2.5,
    "route": [
      {
        "from": "user_location",
        "to": "quest_1",
        "distance_km": 1.5
      },
      {
        "from": "quest_1",
        "to": "quest_2",
        "distance_km": 1.0
      }
    ]
  }
}
```

**Status Codes:**
- 200: 성공
- 404: 사용자를 찾을 수 없음
- 500: 서버 오류

**Notes:**
- `walk_distance_km`: 선택한 퀘스트 루트의 총 거리 (quest_ids 제공 시)
- `mint_points`: 사용자 총 포인트 (모든 포인트 트랜잭션 합계)
- `walk_calculation`은 `quest_ids`가 제공될 때만 포함됩니다

---

### POST /map/stats/walk-distance

선택한 퀘스트 루트의 총 거리 계산 (walk 거리만)

**Headers:**
- `Authorization: Bearer <token>` (필수)

**Request Body:**

```json
{
  "quest_ids": [1, 2, 3],
  "user_latitude": 37.5665,
  "user_longitude": 126.9780
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| quest_ids | array[integer] | 필수 | 선택한 퀘스트 ID 목록 (순서대로) |
| user_latitude | float | 필수 | 사용자 현재 위도 |
| user_longitude | float | 필수 | 사용자 현재 경도 |

**Response:**

```json
{
  "success": true,
  "total_distance_km": 2.5,
  "route": [
    {
      "from": {
        "type": "user_location",
        "latitude": 37.5665,
        "longitude": 126.9780
      },
      "to": {
        "type": "quest",
        "quest_id": 1,
        "name": "Gyeongbokgung Palace",
        "latitude": 37.579617,
        "longitude": 126.977041
      },
      "distance_km": 1.5
    },
    {
      "from": {
        "type": "quest",
        "quest_id": 1,
        "name": "Gyeongbokgung Palace",
        "latitude": 37.579617,
        "longitude": 126.977041
      },
      "to": {
        "type": "quest",
        "quest_id": 2,
        "name": "N Seoul Tower",
        "latitude": 37.551169,
        "longitude": 126.988227
      },
      "distance_km": 1.0
    }
  ]
}
```

**Status Codes:**
- 200: 성공
- 400: 잘못된 요청 (quest_ids가 비어있거나, 위치 정보 없음)
- 404: 퀘스트를 찾을 수 없음
- 500: 서버 오류

**Notes:**
- 퀘스트 순서는 `quest_ids` 배열 순서대로 계산됩니다
- 사용자 위치 → 첫 번째 퀘스트 → 두 번째 퀘스트 → ... 순으로 거리를 계산합니다

---

## AI Station Endpoints

### GET /ai-station/chat-list

탐험/퀘스트 모드를 아우르는 채팅 리스트 조회 (하프 모달용). `mode`와 `function_type`을 조합해서 필요한 탭만 불러올 수 있습니다.

**Headers:**
- `Authorization: Bearer <token>` (필수)

**Query Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| limit | integer | 선택 | 결과 개수 (기본: 20) |
| mode | string | 선택 | `explore`, `quest` 중 선택 |
| function_type | string | 선택 | `rag_chat`, `vlm_chat`, `route_recommend` |

**필터링 규칙:**
- `mode`와 `function_type` 모두 없으면: **일반 채팅만** 반환 (`mode=explore`, `function_type=rag_chat`)
- `mode`만 지정:
  - `mode=explore`: 일반 채팅(`rag_chat`) + 여행일정 채팅(`route_recommend`)
  - `mode=quest`: 퀘스트 채팅(`rag_chat`, `vlm_chat`)
- `function_type`만 지정:
  - `function_type=rag_chat`: 일반 채팅(`explore`) + 퀘스트 채팅(`quest`)
  - `function_type=vlm_chat`: 퀘스트 채팅(`quest`)만
  - `function_type=route_recommend`: 여행일정 채팅(`explore`)만
- 둘 다 지정: 정확히 일치하는 것만 반환

**Response:**

```json
{
  "success": true,
  "sessions": [
    {
      "session_id": "uuid",
      "function_type": "rag_chat",
      "mode": "explore",
      "title": "근정전에 대해 알려줘",
      "is_read_only": false,
      "created_at": "2024-01-01T12:00:00Z",
      "updated_at": "2024-01-01T12:00:00Z",
      "time_ago": "5분전",
      "chats": [
        {
          "id": 1,
          "user_message": "근정전에 대해 알려줘",
          "ai_response": "근정전은...",
          "created_at": "2024-01-01T12:00:00Z"
        }
      ]
    },
    {
      "session_id": "uuid-2",
      "function_type": "route_recommend",
      "mode": "explore",
      "title": "역사유적 탐방",
      "is_read_only": true,
      "created_at": "2024-01-01T10:00:00Z",
      "updated_at": "2024-01-01T10:00:00Z",
      "time_ago": "01월 01일",
      "chats": []
    },
    {
      "session_id": "uuid-3",
      "function_type": "rag_chat",
      "mode": "quest",
      "title": "경복궁 퀘스트",
      "is_read_only": true,
      "created_at": "2024-01-01T09:00:00Z",
      "updated_at": "2024-01-01T09:05:00Z",
      "time_ago": "01월 01일",
      "chats": [
        {
          "id": 31,
          "user_message": "이 궁궐의 하이라이트가 뭐야?",
          "ai_response": "경복궁의 하이라이트는 근정전과 경회루... ",
          "created_at": "2024-01-01T09:05:00Z"
        }
      ]
    }
  ],
  "count": 2
}
```

**Notes:**
- `title`: 일반 채팅은 첫 번째 질문, 여행 일정은 테마, 퀘스트 채팅은 퀘스트명
- `is_read_only`: 여행 일정/퀘스트 채팅은 true (조회만 가능)
- `time_ago`: "방금", "5분전", "2시간전", "01월 01일" 형식

---

### GET /ai-station/chat-session/{session_id}

특정 세션의 채팅 내역 조회

**Headers:**
- `Authorization: Bearer <token>` (필수)

**Path Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| session_id | string | 필수 | 세션 ID |

**Response:**

```json
{
  "success": true,
  "session": {
    "session_id": "uuid",
    "function_type": "rag_chat",
    "mode": "explore",
    "title": "근정전에 대해 알려줘",
    "is_read_only": false,
    "created_at": "2024-01-01T12:00:00Z"
  },
  "chats": [
    {
      "id": 1,
      "user_message": "근정전에 대해 알려줘",
      "ai_response": "근정전은 경복궁의 정전으로...",
      "created_at": "2024-01-01T12:00:00Z"
    },
    {
      "id": 2,
      "user_message": "그럼 사정전은?",
      "ai_response": "사정전은...",
      "created_at": "2024-01-01T12:05:00Z"
    }
  ],
  "count": 2
}
```

---

### POST /ai-station/explore/rag-chat

일반 채팅 (히스토리 저장)
- 첫 번째 질문이 세션 제목으로 사용됨
- 다시 들어와서 이어서 대화 가능

**Headers:**
- `Authorization: Bearer <token>` (필수)

**Request Body:**

```json
{
  "user_message": "경복궁 근정전에 대해 알려줘",
  "language": "ko",
  "prefer_url": false,
  "enable_tts": true,
  "chat_session_id": "uuid-optional"
}
```

**Response:**

```json
{
  "success": true,
  "message": "근정전은 경복궁의 정전으로...",
  "session_id": "uuid",
  "audio": "base64_encoded_audio_or_null",
  "audio_url": "https://storage.url/audio.mp3_or_null"
}
```

**Notes:**
- `chat_session_id`가 없으면 새 세션 생성
- `chat_session_id`가 있으면 기존 세션에 추가
- 첫 번째 메시지일 경우 `user_message`가 세션 제목으로 저장됨
- **특정 장소 환영 메시지**: RAG 검색 결과에서 첫 번째 장소를 감지하여, 해당 장소에 대한 환영 메시지를 생성합니다 (예: "경복궁에 오신 것을 환영합니다")

---

### POST /ai-station/quest/rag-chat

**AI Plus 챗** - 퀘스트 모드 맞춤형 여행 가이드 채팅

퀘스트 모드 - 장소 메타데이터를 context로 사용하는 LLM 채팅. 세션은 자동 생성되며 히스토리에 **조회 전용**으로 저장됩니다.

**핵심 원칙:**
1. **Quest_id 기반 데이터 필터링**: 오직 해당 `quest_id`에 해당하는 DB 데이터만 사용합니다.
2. **데이터 기반 답변**: Quest와 Place 테이블에서 가져온 실제 데이터만을 기반으로 답변합니다.
3. **DB 분리 설계**: 추후 맞춤형 여행 가이드 고도화를 위해 Quest별로 별도의 RAG 데이터베이스나 벡터 스토어를 분리할 수 있도록 설계되었습니다.

**Headers:**
- `Authorization: Bearer <token>` (필수)

**Request Body:**

```json
{
  "quest_id": 1,                    // 필수: Quest ID (해당 Quest의 데이터만 사용)
  "user_message": "이 장소의 역사를 알려줘",
  "landmark": "경복궁",              // 선택적: 장소 이름
  "language": "ko",                  // 선택적: 언어 (기본: "en")
  "prefer_url": false,               // 선택적: TTS URL 선호 여부
  "enable_tts": true,                // 선택적: TTS 활성화 여부
  "chat_session_id": "uuid-optional" // 선택적: 채팅 세션 ID
}
```

**Response:**

```json
{
  "success": true,
  "message": "경복궁은 조선왕조의 법궁으로...",
  "landmark": "경복궁",
  "quest_id": 1,
  "session_id": "uuid",
  "audio": "base64_encoded_audio_or_null"
}
```

**Notes:**
- **Quest_id 필수**: `quest_id`는 반드시 전달해야 하며, 서버가 해당 퀘스트/장소 설명을 context로 붙여 응답합니다.
- **데이터 필터링**: 오직 해당 `quest_id`에 연결된 Quest와 Place 데이터만 사용합니다. 다른 Quest나 Place의 데이터는 절대 사용하지 않습니다.
- **히스토리 저장**: 히스토리에 저장되지만 `is_read_only = true` 로 표시되므로 이어 쓰기는 불가합니다.
- **향후 RAG 검색**: 향후 RAG 검색을 추가할 경우에도 반드시 `quest_id` 또는 `place_id`로 필터링해야 합니다.
- **DB 분리 설계**: 추후 고도화를 위해 Quest별로 독립적인 벡터 스토어 네임스페이스나 RAG 데이터베이스를 사용할 수 있도록 설계되었습니다.

---

### POST /ai-station/quest/vlm-chat

**AI Plus 챗** - 퀘스트 모드 VLM 채팅

퀘스트 모드 - VLM 채팅. 사용자가 업로드한 이미지를 분석하고, 현재 진행 중인 퀘스트 장소 정보와 결합하여 설명합니다. 결과는 히스토리에 **조회 전용**으로 저장됩니다.

**핵심 원칙:**
1. **Quest_id 기반 데이터 필터링**: 오직 해당 `quest_id`에 해당하는 DB 데이터만 사용합니다.
2. **데이터 기반 답변**: Quest와 Place 테이블에서 가져온 실제 데이터만을 기반으로 이미지 분석 및 답변을 수행합니다.
3. **DB 분리 설계**: 추후 맞춤형 여행 가이드 고도화를 위해 Quest별로 별도의 RAG 데이터베이스나 벡터 스토어를 분리할 수 있도록 설계되었습니다.

**Headers:**
- `Authorization: Bearer <token>` (필수)

**Request Body:**

```json
{
  "quest_id": 1,                    // 필수: Quest ID (해당 Quest의 데이터만 사용)
  "image": "base64_encoded_image",  // 필수: base64 인코딩된 이미지
  "user_message": "이 장소가 뭐야?", // 선택적: 사용자 메시지
  "language": "ko",                  // 선택적: 언어 (기본: "en")
  "prefer_url": false,               // 선택적: TTS URL 선호 여부
  "enable_tts": true,                // 선택적: TTS 활성화 여부
  "chat_session_id": "uuid-optional" // 선택적: 채팅 세션 ID
}
```

**Response:**

```json
{
  "success": true,
  "message": "경복궁은 조선시대 법궁으로...",
  "place": {
    "id": "place-001",
    "name": "경복궁",
    "category": "역사유적"
  },
  "image_url": "https://storage.url/image.jpg",
  "quest_id": 1,
  "session_id": "uuid",
  "audio": "base64_encoded_audio_or_null"
}
```

**Notes:**
- **Quest_id 필수**: `quest_id`는 반드시 전달해야 하며, 해당 퀘스트 정보를 context로 첨부하여 이미지 분석을 수행합니다.
- **데이터 필터링**: 오직 해당 `quest_id`에 연결된 Quest와 Place 데이터만 사용합니다. 다른 Quest나 Place의 데이터는 절대 사용하지 않습니다.
- **이미지 분석**: 사용자가 찍은 이미지가 해당 장소와 어떻게 연결되는지 Quest 데이터를 기반으로 안내합니다.
- **히스토리 저장**: 히스토리에서는 `function_type = vlm_chat`, `mode = quest`, `is_read_only = true`로 관리됩니다.
- **향후 RAG 검색**: 향후 RAG 검색을 추가할 경우에도 반드시 `quest_id` 또는 `place_id`로 필터링해야 합니다.
- **DB 분리 설계**: 추후 고도화를 위해 Quest별로 독립적인 벡터 스토어 네임스페이스나 RAG 데이터베이스를 사용할 수 있도록 설계되었습니다.

---

### POST /ai-station/stt-tts

STT + TTS 통합 엔드포인트

**Headers:**
- `Authorization: Bearer <token>` (필수)

**Request Body:**

```json
{
  "audio": "base64_encoded_audio",
  "language_code": "ko-KR",
  "prefer_url": false
}
```

**Response:**

```json
{
  "success": true,
  "transcribed_text": "경복궁에 대해 알려줘",
  "audio_url": "https://storage.url/audio.mp3_or_null",
  "audio": "base64_encoded_audio"
}
```

---

### POST /ai-station/route-recommend

여행 일정 추천 (4개 퀘스트 추천)
- 히스토리에 저장됨 (보기 전용)
- 테마가 세션 제목으로 사용됨
- 다시 들어와서 수정 불가, 보기만 가능
- 출발 지점 지정 또는 현재 GPS 기준으로 가까운 순 정렬
- 마지막 장소는 야경 특별 장소로 추천

**Headers:**
- `Authorization: Bearer <token>` (필수)

**Request Body:**

```json
{
  "preferences": {
    "theme": ["Culture", "History", "Food"],  // 다중 선택 가능 (3~4개 권장), 단일 선택도 지원: "Culture"
    "category": "역사유적",                    // 선택적: 카테고리 정보
    "difficulty": "easy",                      // 선택적: 난이도
    "duration": "half_day",                    // 선택적: 소요 시간
    "districts": ["Jongno-gu", "Gangnam-gu"]  // 다중 선택 가능
  },
  "must_visit_place_id": "place-001",         // 선택적: 필수 방문 장소 ID
  "latitude": 37.5665,                        // 선택적: 현재 GPS 위도
  "longitude": 126.9780,                       // 선택적: 현재 GPS 경도
  "start_latitude": 37.5665,                  // 선택적: 출발 지점 위도 (서울역, 강남역 등)
  "start_longitude": 126.9780                 // 선택적: 출발 지점 경도
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| preferences | object | 필수 | 사용자 취향 정보 |
| preferences.theme | string \| array | 선택 | 테마 (다중 선택 가능: `["Culture", "History", "Food"]`, 단일 선택도 지원: `"Culture"`) |
| preferences.category | string \| object | 선택 | 카테고리 정보 |
| preferences.districts | array | 선택 | 선호하는 구/지역 리스트 (다중 선택 가능) |
| preferences.difficulty | string | 선택 | 난이도 (easy, medium, hard) |
| preferences.duration | string | 선택 | 소요 시간 (half_day, full_day 등) |
| must_visit_place_id | string | 선택 | 필수 방문 장소 ID (출발 위치 기준 거리순으로 자연스럽게 배치) |
| latitude | float | 선택 | 현재 GPS 위도 (거리 계산용, 출발 지점 미지정 시 사용) |
| longitude | float | 선택 | 현재 GPS 경도 (거리 계산용, 출발 지점 미지정 시 사용) |
| start_latitude | float | 선택 | 출발 지점 위도 (지정 시 사용, 없으면 latitude 사용) |
| start_longitude | float | 선택 | 출발 지점 경도 (지정 시 사용, 없으면 longitude 사용) |

**Response:**

```json
{
  "success": true,
  "quests": [
    {
      "id": 1,
      "name": "Gyeongbokgung Palace",
      "description": "...",
      "category": "Historic Site",
      "latitude": 37.579617,
      "longitude": 126.977041,
      "reward_point": 100,
      "distance_from_start": 1.5,
      "recommendation_score": 0.85,
      "score_breakdown": {
        "category": 1.0,
        "distance": 0.9,
        "diversity": 0.8,
        "popularity": 0.7,
        "reward": 0.5
      }
    },
    {
      "id": 2,
      "name": "N Seoul Tower",
      "description": "...",
      "category": "Attractions",
      "latitude": 37.551169,
      "longitude": 126.988227,
      "reward_point": 150,
      "distance_from_start": 2.3
    }
  ],
  "count": 4,
  "session_id": "uuid"
}
```

**Notes:**
- `preferences.theme` 또는 `preferences.category`가 세션 제목으로 사용됨 (theme이 리스트인 경우 첫 번째 테마 사용)
- `is_read_only: true`로 저장되어 수정 불가
- **테마 다중 선택**: `theme`을 리스트로 전달하면 여러 테마 중 하나라도 매칭되면 높은 점수 부여 (3~4개 권장)
- **출발 지점 기준 정렬**: `start_latitude`와 `start_longitude`가 지정되면 해당 지점 기준으로 가까운 순 정렬, 없으면 `latitude`와 `longitude` 사용
- **필수 방문 장소**: `must_visit_place_id`가 지정되면 항상 추천 결과에 포함되며, 출발 위치 기준 거리순으로 자연스럽게 배치됨 (1~4번째 중 적절한 위치)
- **야경 특별 장소**: 마지막 장소(4번째)는 자동으로 야경 특별 장소로 추천됩니다 (metadata, description, name에서 야경 관련 키워드 검색)
- **점수 계산**: 각 퀘스트는 카테고리 매칭(30%), 거리(25%), 다양성(20%), 인기도(15%), 포인트(10%) 가중치로 종합 점수를 계산합니다
  - 테마 다중 선택 시 여러 테마 중 가장 높은 매칭 점수를 사용
- **거리 정보**: `distance_from_start`는 출발 지점으로부터의 거리(km)입니다
- **중복 체크**: `place_id` 기준으로 중복된 장소는 제외됩니다
- **최대 4개 제한**: 추천 결과는 최대 4개 퀘스트로 제한됩니다

---

## Analytics Endpoints

### GET /analytics/location-stats/district

지자체별 위치 정보 통계 조회

**Headers:**
- `Authorization: Bearer <token>` (필수)

**Query Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| start_date | string | 선택 | 시작 날짜 (YYYY-MM-DD) |
| end_date | string | 선택 | 종료 날짜 (YYYY-MM-DD) |

**Response:**

```json
{
  "success": true,
  "stats": [
    {
      "district": "종로구",
      "visitor_count": 150,
      "quest_count": 320,
      "interest_count": 450,
      "avg_distance_km": 1.2
    }
  ],
  "total_districts": 5,
  "period": {
    "start_date": "2024-01-01",
    "end_date": "2024-01-31"
  }
}
```

**Notes:**
- `visitor_count`: 익명화된 사용자 수 (중복 제거)
- `quest_count`: 퀘스트 방문 횟수
- `interest_count`: 관심 표시 횟수
- `avg_distance_km`: 평균 거리 (km)
- 방문자 수 기준 내림차순 정렬

---

### GET /analytics/location-stats/quest

퀘스트별 방문 통계 조회

**Headers:**
- `Authorization: Bearer <token>` (필수)

**Query Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| quest_id | integer | 선택 | 퀘스트 ID (지정 시 해당 퀘스트만) |
| start_date | string | 선택 | 시작 날짜 (YYYY-MM-DD) |
| end_date | string | 선택 | 종료 날짜 (YYYY-MM-DD) |

**Response:**

```json
{
  "success": true,
  "stats": [
    {
      "quest_id": 1,
      "quest_name": "경복궁",
      "visitor_count": 85,
      "visit_count": 120,
      "district": "종로구",
      "avg_distance_km": 0.8
    }
  ],
  "total_quests": 10,
  "period": {
    "start_date": "2024-01-01",
    "end_date": "2024-01-31"
  }
}
```

**Notes:**
- `visitor_count`: 방문자 수 (중복 제거)
- `visit_count`: 방문 횟수 (전체)
- 방문 횟수 기준 내림차순 정렬

---

### GET /analytics/location-stats/time

시간대별 통계 조회

**Headers:**
- `Authorization: Bearer <token>` (필수)

**Query Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| start_date | string | 선택 | 시작 날짜 (YYYY-MM-DD) |
| end_date | string | 선택 | 종료 날짜 (YYYY-MM-DD) |
| group_by | string | 선택 | 그룹화 기준: hour, day, week (기본: hour) |

**Response:**

```json
{
  "success": true,
  "stats": [
    {
      "time_period": "2024-01-01 14:00",
      "visitor_count": 25,
      "visit_count": 35
    }
  ],
  "total_periods": 24,
  "group_by": "hour",
  "period": {
    "start_date": "2024-01-01",
    "end_date": "2024-01-01"
  }
}
```

**Notes:**
- `group_by`:
  - `hour`: 시간별 (예: "2024-01-01 14:00")
  - `day`: 일별 (예: "2024-01-01")
  - `week`: 주별 (예: "2024-W01")
- 시간대 순서대로 정렬

---

### GET /analytics/location-stats/summary

전체 요약 통계 조회

**Headers:**
- `Authorization: Bearer <token>` (필수)

**Query Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| start_date | string | 선택 | 시작 날짜 (YYYY-MM-DD) |
| end_date | string | 선택 | 종료 날짜 (YYYY-MM-DD) |

**Response:**

```json
{
  "success": true,
  "summary": {
    "total_visitors": 500,
    "total_visits": 1200,
    "total_quests": 50,
    "total_districts": 15,
    "avg_distance_km": 1.5
  },
  "period": {
    "start_date": "2024-01-01",
    "end_date": "2024-01-31"
  }
}
```

**Notes:**
- `total_visitors`: 총 방문자 수 (중복 제거)
- `total_visits`: 총 방문 횟수
- `total_quests`: 방문된 퀘스트 수 (중복 제거)
- `total_districts`: 방문된 자치구 수 (중복 제거)
- `avg_distance_km`: 평균 거리 (km)

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
