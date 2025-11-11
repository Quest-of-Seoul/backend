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
Spring Boot (비즈니스 로직)
    ↓
FastAPI (AI 서비스)
    ↓
Pinecone (벡터 DB)
```

## 프로젝트 구조

```
backend/
├── database/
│   ├── mysql_schema.sql
│   └── pinecone_schema.py
├── routers/
│   ├── vlm.py
│   ├── docent.py
│   └── recommend.py
├── services/
│   ├── ai.py
│   ├── vlm.py
│   ├── embedding.py
│   ├── pinecone_store.py
│   ├── recommendation.py
│   └── tts.py
├── scripts/
│   └── test_api.py
├── main.py
└── requirements.txt
```

## 시작하기

### 1. 환경 설정

`.env` 파일 생성:

```bash
OPENAI_API_KEY=sk-your-key
GOOGLE_API_KEY=your-key
GOOGLE_APPLICATION_CREDENTIALS=./google-tts-credentials.json
PINECONE_API_KEY=your-key
PORT=8000
```

### 2. 설치

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Pinecone 초기화

```bash
python database/pinecone_schema.py
```

### 4. 서버 실행

```bash
python main.py
```

API 문서: http://localhost:8000/docs

## 환경 변수

| 변수 | 설명 | 필수 |
|------|------|------|
| OPENAI_API_KEY | GPT-4V API 키 | ✅ |
| GOOGLE_API_KEY | Gemini API 키 | ✅ |
| GOOGLE_APPLICATION_CREDENTIALS | TTS 인증 파일 경로 | ✅ |
| PINECONE_API_KEY | Pinecone API 키 | ✅ |
| PORT | 서버 포트 | ⚪ (기본: 8000) |

## 주요 기술

- **FastAPI**: 웹 프레임워크
- **GPT-4V**: 이미지 분석
- **Gemini**: 텍스트 생성
- **CLIP**: 이미지 임베딩 (512차원)
- **Pinecone**: 벡터 검색
- **Google Cloud TTS**: 음성 합성

## 배포

```bash
git push origin main
```

Render.com에서 자동 배포 (`render.yaml` 사용)

## 라이선스

MIT License
