# Quest of Seoul - AI Service Backend

FastAPI 기반 AI 서비스 백엔드

## 개요

AI 기능 전담 마이크로서비스
- VLM 이미지 분석 (GPT-4V)
- AI 도슨트 (Gemini)
- AI 장소 추천 시스템 (CLIP + Pinecone)
- TTS (Google Cloud)
- 벡터 검색 (Pinecone)

## 아키텍처

```
Client (iOS/Android)
    ↓
FastAPI Backend
    ├── Supabase (PostgreSQL)
    ├── Pinecone (Vector DB)
    ├── OpenAI (GPT-4o-mini)
    ├── Google Gemini (AI Docent)
    └── Google Cloud TTS
```

## 프로젝트 구조

```
backend/
├── main.py                   # FastAPI 앱
├── requirements.txt          # 의존성
├── .env.example             # 환경변수 예시
├── render.yaml              # 배포 설정
├── google-tts-credentials.json
│
├── database/
│   ├── supabase_schema.sql  # PostgreSQL 스키마
│   └── pinecone_schema.py   # 벡터 DB 초기화
│
├── routers/                 # API 라우터
│   ├── docent.py           # AI 도슨트
│   ├── vlm.py              # 이미지 분석
│   ├── recommend.py        # 추천 시스템
│   ├── quest.py            # 퀘스트 관리
│   └── reward.py           # 리워드 시스템
│
├── services/                # 비즈니스 로직
│   ├── ai.py               # Gemini AI
│   ├── vlm.py              # GPT-4o-mini
│   ├── embedding.py        # CLIP 임베딩
│   ├── recommendation.py   # 추천 알고리즘
│   ├── pinecone_store.py   # 벡터 DB
│   ├── db.py               # Supabase 클라이언트
│   ├── storage.py          # 파일 스토리지
│   ├── tts.py              # TTS
│   └── optimized_search.py # 최적화 검색
│
└── scripts/
    ├── test_api.py         # API 테스트
    └── README.md           # 테스트 가이드
```

## 시작하기

### 1. 환경 설정

`.env` 파일 생성:

```bash
# Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-supabase-service-key

# Vector Database
PINECONE_API_KEY=your-pinecone-api-key

# AI Services
OPENAI_API_KEY=sk-your-openai-api-key
GOOGLE_API_KEY=your-google-api-key

# Text-to-Speech
GOOGLE_APPLICATION_CREDENTIALS=./google-tts-credentials.json

# Server
PORT=8000

# Optional
PRELOAD_CLIP_MODEL=false
```

### 2. 설치

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. 데이터베이스 초기화

```bash
# Supabase SQL Editor에서 스키마 실행
# database/supabase_schema.sql

# Pinecone 인덱스 생성
python database/pinecone_schema.py
```

### 4. 서버 실행

```bash
python main.py
```

API 문서:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 환경 변수

| 변수 | 설명 | 필수 |
|------|------|------|
| SUPABASE_URL | Supabase 프로젝트 URL | 필수 |
| SUPABASE_SERVICE_KEY | Supabase 서비스 키 | 필수 |
| PINECONE_API_KEY | Pinecone API 키 | 필수 |
| OPENAI_API_KEY | OpenAI API 키 (GPT-4o-mini) | 필수 |
| GOOGLE_API_KEY | Google Gemini API 키 | 필수 |
| GOOGLE_APPLICATION_CREDENTIALS | TTS 인증 파일 경로 | 필수 |
| PORT | 서버 포트 | 선택 (기본: 8000) |
| PRELOAD_CLIP_MODEL | CLIP 모델 사전 로드 | 선택 (기본: false) |

## 주요 기술

- **FastAPI**: 웹 프레임워크
- **Supabase**: PostgreSQL 데이터베이스
- **Pinecone**: 벡터 검색
- **GPT-4o-mini**: 이미지 분석 (비용 효율적)
- **Gemini 2.5 Flash**: AI 도슨트
- **CLIP**: 이미지 임베딩 (512차원)
- **Google Cloud TTS**: 음성 합성

## 배포

```bash
git push origin main
```

Render.com에서 자동 배포 (`render.yaml` 사용)

## 라이선스

MIT License