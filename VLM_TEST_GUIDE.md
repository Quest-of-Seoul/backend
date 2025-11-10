# VLM 테스트 가이드

## 빠른 시작

### 1. 환경 설정

```bash
# .env 파일 설정
PINECONE_API_KEY=your-key
OPENAI_API_KEY=your-key
SUPABASE_URL=your-url
SUPABASE_SERVICE_KEY=your-key
```

### 2. 서버 실행

```bash
uvicorn main:app --reload
```

---

## 테스트 명령어

### Health Check

```bash
python test_vlm.py --health
```

**확인 사항:**
- `pinecone: true`
- `clip: true`
- `gpt4v: true`

---

### 벡터 검색 (Pinecone)

```bash
python test_vlm.py --similar test/vlm_images/bukchon_hanok_village.jpg
```

**테스트 내용:**
- CLIP 임베딩 생성
- Pinecone 유사도 검색
- 상위 3개 장소 반환

---

### 전체 VLM 분석

```bash
python test_vlm.py --analyze test/vlm_images/bukchon_hanok_village.jpg \
  --lat 37.582306 --lon 126.985302
```

**처리 흐름:**
1. CLIP 임베딩 생성
2. Pinecone 벡터 검색
3. GPS 주변 장소 검색
4. GPT-4V 이미지 분석
5. Gemini 설명 보강

---

### TTS 포함 테스트

```bash
python test_vlm.py --analyze test/vlm_images/myeongdong_cathedral.jpg \
  --lat 37.5636 --lon 126.9869 --tts
```

---

## 테스트 이미지

```
test/vlm_images/
├── bukchon_hanok_village.jpg        # 북촌한옥마을
├── bukchon_hanok_village_case1.jpg
├── bukchon_hanok_village_case2.jpg
├── myeongdong_cathedral.jpg         # 명동성당
├── myeongdong_cathedral_case1.jpg
└── myeongdong_cathedral_case2.jpg
```

**GPS 좌표:**
- 북촌: `--lat 37.582306 --lon 126.985302`
- 명동: `--lat 37.5636 --lon 126.9869`

---

## 예상 결과

```
Response received!
Description: [AI 생성 설명]
Matched Place: 북촌한옥마을
Confidence Score: 0.85
Processing Time: 2500ms

Similar Places (3):
  1. 북촌한옥마을 (similarity: 0.92)
  2. 경복궁 (similarity: 0.78)
  3. 인사동 (similarity: 0.73)
```

---

## 트러블슈팅

### Pinecone 연결 실패

```bash
python setup_pinecone.py status
```

### 벡터 없음

```bash
python seed_image_vectors.py --all
python seed_image_vectors.py --status
```

### OpenAI API 에러

→ `.env`에 `OPENAI_API_KEY` 확인

---

## 유용한 팁

**캐싱 비활성화:**
```bash
# 코드에서 use_cache=False로 설정됨
```

**다른 서버 테스트:**
```bash
python test_vlm.py --analyze image.jpg --base-url http://your-server.com
```

**주변 장소만:**
```bash
python test_vlm.py --nearby --lat 37.5796 --lon 126.9770
```

