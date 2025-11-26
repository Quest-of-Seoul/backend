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
# 카테고리별 목표 개수 자동 수집 (권장)
python scripts/collect_places.py --category <카테고리>

# 특정 개수만 수집
python scripts/collect_places.py --category <카테고리> --max-places <개수>
```

## 카테고리별 목표 개수

각 카테고리는 표에 정의된 목표 개수가 있습니다. `--max-places`를 지정하지 않으면 자동으로 목표 개수만큼 수집합니다:

| 카테고리 | 목표 개수 | 설명 |
|---------|----------|------|
| Attractions | 92 | 도시의 대표 관광명소(랜드마크·테마파크·핫플 등) |
| History | 649 | 역사·유적지·궁·전통 공간 |
| Culture | 599 | 박물관·미술관·전시·공연 등 문화시설 |
| Nature | 136 | 공원·산·강·자연풍경 |
| Food | 1004 | 식당·길거리음식·현지 맛집 (카페/주점 제외) |
| Drinks | 247 | 카페·티하우스·바(주점) |
| Shopping | 269 | 쇼핑·시장·상점가 |
| Activities | 368 | 체험·클래스·액티비티 |
| Events | 183 | 축제·공연·행사 |

## 카테고리별 수집 명령어

### Attractions (도시의 대표 관광명소) - 추천 테마

랜드마크, 테마공원, 핫플레이스 등 (목표: 92개)

```bash
# 전체 수집 (92개, 권장)
python scripts/collect_places.py --category Attractions

# 특정 개수만 수집
python scripts/collect_places.py --category Attractions --max-places 50

# 이미지 임베딩 없이 수집 (빠른 수집)
python scripts/collect_places.py --category Attractions --no-embeddings
```

### History (역사·유적지·궁·전통 공간)

목표: 649개

```bash
# 전체 수집 (649개)
python scripts/collect_places.py --category History

# 특정 개수만 수집
python scripts/collect_places.py --category History --max-places 100
```

### Culture (박물관·미술관 전시·공연 등 문화시설) - 추천 테마

목표: 599개

```bash
# 전체 수집 (599개)
python scripts/collect_places.py --category Culture

# 특정 개수만 수집
python scripts/collect_places.py --category Culture --max-places 100
```

### Nature (공원·산·강·자연풍경)

목표: 136개

```bash
# 전체 수집 (136개)
python scripts/collect_places.py --category Nature

# 특정 개수만 수집
python scripts/collect_places.py --category Nature --max-places 50
```

### Food (식당·길거리음식·현지 맛집)

카페/찻집, 주점 제외 (목표: 1004개)

```bash
# 전체 수집 (1004개)
python scripts/collect_places.py --category Food

# 특정 개수만 수집
python scripts/collect_places.py --category Food --max-places 200
```

### Drinks (카페·티하우스·바(주점))

목표: 247개

```bash
# 전체 수집 (247개)
python scripts/collect_places.py --category Drinks

# 특정 개수만 수집
python scripts/collect_places.py --category Drinks --max-places 50
```

### Shopping (쇼핑·시장·상점가)

목표: 269개

```bash
# 전체 수집 (269개)
python scripts/collect_places.py --category Shopping

# 특정 개수만 수집
python scripts/collect_places.py --category Shopping --max-places 50
```

### Activities (체험·클래스·액티비티)

목표: 368개

```bash
# 전체 수집 (368개)
python scripts/collect_places.py --category Activities

# 특정 개수만 수집
python scripts/collect_places.py --category Activities --max-places 100
```

### Events (축제·공연·행사)

목표: 183개

```bash
# 전체 수집 (183개)
python scripts/collect_places.py --category Events

# 특정 개수만 수집
python scripts/collect_places.py --category Events --max-places 50
```

## 옵션 설명

### 필수 옵션

- `--category`: 수집할 카테고리
  - 선택 가능: `Attractions`, `History`, `Culture`, `Nature`, `Food`, `Drinks`, `Shopping`, `Activities`, `Events`
  - 예: `--category Attractions`

### 선택 옵션

- `--max-places`: 최대 수집 장소 수 (기본값: 카테고리별 목표 개수)
  - 지정하지 않으면 카테고리별 목표 개수(표 참고)만큼 자동 수집
  - `0` 이하로 지정하면 전체 데이터 수집 (제한 없음)
  - 예: `--max-places 100`

- `--lang-code`: VISIT SEOUL API 언어 코드 (기본값: "en")
  - 선택 가능: `ko` (한국어), `en` (영어), `ja` (일본어), `zh` (중국어)
  - 예: `--lang-code ko`

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

1. **카테고리 매핑** - Quest of Seoul 카테고리를 VISIT SEOUL API 카테고리 코드로 매핑
2. **VISIT SEOUL 장소 수집** - 카테고리별 장소 리스트 조회 (지정된 언어 코드 사용)
3. **VISIT SEOUL 상세 정보 수집** - 각 장소의 상세 정보 조회
4. **데이터 파싱 및 저장** - VISIT SEOUL 응답을 표준 형식으로 변환하여 DB에 저장
5. **퀘스트 생성** - 저장된 장소로부터 자동 퀘스트 생성
6. **이미지 임베딩 생성** - 이미지 다운로드 → 임베딩 생성 → Pinecone 저장 (선택사항)

## 출력 통계

수집 완료 후 다음 통계가 출력됩니다:

```
Collection Statistics:
  Category: Attractions
  Lang code: en
  Target count: 92
  VISIT SEOUL places collected: 92
  Places saved: 92
  Quests created: 92
  Embeddings created: 90
  Errors: 0
```

- **Category**: 수집한 카테고리
- **Lang code**: 사용한 언어 코드
- **Target count**: 목표 수집 개수 (표에 정의된 값)
- **VISIT SEOUL places collected**: VISIT SEOUL API에서 수집된 장소 수
- **Places saved**: DB에 저장된 장소 수
- **Quests created**: 생성된 퀘스트 수
- **Embeddings created**: 생성된 이미지 임베딩 수
- **Errors**: 발생한 에러 수

목표 개수보다 적게 수집된 경우 경고 메시지가 출력됩니다.

## 참고사항

- 기본적으로 모든 데이터는 VISIT SEOUL API에서 **영문**으로 수집됩니다 (`--lang-code en`, 기본값)
- `--lang-code` 옵션으로 다른 언어로 수집 가능합니다
- 카테고리별 목표 개수는 VISIT SEOUL API의 실제 데이터 수를 기준으로 설정되어 있습니다
- 대량 수집 시 API 호출 제한을 고려하여 `--delay` 옵션을 조정하는 것을 권장합니다
- 이미지 임베딩 생성은 시간이 오래 걸릴 수 있으므로, 빠른 테스트를 원하면 `--no-embeddings` 옵션을 사용하세요
