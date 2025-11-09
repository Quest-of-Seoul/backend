# 백엔드 아키텍처 분석

## 1. 개요

Quest of Seoul의 백엔드는 FastAPI 프레임워크를 사용한 위치 기반 AR 관광 애플리케이션 서버입니다. AI 기반 도슨트, VLM 이미지 분석, 게임화된 퀘스트 시스템, 그리고 보상 메커니즘을 제공합니다.

## 2. 기술 스택

### 핵심 프레임워크
- **FastAPI** (v0.115.0) - 현대적이고 빠른 비동기 웹 프레임워크
- **Uvicorn** (v0.32.0) - ASGI 서버
- **Python 3.x** - 런타임 환경

### 주요 라이브러리
- **Supabase** (v2.9.1) - PostgreSQL 데이터베이스 및 스토리지 (pgvector 확장)
- **OpenAI** (v1.0.0+) - GPT-4V Vision API (이미지 분석)
- **Google Gemini AI** (v0.8.3) - 대화형 AI (gemini-2.5-flash 모델)
- **Google Cloud TTS** (v2.18.0) - 음성 합성
- **Transformers** (v4.30.0+) - CLIP 이미지 임베딩
- **PyTorch** (v2.0.0+) - 딥러닝 프레임워크
- **Pydantic** (v2.9.2) - 데이터 검증
- **WebSockets** (v12.0) - 실시간 통신
- **Pillow** (v10.0.0+) - 이미지 처리

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
│   ├── reward.py                   # 보상/포인트 엔드포인트
│   └── vlm.py                      # VLM 이미지 분석 엔드포인트
│
├── services/                        # 비즈니스 로직 서비스
│   ├── __init__.py
│   ├── ai.py                       # Google Gemini AI 통합
│   ├── db.py                       # Supabase 데이터베이스 클라이언트
│   ├── embedding.py                # CLIP 이미지 임베딩
│   ├── storage.py                  # Supabase Storage (파일 업로드)
│   ├── tts.py                      # Google Cloud Text-to-Speech
│   └── vlm.py                      # GPT-4V Vision API 통합
│
├── setup_db_function.py            # 데이터베이스 함수 설정 스크립트
├── setup_db_function_psql.py       # 대체 DB 설정 (PostgreSQL)
├── setup_vlm_schema.sql            # VLM 데이터베이스 스키마 (pgvector)
├── seed_database.py                # 데이터베이스 시딩 스크립트
├── seed_image_vectors.py           # 이미지 임베딩 배치 생성 스크립트
├── test_docent.py                  # API 테스트 스크립트
├── test_gemini.py                  # Gemini AI 테스트 스크립트
├── test_vlm.py                     # VLM API 테스트 스크립트
├── google-tts-credentials.json     # Google Cloud TTS 인증 정보
└── VLM_SETUP_GUIDE.md              # VLM 시스템 설정 가이드
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
GET  /reward/points/{user_id}        # 사용자 포인트 잔액 및 거래 내역 조회
POST /reward/points/add              # 사용자에게 포인트 추가 (수동 지급)
GET  /reward/list                    # 사용 가능한 보상 목록
POST /reward/claim                   # 보상 획득
GET  /reward/claimed/{user_id}       # 획득한 보상 조회
POST /reward/use/{reward_id}         # 보상 사용 처리
```

### 5.5 VLM 이미지 분석 라우터 (routers/vlm.py)
**Prefix:** `/vlm`

```
POST /vlm/analyze                    # AR 카메라 이미지 분석 (base64)
POST /vlm/analyze-multipart          # 이미지 분석 (multipart/form-data)
POST /vlm/similar                    # 유사 이미지 검색 (벡터 검색)
POST /vlm/embed                      # 이미지 임베딩 생성 (관리자용)
GET  /vlm/places/nearby              # GPS 기반 주변 장소 조회
GET  /vlm/health                     # VLM 서비스 상태 확인
```

#### 주요 엔드포인트 상세

**GET /reward/points/{user_id}**
- 사용자의 총 포인트 잔액 조회 (get_user_points 함수 사용)
- 최근 거래 내역 10건 반환
- 응답: `{ total_points: number, transactions: array }`

**POST /reward/points/add**
- 요청: `{ user_id: string, points: number, reason: string }`
- 사용자에게 포인트 수동 지급 (관리자/이벤트용)
- 사용자가 없으면 자동으로 users 테이블에 생성
- 응답: 이전 잔액, 새 잔액, 추가된 포인트 반환

**POST /reward/claim**
- 요청: `{ user_id: string, reward_id: number }`
- 포인트 충분 여부 확인 후 보상 획득
- 포인트 차감 (음수 값으로 points 테이블에 기록)
- QR 코드 토큰 생성 (16바이트 URL-safe)
- user_rewards 테이블에 기록

**POST /vlm/analyze**
- 요청: `{ user_id: string, image: base64, latitude: float, longitude: float, language: string, enable_tts: boolean }`
- AR 카메라로 촬영한 이미지를 GPT-4V로 분석
- GPS 기반 주변 장소 검색 (반경 1km)
- CLIP 임베딩 생성 및 벡터 유사도 검색
- Gemini로 최종 설명 보강
- TTS 오디오 생성 (선택적)
- 응답: 장소 정보, 설명, 유사 이미지, 신뢰도 점수, 오디오 URL
- 처리 시간: 평균 5-12초 (VLM API 호출 포함)

**POST /vlm/similar**
- 요청: `{ image: base64, limit: int, threshold: float }`
- 이미지와 유사한 장소 사진을 벡터 검색
- pgvector 코사인 유사도 기반
- 응답: 유사 이미지 목록 (장소 정보 포함)

## 6. 데이터베이스 스키마

**데이터베이스:** Supabase (PostgreSQL)

### 6.1 테이블 구조

#### users (사용자)
```sql
- id (PK, uuid)              # 사용자 고유 ID
- email (text)               # 이메일
- nickname (text)            # 닉네임
- created_at (timestamp)
```

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

#### places (장소 - VLM용)
```sql
- id (PK, uuid)
- name (text)               # 장소명 (한글)
- name_en (text)            # 영문명
- description (text)         # 장소 설명
- category (text)           # 카테고리 (관광지, 음식점 등)
- address (text)            # 주소
- latitude (decimal)        # 위도
- longitude (decimal)       # 경도
- image_url (text)          # 대표 이미지 URL
- images (text[])           # 추가 이미지 URL 배열
- metadata (jsonb)          # 추가 메타정보
- view_count (integer)      # 조회수
- is_active (boolean)
- created_at (timestamp)
```

#### image_vectors (이미지 임베딩 - VLM용)
```sql
- id (PK, uuid)
- place_id (uuid, FK)       # places.id
- image_url (text)          # 이미지 URL
- image_hash (text)         # 이미지 해시 (중복 방지)
- embedding (vector(512))   # CLIP 임베딩 (512차원)
- source (text)             # 출처 (dataset, user_upload)
- metadata (jsonb)
- created_at (timestamp)
```

#### vlm_logs (VLM 분석 로그)
```sql
- id (PK, uuid)
- user_id (text)
- image_url (text)          # 업로드된 이미지 URL
- image_hash (text)         # 이미지 해시 (캐싱용)
- latitude (decimal)        # 촬영 위치
- longitude (decimal)
- vlm_provider (text)       # VLM 제공자 (gpt4v)
- vlm_response (text)       # VLM 원본 응답
- final_description (text)   # 최종 설명 (Gemini 보강)
- matched_place_id (uuid, FK) # 매칭된 장소
- similar_places (jsonb)    # 유사 장소 목록
- confidence_score (decimal) # 신뢰도 점수 (0.0-1.0)
- processing_time_ms (integer) # 처리 시간
- error_message (text)
- created_at (timestamp)
```

### 6.2 데이터베이스 함수
- **get_user_points(user_uuid)** - 사용자의 총 포인트 반환 (points.value의 합계)
- **search_similar_images(query_embedding, match_threshold, match_count)** - 벡터 유사도 검색 (pgvector)
- **search_places_by_radius(lat, lon, radius_km, limit_count)** - GPS 반경 내 장소 검색

### 6.3 관계도
```
users (1) ──── (*) user_quests (*) ──── (1) quests
users (1) ──── (*) points
users (1) ──── (*) user_rewards (*) ──── (1) rewards
users (1) ──── (*) chat_logs

places (1) ──── (*) image_vectors
places (1) ──── (*) vlm_logs
```

### 6.4 pgvector 확장
- **vector(512)** - 512차원 임베딩 벡터 타입
- **코사인 유사도 검색** - `<=>` 연산자 사용
- **IVFFlat 인덱스** - 벡터 검색 성능 최적화 (lists=100)

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

### 7.5 OpenAI GPT-4V (services/vlm.py)
- **모델:** gpt-4o (Vision 기능 포함)
- **용도:** AR 카메라 이미지 분석 및 장소 식별

**주요 함수:**
- `analyze_image_gpt4v()` - 이미지 분석 (base64 입력)
- `analyze_place_image()` - 장소 이미지 종합 분석
- `extract_place_info_from_vlm_response()` - VLM 응답 파싱
- `calculate_confidence_score()` - 종합 신뢰도 점수 계산

**기능:**
- 고해상도 이미지 분석 (detail="high")
- 이미지 자동 압축 (1024x1024 이하)
- GPS 기반 주변 장소 정보 통합
- 구조화된 응답 형식 (장소명, 카테고리, 설명, 신뢰도)

### 7.6 CLIP 이미지 임베딩 (services/embedding.py)
- **모델:** openai/clip-vit-base-patch32
- **용도:** 이미지를 512차원 벡터로 변환

**주요 함수:**
- `generate_image_embedding()` - 단일 이미지 임베딩 생성
- `generate_embeddings_batch()` - 배치 임베딩 생성 (효율적)
- `calculate_cosine_similarity()` - 벡터 유사도 계산
- `hash_image()` - 이미지 SHA-256 해시 생성

**기능:**
- CPU/GPU 자동 선택
- 배치 처리 지원 (기본 8개)
- 모델 싱글톤 패턴 (메모리 최적화)
- L2 정규화된 임베딩

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
- 수동 포인트 지급 기능 (관리자/이벤트용)
- 포인트 잔액 조회 및 거래 내역 추적
- 보상 카탈로그 (배지, 할인 쿠폰)
- 보상 교환용 QR 코드 생성
- 사용자 자동 생성 (첫 포인트 추가 시)

### 8.4 WebSocket 스트리밍
- 실시간 TTS 오디오 스트리밍
- 청크 단위 오디오 전송으로 부드러운 재생
- 채팅 + TTS 통합 스트리밍
- 스트리밍 중 진행 상황 추적

### 8.5 이중 오디오 전송 모드
1. **Expo Go 모드 (prefer_url=True):** Supabase Storage에 업로드, URL 반환
2. **독립 실행형 모드 (prefer_url=False):** base64 인코딩 오디오 또는 WebSocket 스트리밍 사용

### 8.6 VLM 이미지 분석 시스템
- AR 카메라 촬영 이미지 자동 분석
- GPT-4V를 통한 장소 식별 및 설명 생성
- CLIP 기반 벡터 유사도 검색
- GPS + 벡터 + VLM 하이브리드 매칭
- 신뢰도 점수 계산 (VLM 40% + 벡터 40% + GPS 20%)
- 이미지 해시 기반 캐싱 (24시간)
- Gemini를 통한 최종 설명 보강
- 처리 시간: 평균 5-12초

**처리 흐름:**
```
1. 이미지 수신 (base64 or multipart)
   ↓
2. 이미지 해시 생성 → 캐싱 체크
   ↓
3. GPS 기반 주변 장소 검색 (반경 1km)
   ↓
4. CLIP 임베딩 생성 (512차원)
   ↓
5. pgvector 유사도 검색 (Top-3)
   ↓
6. GPT-4V API 호출 (이미지 분석)
   ↓
7. 장소 매칭 (이름 + 벡터 검색)
   ↓
8. Gemini로 최종 설명 보강
   ↓
9. TTS 생성 (선택적)
   ↓
10. vlm_logs 테이블에 저장
```

## 9. 환경 설정

### 환경 변수 (.env)
```bash
SUPABASE_URL                    # Supabase 프로젝트 URL
SUPABASE_SERVICE_KEY            # Supabase 서비스 역할 키
OPENAI_API_KEY                  # OpenAI GPT-4V API 키 (이미지 분석 필수)
GEMINI_API_KEY                  # Google Gemini API 키
GOOGLE_APPLICATION_CREDENTIALS  # Google Cloud TTS 인증 정보 경로
PRELOAD_CLIP_MODEL             # CLIP 모델 사전 로드 (true/false, 기본값: false)
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
- **타입:** VLM 이미지 분석 기반 AR 관광 애플리케이션 백엔드
- **아키텍처 패턴:** 계층형 서비스 지향 아키텍처
- **API 스타일:** RESTful + WebSocket
- **데이터베이스:** PostgreSQL (Supabase) + pgvector 확장
- **AI 통합:** 
  - GPT-4V (이미지 분석)
  - Google Gemini (대화형 AI, 텍스트 보강)
  - CLIP (이미지 임베딩)
- **오디오 처리:** 스트리밍 지원 Google Cloud TTS
- **파일 저장소:** Supabase Storage (오디오, 이미지)
- **벡터 검색:** pgvector (코사인 유사도)
- **배포:** 클라우드 준비 완료 (Render.com 호환)

### 주요 설계 결정사항
1. 성능을 위한 전체 비동기(async/await) 처리
2. 유지보수성을 위한 서비스 레이어 분리
3. GPT-4V 단독 사용 (이미지 분석 정확도 최적화)
4. CLIP 기반 벡터 검색 + GPS + VLM 하이브리드 매칭
5. pgvector를 사용한 고속 벡터 유사도 검색
6. 이미지 해시 기반 캐싱으로 VLM API 비용 절감
7. Expo Go vs 독립 실행형 앱을 위한 이중 오디오 전송 모드
8. 대용량 오디오 파일의 더 나은 UX를 위한 WebSocket 스트리밍
9. Haversine 거리를 사용한 지리공간 쿼리
10. 포인트 기반 게임화 시스템
11. 데이터베이스 클라이언트용 싱글톤 패턴
12. CLIP 모델 싱글톤으로 메모리 최적화

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
5. POST /quest/progress - 퀘스트 완료 (자동으로 포인트 적립)
   ↓
6. GET /reward/points/{user_id} - 포인트 잔액 및 거래 내역 확인
   ↓
7. POST /reward/claim - 포인트로 보상 획득
   ↓
8. POST /reward/use - 보상 사용 (QR 코드)
```

### AR 카메라 이미지 분석 워크플로우
```
1. 사용자가 AR 카메라로 장소 촬영
   ↓
2. POST /vlm/analyze - 이미지 + GPS 좌표 전송
   ↓
3. 백엔드 처리:
   - 이미지 해시 생성 및 캐싱 확인
   - GPS 기반 주변 장소 검색 (1km 반경)
   - CLIP 임베딩 생성 및 벡터 검색
   - GPT-4V로 이미지 분석
   - 장소 매칭 및 신뢰도 계산
   - Gemini로 최종 설명 보강
   - TTS 오디오 생성 (선택적)
   ↓
4. 클라이언트 응답:
   - 장소 정보 (이름, 카테고리, 주소)
   - AI 생성 설명 (3-4문장)
   - 유사 장소 이미지 (Top-3)
   - 신뢰도 점수
   - 오디오 URL (TTS 활성화시)
   ↓
5. 사용자가 장소 정보와 설명을 확인하고 오디오 재생
```

### 포인트 관리 워크플로우
```
1. 관리자/이벤트: POST /reward/points/add - 사용자에게 포인트 수동 지급
   ↓
2. 시스템: 사용자가 없으면 자동 생성 (users 테이블)
   ↓
3. GET /reward/points/{user_id} - 포인트 잔액 확인
   ↓
4. 응답: 총 포인트 + 최근 거래 내역 10건
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

**마지막 업데이트:** 2025년 11월 9일
**버전:** 1.2

## 변경 이력

### v1.2 (2025-11-09)
- **VLM 이미지 분석 시스템 추가**
  - OpenAI GPT-4V Vision API 통합
  - CLIP 기반 이미지 임베딩 및 벡터 검색
  - pgvector 확장 및 유사도 검색
  - `places`, `image_vectors`, `vlm_logs` 테이블 추가
  - `/vlm` 라우터 및 6개 엔드포인트 추가
  - GPS + 벡터 + VLM 하이브리드 장소 매칭
  - 이미지 해시 기반 캐싱 시스템
  - 신뢰도 점수 계산 알고리즘
  - AR 카메라 이미지 분석 워크플로우
- `services/vlm.py` 추가 (GPT-4V 통합)
- `services/embedding.py` 추가 (CLIP 임베딩)
- `setup_vlm_schema.sql` 추가 (VLM DB 스키마)
- `seed_image_vectors.py` 추가 (이미지 임베딩 배치 생성)
- `test_vlm.py` 추가 (VLM API 테스트)
- `VLM_SETUP_GUIDE.md` 추가 (VLM 설정 가이드)
- 기술 스택 업데이트 (OpenAI, Transformers, PyTorch, Pillow)
- 환경 변수에 `OPENAI_API_KEY`, `PRELOAD_CLIP_MODEL` 추가

### v1.1 (2025-11-09)
- `users` 테이블 추가 (사용자 관리)
- `POST /reward/points/add` 엔드포인트 추가 (수동 포인트 지급)
- `GET /reward/points/{user_id}` 응답에 거래 내역 추가
- 사용자 자동 생성 기능 추가
- API 엔드포인트 상세 설명 추가
- 포인트 관리 워크플로우 추가

### v1.0 (2025-11)
- 초기 백엔드 아키텍처 문서 작성
