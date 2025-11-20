# 장소 데이터 수집 가이드

TourAPI와 VISIT SEOUL API에서 장소 데이터를 수집하고 DB에 저장하는 스크립트 사용 가이드입니다.

## 사전 준비

### 1. 환경변수 설정

`.env` 파일에 다음 환경변수를 설정해야 합니다:

```bash
# TourAPI (한국관광공사)
TOUR_API_KEY=your_tour_api_key

# VISIT SEOUL API
VISIT_SEOUL_API_KEY=your_visit_seoul_api_key

# Supabase (DB)
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_KEY=your_supabase_service_key

# Pinecone (이미지 임베딩 사용 시)
PINECONE_API_KEY=your_pinecone_api_key
```

### 2. API 키 발급

- **TourAPI**: https://api.visitkorea.or.kr/ 에서 발급
- **VISIT SEOUL API**: https://api.visitseoul.net/ 에서 발급

## 기본 사용법

```bash
python scripts/collect_places.py --category <카테고리> --max-places <개수>
```

## 카테고리별 수집 명령어

### Attraction (관광지) - 추천 테마

```bash
# 기본 (50개, 이미지 임베딩 포함)
python scripts/collect_places.py --category Attraction --max-places 50

# 더 많이 수집 (100개)
python scripts/collect_places.py --category Attraction --max-places 100

# 이미지 임베딩 없이 수집 (빠른 수집)
python scripts/collect_places.py --category Attraction --max-places 50 --no-embeddings
```

### Culture (문화시설) - 추천 테마

```bash
# 기본 (50개)
python scripts/collect_places.py --category Culture --max-places 50

# 더 많이 수집
python scripts/collect_places.py --category Culture --max-places 100
```

### Events (축제/공연/행사)

```bash
python scripts/collect_places.py --category Events --max-places 50
```

### Shopping (쇼핑)

```bash
python scripts/collect_places.py --category Shopping --max-places 50
```

### Food (음식점)

```bash
python scripts/collect_places.py --category Food --max-places 50
```

### Extreme (레포츠/체험)

```bash
python scripts/collect_places.py --category Extreme --max-places 50
```

### Sleep (숙박)

```bash
python scripts/collect_places.py --category Sleep --max-places 50
```

## 옵션 설명

### 필수 옵션

- `--category`: 수집할 카테고리
  - 선택 가능: `Attraction`, `Culture`, `Events`, `Shopping`, `Food`, `Extreme`, `Sleep`
  - 예: `--category Attraction`

### 선택 옵션

- `--max-places`: 최대 수집 장소 수 (기본값: 50)
  - 예: `--max-places 100`

- `--area-code`: 지역코드 (기본값: "1" = 서울)
  - 서울: "1"
  - 예: `--area-code 1`

- `--delay`: API 호출 간 지연 시간 초 (기본값: 0.5)
  - API 호출 제한을 피하기 위해 사용
  - 예: `--delay 1.0` (1초 대기)

- `--no-embeddings`: 이미지 임베딩 생성 건너뛰기
  - 이미지 임베딩 생성 없이 데이터만 수집 (더 빠름)
  - 예: `--no-embeddings`

## 수집 프로세스

스크립트는 다음 단계로 진행됩니다:

1. **TourAPI 장소 수집** - 카테고리별 장소 리스트 조회
2. **TourAPI 상세 정보 수집** - 각 장소의 상세 정보 및 이용안내 조회
3. **VISIT SEOUL 장소 수집** - 매칭을 위한 장소 리스트 조회
4. **VISIT SEOUL 상세 정보 수집** - 각 장소의 상세 정보 조회
5. **데이터 매칭** - 장소명 유사도 및 좌표 거리 기반 매칭
6. **데이터 통합 및 저장** - 두 API 데이터 통합 후 DB 저장
7. **퀘스트 생성** - 저장된 장소로부터 자동 퀘스트 생성
8. **이미지 임베딩 생성** - 이미지 다운로드 → 임베딩 생성 → Pinecone 저장

## 출력 통계

수집 완료 후 다음 통계가 출력됩니다:

```
Collection Statistics:
  Category: Attraction
  TourAPI places collected: 50
  VISIT SEOUL places collected: 120
  Places matched: 35
  Places saved: 50
  Quests created: 50
  Embeddings created: 48
  Errors: 2
```

- **TourAPI places collected**: TourAPI에서 수집된 장소 수
- **VISIT SEOUL places collected**: VISIT SEOUL API에서 수집된 장소 수
- **Places matched**: 두 API에서 매칭된 장소 수
- **Places saved**: DB에 저장된 장소 수
- **Quests created**: 생성된 퀘스트 수
- **Embeddings created**: 생성된 이미지 임베딩 수
- **Errors**: 발생한 에러 수
