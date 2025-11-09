# 백엔드 아키텍처 분석

## 1. 개요

Quest of Seoul의 백엔드는 FastAPI 프레임워크를 사용한 위치 기반 AR 관광 애플리케이션 서버입니다. AI 기반 도슨트, 게임화된 퀘스트 시스템, 그리고 보상 메커니즘을 제공합니다.

## 2. 기술 스택

### 핵심 프레임워크
- **FastAPI** (v0.115.0) - 현대적이고 빠른 비동기 웹 프레임워크
- **Uvicorn** (v0.32.0) - ASGI 서버
- **Python 3.x** - 런타임 환경

### 주요 라이브러리
- **Supabase** (v2.9.1) - PostgreSQL 데이터베이스 및 스토리지
- **Google Gemini AI** (v0.8.3) - 대화형 AI (gemini-2.5-flash 모델)
- **Google Cloud TTS** (v2.18.0) - 음성 합성
- **Pydantic** (v2.9.2) - 데이터 검증
- **WebSockets** (v12.0) - 실시간 통신

## 3. 디렉토리 구조

```
backend/
├── main.py                          # FastAPI 애플리케이션 진입점
├── requirements.txt                  # Python 의존성
├── .env.example                     # 환경 변수 템플릿
├── render.yaml                      # Render.com 배포 설정
│
├── routers/                         # API 라우트 핸들러
│   ├── __init__.py
│   ├── docent.py                   # AI 도슨트/채팅 엔드포인트
│   ├── quest.py                    # 퀘스트 관리 엔드포인트
│   └── reward.py                   # 보상/포인트 엔드포인트
│
├── services/                        # 비즈니스 로직 서비스
│   ├── __init__.py
│   ├── ai.py                       # Google Gemini AI 통합
│   ├── db.py                       # Supabase 데이터베이스 클라이언트
│   ├── storage.py                  # Supabase Storage (파일 업로드)
│   └── tts.py                      # Google Cloud Text-to-Speech
│
├── setup_db_function.py            # 데이터베이스 함수 설정 스크립트
├── setup_db_function_psql.py       # 대체 DB 설정 (PostgreSQL)
├── seed_database.py                # 데이터베이스 시딩 스크립트
├── test_docent.py                  # API 테스트 스크립트
├── test_gemini.py                  # Gemini AI 테스트 스크립트
└── google-tts-credentials.json     # Google Cloud TTS 인증 정보
```

## 4. 아키텍처 패턴

**계층형 아키텍처 (Layered Architecture) / 서비스 지향 아키텍처 (SOA)**

```
┌─────────────────────────────────────────┐
│     Presentation Layer (Routers)        │  ← API 엔드포인트
├─────────────────────────────────────────┤
│   Business Logic Layer (Services)       │  ← AI, TTS, Storage
├─────────────────────────────────────────┤
│   Data Access Layer (DB Service)        │  ← Supabase
└─────────────────────────────────────────┘
```

### 주요 설계 원칙
- 비동기(async/await) 처리로 성능 최적화
- 서비스 레이어 분리로 유지보수성 향상
- 싱글톤 패턴으로 데이터베이스 클라이언트 관리
- RESTful API + WebSocket 하이브리드 접근

## 5. API 엔드포인트

### 5.1 메인 애플리케이션 (main.py)

```
GET  /                    # API 정보
GET  /health             # 헬스 체크
```

### 5.2 도슨트 라우터 (routers/docent.py)
**Prefix:** `/docent`

#### HTTP 엔드포인트
```
POST /docent/chat                    # AI 도슨트와 랜드마크에 대해 채팅
POST /docent/quiz                    # 퀴즈 문제 생성
POST /docent/tts                     # 텍스트-음성 변환
GET  /docent/history/{user_id}       # 채팅 이력 조회
```

#### WebSocket 엔드포인트
```
WS   /docent/ws/tts                  # WebSocket을 통한 TTS 스트리밍
WS   /docent/ws/chat                 # TTS 스트리밍이 포함된 AI 채팅
```

### 5.3 퀘스트 라우터 (routers/quest.py)
**Prefix:** `/quest`

```
GET  /quest/list                     # 모든 퀘스트 조회
POST /quest/nearby                   # 위치 근처 퀘스트 조회
POST /quest/progress                 # 퀘스트 진행 상황 업데이트
GET  /quest/user/{user_id}           # 사용자 퀘스트 조회
GET  /quest/{quest_id}               # 퀘스트 상세 정보
```

### 5.4 보상 라우터 (routers/reward.py)
**Prefix:** `/reward`

```
GET  /reward/points/{user_id}        # 사용자 포인트 잔액 조회
GET  /reward/list                    # 사용 가능한 보상 목록
POST /reward/claim                   # 보상 획득
GET  /reward/claimed/{user_id}       # 획득한 보상 조회
POST /reward/use/{reward_id}         # 보상 사용 처리
```

## 6. 데이터베이스 스키마

**데이터베이스:** Supabase (PostgreSQL)

### 6.1 테이블 구조

#### quests (퀘스트)
```sql
- id (PK)
- name (text)                # 퀘스트 이름
- description (text)          # 설명
- lat (float)                # 위도
- lon (float)                # 경도
- reward_point (integer)      # 보상 포인트
- created_at (timestamp)
```

#### user_quests (사용자-퀘스트 연결)
```sql
- id (PK)
- user_id (uuid, FK)         # 사용자 ID
- quest_id (integer, FK)      # 퀘스트 ID
- status (text)              # 'in_progress', 'completed', 'failed'
- completed_at (timestamp)
- created_at (timestamp)
```

#### points (포인트)
```sql
- id (PK)
- user_id (uuid)             # 사용자 ID
- value (integer)            # 포인트 값 (양수/음수)
- reason (text)              # 획득/사용 사유
- created_at (timestamp)
```

#### rewards (보상)
```sql
- id (PK)
- name (text)                # 보상 이름
- type (text)                # 'badge', 'coupon'
- point_cost (integer)        # 필요 포인트
- description (text)
- is_active (boolean)
- created_at (timestamp)
```

#### user_rewards (사용자-보상 연결)
```sql
- id (PK)
- user_id (uuid)
- reward_id (integer, FK)
- qr_code (text)             # 교환용 고유 토큰
- used_at (timestamp)
- claimed_at (timestamp)
```

#### chat_logs (채팅 로그)
```sql
- id (PK)
- user_id (uuid)
- landmark (text)            # 랜드마크 이름
- user_message (text)
- ai_response (text)
- created_at (timestamp)
```

### 6.2 데이터베이스 함수
- **get_user_points(user_uuid)** - 사용자의 총 포인트 반환 (points.value의 합계)

### 6.3 관계도
```
Users (1) ──── (*) user_quests (*) ──── (1) quests
Users (1) ──── (*) points
Users (1) ──── (*) user_rewards (*) ──── (1) rewards
Users (1) ──── (*) chat_logs
```

## 7. 외부 서비스 통합

### 7.1 Google Gemini AI (services/ai.py)
- **모델:** gemini-2.5-flash
- **용도:** 랜드마크에 대한 AI 도슨트 메시지 생성

**주요 함수:**
- `generate_docent_message()` - 대화형 관광 가이드 응답 생성
- `generate_quiz()` - 객관식 퀴즈 문제 생성

**기능:**
- 이중 언어 지원 (한국어/영어)
- 맥락 기반 랜드마크 정보
- 관광객과의 인터랙티브 Q&A

### 7.2 Google Cloud Text-to-Speech (services/tts.py)
- **용도:** 텍스트를 자연스러운 음성으로 변환

**주요 함수:**
- `text_to_speech_bytes()` - MP3 오디오 바이트 반환
- `text_to_speech()` - base64 인코딩된 오디오 반환
- `text_to_speech_url()` - 스토리지에 업로드하고 URL 반환

**기능:**
- 고품질 Wavenet 음성
- 한국어(ko-KR-Wavenet-A) 및 영어(en-US-Wavenet-F) 음성
- 모바일 최적화 오디오 인코딩
- WebSocket을 통한 스트리밍 지원

### 7.3 Supabase Database (services/db.py)
- **용도:** PostgreSQL 데이터베이스 호스팅

**기능:**
- 실시간 구독
- Row-level 보안
- 내장 인증
- REST API

### 7.4 Supabase Storage (services/storage.py)
- **버킷:** "tts" 버킷 (오디오 파일용)
- **용도:** TTS 오디오 파일 저장 및 제공

**주요 함수:**
- `upload_audio_to_storage()` - MP3 파일 업로드
- `delete_audio_from_storage()` - 파일 삭제
- `list_audio_files()` - 저장된 파일 목록
- `cleanup_old_files()` - 24시간 이상 된 파일 정리

**기능:**
- 공개 URL 접근
- 임시 파일 자동 정리
- 캐싱 지원

## 8. 핵심 기능

### 8.1 AI 도슨트 채팅
- 서울 랜드마크에 대한 인터랙티브 대화
- 사용자 질문 기반 맥락적 응답
- 이중 언어 지원 (한국어/영어)
- TTS를 통한 오디오 응답
- 채팅 이력 로깅

### 8.2 위치 기반 퀘스트
- GPS 기반 퀘스트 발견 (Haversine 거리 계산)
- 유명 서울 랜드마크 퀘스트 (경복궁, N서울타워 등)
- 진행 상황 추적 (in_progress, completed, failed)
- 완료 시 포인트 보상

### 8.3 게임화 시스템
- 퀘스트 완료로 포인트 획득
- 보상 카탈로그 (배지, 할인 쿠폰)
- 보상 교환용 QR 코드 생성
- 거래 내역 추적

### 8.4 WebSocket 스트리밍
- 실시간 TTS 오디오 스트리밍
- 청크 단위 오디오 전송으로 부드러운 재생
- 채팅 + TTS 통합 스트리밍
- 스트리밍 중 진행 상황 추적

### 8.5 이중 오디오 전송 모드
1. **Expo Go 모드 (prefer_url=True):** Supabase Storage에 업로드, URL 반환
2. **독립 실행형 모드 (prefer_url=False):** base64 인코딩 오디오 또는 WebSocket 스트리밍 사용

## 9. 환경 설정

### 환경 변수 (.env)
```bash
SUPABASE_URL                    # Supabase 프로젝트 URL
SUPABASE_SERVICE_KEY            # Supabase 서비스 역할 키
GEMINI_API_KEY                  # Google Gemini API 키
GOOGLE_APPLICATION_CREDENTIALS  # Google Cloud TTS 인증 정보 경로
PORT                           # 서버 포트 (기본값: 8000)
```

### 배포 설정 (render.yaml)
- **플랫폼:** Render.com
- **런타임:** Python
- **빌드:** pip install
- **시작:** uvicorn 서버
- **리전:** Oregon (아시아의 경우 Singapore)
- **플랜:** 무료 티어 사용 가능

## 10. 샘플 데이터

### 퀘스트 (서울 랜드마크 5곳)
1. 경복궁 (100 포인트)
2. N서울타워 (150 포인트)
3. 명동 (80 포인트)
4. 인사동 (90 포인트)
5. 홍대 (70 포인트)

### 보상 (5종류)
1. 서울 여행 배지 (50 포인트)
2. 카페 할인 쿠폰 (100 포인트)
3. 경복궁 입장권 (200 포인트)
4. 서울 투어 마스터 배지 (500 포인트)
5. 한복 체험 쿠폰 (300 포인트)

## 11. 아키텍처 요약

### 애플리케이션 특성
- **타입:** 퀘스트 기반 AR 관광 애플리케이션 백엔드
- **아키텍처 패턴:** 계층형 서비스 지향 아키텍처
- **API 스타일:** RESTful + WebSocket
- **데이터베이스:** PostgreSQL (Supabase)
- **AI 통합:** 대화형 AI용 Google Gemini
- **오디오 처리:** 스트리밍 지원 Google Cloud TTS
- **파일 저장소:** 오디오 파일용 Supabase Storage
- **배포:** 클라우드 준비 완료 (Render.com 호환)

### 주요 설계 결정사항
1. 성능을 위한 전체 비동기(async/await) 처리
2. 유지보수성을 위한 서비스 레이어 분리
3. Expo Go vs 독립 실행형 앱을 위한 이중 오디오 전송 모드
4. 대용량 오디오 파일의 더 나은 UX를 위한 WebSocket 스트리밍
5. Haversine 거리를 사용한 지리공간 쿼리
6. 포인트 기반 게임화 시스템
7. 데이터베이스 클라이언트용 싱글톤 패턴

## 12. 워크플로우 예시

### 전형적인 사용자 여정
```
1. 사용자가 서울 랜드마크 근처에 도착
   ↓
2. GET /quest/nearby - 근처 퀘스트 조회
   ↓
3. POST /quest/progress - 퀘스트 시작
   ↓
4. WS /docent/ws/chat - AI 도슨트와 대화
   ↓
5. POST /quest/progress - 퀘스트 완료
   ↓
6. POST /reward/claim - 포인트로 보상 획득
   ↓
7. POST /reward/use - 보상 사용 (QR 코드)
```

### 데이터 흐름
```
Client Request
    ↓
Router (Presentation)
    ↓
Service (Business Logic)
    ↓
External API / Database
    ↓
Service (Response Processing)
    ↓
Router (Response Formatting)
    ↓
Client Response
```

## 13. 보안 고려사항

- 환경 변수를 통한 API 키 관리
- Supabase Row Level Security (RLS)
- CORS 설정
- 서비스 역할 키를 사용한 데이터베이스 액세스
- TTS 오디오 파일의 자동 정리 (24시간)

## 14. 확장성 고려사항

- 비동기 처리로 높은 동시성 지원
- WebSocket을 통한 실시간 통신
- Supabase의 확장 가능한 데이터베이스
- Stateless 서버 디자인
- 클라우드 기반 외부 서비스 (AI, TTS)

---

**마지막 업데이트:** 2025년 11월
**버전:** 1.0
