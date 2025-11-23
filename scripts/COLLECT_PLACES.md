# 장소 데이터 수집 가이드

VISIT SEOUL API에서 장소 데이터를 수집하고 DB에 저장하는 스크립트 사용 가이드입니다.

## 사전 준비

### 1. 환경변수 설정

`.env` 파일에 다음 환경변수를 설정해야 합니다:

```bash
# VISIT SEOUL API
VISIT_SEOUL_API_KEY=your_visit_seoul_api_key

# Supabase (DB)
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_KEY=your_supabase_service_key

# Pinecone (이미지 임베딩 사용 시)
PINECONE_API_KEY=your_pinecone_api_key
```

### 2. API 키 발급

- **VISIT SEOUL API**: https://api.visitseoul.net/ 에서 발급

## 기본 사용법

```bash
python scripts/collect_places.py --category <카테고리> --max-places <개수>
```

## 카테고리별 수집 명령어

### Attractions (도시의 대표 관광명소) - 추천 테마

랜드마크, 테마공원, 핫플레이스 등

```bash
# 기본 (50개, 이미지 임베딩 포함)
python scripts/collect_places.py --category Attractions --max-places 50

# 더 많이 수집 (100개)
python scripts/collect_places.py --category Attractions --max-places 100

# 이미지 임베딩 없이 수집 (빠른 수집)
python scripts/collect_places.py --category Attractions --max-places 50 --no-embeddings
```

### History (역사·유적지·궁·전통 공간)

```bash
python scripts/collect_places.py --category History --max-places 50
```

### Culture (박물관·미술관 전시·공연 등 문화시설) - 추천 테마

```bash
# 기본 (50개)
python scripts/collect_places.py --category Culture --max-places 50

# 더 많이 수집
python scripts/collect_places.py --category Culture --max-places 100
```

### Nature (공원·산·강·자연풍경)

```bash
python scripts/collect_places.py --category Nature --max-places 50
```

### Food (식당·길거리음식·현지 맛집)

카페/찻집, 주점 제외

```bash
python scripts/collect_places.py --category Food --max-places 50
```

### Drinks (카페·티하우스·바(주점))

```bash
python scripts/collect_places.py --category Drinks --max-places 50
```

### Shopping (쇼핑·시장·상점가)

```bash
python scripts/collect_places.py --category Shopping --max-places 50
```

### Activities (체험·클래스·액티비티)

```bash
python scripts/collect_places.py --category Activities --max-places 50
```

### Events (축제·공연·행사)

```bash
python scripts/collect_places.py --category Events --max-places 50
```

## 옵션 설명

### 필수 옵션

- `--category`: 수집할 카테고리
  - 선택 가능: `Attractions`, `History`, `Culture`, `Nature`, `Food`, `Drinks`, `Shopping`, `Activities`, `Events`
  - 예: `--category Attractions`

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

1. **VISIT SEOUL 장소 수집** - 카테고리별 장소 리스트 조회 (영문)
2. **VISIT SEOUL 상세 정보 수집** - 각 장소의 상세 정보 조회
3. **데이터 저장** - 장소 데이터를 DB에 저장
4. **퀘스트 생성** - 저장된 장소로부터 자동 퀘스트 생성
5. **이미지 임베딩 생성** - 이미지 다운로드 → 임베딩 생성 → Pinecone 저장

## 출력 통계

수집 완료 후 다음 통계가 출력됩니다:

```
Collection Statistics:
  Category: Attraction
  VISIT SEOUL places collected: 50
  Places saved: 50
  Quests created: 50
  Embeddings created: 48
  Errors: 2
```

- **VISIT SEOUL places collected**: VISIT SEOUL API에서 수집된 장소 수
- **Places saved**: DB에 저장된 장소 수
- **Quests created**: 생성된 퀘스트 수
- **Embeddings created**: 생성된 이미지 임베딩 수
- **Errors**: 발생한 에러 수

## 참고사항

- 모든 데이터는 VISIT SEOUL API에서 **영문**으로 수집됩니다 (`lang_code_id="en"`)
