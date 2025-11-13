# API Test Scripts

Quest of Seoul 백엔드 API 테스트 가이드

## test_api.py

모든 API 엔드포인트를 테스트하는 통합 스크립트

### 사전 준비

```bash
# 서버 실행 (별도 터미널)
python main.py

# 테스트 이미지 준비 (선택)
# 이미지 기반 테스트를 위해 JPEG/PNG 파일 필요
```

---

## 사용법

### 기본 테스트

```bash
# 서버 상태 확인
python scripts/test_api.py --root
python scripts/test_api.py --health

# 모든 테스트 실행 (이미지 제외)
python scripts/test_api.py --all

# 모든 테스트 실행 (이미지 포함)
python scripts/test_api.py --full --image ./test.jpg
```

---

## 기능별 테스트

### 1. Docent (AI 도슨트)

```bash
# 전체 도슨트 기능 테스트
python scripts/test_api.py --docent

# 개별 테스트
python scripts/test_api.py --docent-chat      # AI 대화
python scripts/test_api.py --docent-quiz      # 퀴즈 생성
python scripts/test_api.py --docent-tts       # TTS 생성
python scripts/test_api.py --docent-history   # 대화 기록
```

**테스트 내용:**
- POST /docent/chat - AI 도슨트 대화
- POST /docent/quiz - 퀴즈 생성
- POST /docent/tts - TTS 생성
- GET /docent/history/{user_id} - 대화 기록

---

### 2. Quest (퀘스트 시스템)

```bash
# 전체 퀘스트 기능 테스트
python scripts/test_api.py --quest

# 개별 테스트
python scripts/test_api.py --quest-list        # 퀘스트 목록
python scripts/test_api.py --quest-nearby      # 주변 퀘스트
python scripts/test_api.py --quest-progress    # 진행 상황
python scripts/test_api.py --quest-user        # 사용자 퀘스트
python scripts/test_api.py --quest-detail      # 퀘스트 상세
```

**테스트 내용:**
- GET /quest/list - 퀘스트 목록
- POST /quest/nearby - 주변 퀘스트
- POST /quest/progress - 진행 상황 업데이트
- GET /quest/user/{user_id} - 사용자 퀘스트
- GET /quest/{quest_id} - 퀘스트 상세

---

### 3. Reward (리워드 시스템)

```bash
# 전체 리워드 기능 테스트
python scripts/test_api.py --reward

# 개별 테스트
python scripts/test_api.py --reward-points     # 포인트 조회
python scripts/test_api.py --reward-add        # 포인트 추가
python scripts/test_api.py --reward-list       # 리워드 목록
python scripts/test_api.py --reward-claimed    # 획득한 리워드
python scripts/test_api.py --reward-claim      # 리워드 획득
python scripts/test_api.py --reward-use        # 리워드 사용
```

**테스트 내용:**
- GET /reward/points/{user_id} - 포인트 조회
- POST /reward/points/add - 포인트 추가
- GET /reward/list - 리워드 목록
- POST /reward/claim - 리워드 획득
- GET /reward/claimed/{user_id} - 획득한 리워드
- POST /reward/use/{reward_id} - 리워드 사용

---

### 4. VLM (이미지 분석)

```bash
# 전체 VLM 기능 테스트 (이미지 필수)
python scripts/test_api.py --vlm --image ./test.jpg

# 개별 테스트
python scripts/test_api.py --vlm-analyze --image ./test.jpg    # 이미지 분석
python scripts/test_api.py --vlm-similar --image ./test.jpg    # 유사 이미지
python scripts/test_api.py --vlm-nearby                        # 주변 장소
python scripts/test_api.py --vlm-health                        # 상태 확인
```

**테스트 내용:**
- POST /vlm/analyze - 이미지 분석
- POST /vlm/similar - 유사 이미지 검색
- GET /vlm/places/nearby - 주변 장소
- GET /vlm/health - 서비스 상태

---

### 5. Recommend (추천 시스템)

```bash
# 전체 추천 기능 테스트
python scripts/test_api.py --recommend

# 개별 테스트
python scripts/test_api.py --recommend-places --image ./test.jpg    # 장소 추천
python scripts/test_api.py --recommend-quests                       # 주변 퀘스트
python scripts/test_api.py --recommend-category                     # 카테고리별
python scripts/test_api.py --recommend-quest-detail                 # 퀘스트 상세
python scripts/test_api.py --recommend-submit                       # 퀴즈 제출
python scripts/test_api.py --recommend-stats                        # 통계
```

**테스트 내용:**
- POST /recommend/similar-places - 장소 추천
- GET /recommend/nearby-quests - 주변 퀘스트
- GET /recommend/quests/category/{category} - 카테고리별 퀘스트
- GET /recommend/quests/{quest_id} - 퀘스트 상세
- POST /recommend/quests/{quest_id}/submit - 퀴즈 제출
- GET /recommend/stats - 통계

---

## 커스텀 설정

### 서버 URL 변경

```bash
python scripts/test_api.py --url http://your-server.com --all
```

### 테스트 사용자 ID 변경

스크립트 내 `TEST_USER_ID` 변수 수정

---

## 전체 엔드포인트 목록

### 총 29개 엔드포인트

**Docent (6개)**
1. POST /docent/chat
2. POST /docent/quiz
3. POST /docent/tts
4. GET /docent/history/{user_id}
5. WebSocket /docent/ws/tts
6. WebSocket /docent/ws/chat

**Quest (5개)**
1. GET /quest/list
2. POST /quest/nearby
3. POST /quest/progress
4. GET /quest/user/{user_id}
5. GET /quest/{quest_id}

**Reward (6개)**
1. GET /reward/points/{user_id}
2. POST /reward/points/add
3. GET /reward/list
4. POST /reward/claim
5. GET /reward/claimed/{user_id}
6. POST /reward/use/{reward_id}

**VLM (6개)**
1. POST /vlm/analyze
2. POST /vlm/analyze-multipart
3. POST /vlm/similar
4. POST /vlm/embed
5. GET /vlm/places/nearby
6. GET /vlm/health

**Recommend (6개)**
1. POST /recommend/similar-places
2. GET /recommend/nearby-quests
3. GET /recommend/quests/category/{category}
4. GET /recommend/quests/{quest_id}
5. POST /recommend/quests/{quest_id}/submit
6. GET /recommend/stats

---

## 트러블슈팅

### Connection Error

```
Error: Cannot connect to http://localhost:8000
```

**해결:** 서버가 실행 중인지 확인
```bash
python main.py
```

### Image Not Found

```
Image not found: ./test.jpg
```

**해결:** 올바른 이미지 경로 지정

### API Key Error

```
Error: OPENAI_API_KEY not set
```

**해결:** .env 파일 확인 및 환경 변수 설정

---

## 예제

### 기본 워크플로우

```bash
# 1. 서버 상태 확인
python scripts/test_api.py --health

# 2. 도슨트 기능 테스트
python scripts/test_api.py --docent

# 3. 퀘스트 시스템 테스트
python scripts/test_api.py --quest

# 4. 이미지 분석 테스트
python scripts/test_api.py --vlm-analyze --image ./test.jpg

# 5. 추천 시스템 테스트
python scripts/test_api.py --recommend-places --image ./test.jpg
```

### 전체 통합 테스트

```bash
# 이미지 제외 전체 테스트
python scripts/test_api.py --all

# 이미지 포함 전체 테스트
python scripts/test_api.py --full --image ./test.jpg
```

---

## 참고

- API 문서: `/API_DOCS.md`
- Swagger UI: `http://localhost:8000/docs`
- 환경 변수: `/.env.example`
