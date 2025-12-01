# 장소 데이터 수집 가이드

VISIT SEOUL API에서 장소 데이터를 수집하고 데이터베이스에 저장하는 스크립트입니다.

## 개요

이 스크립트는 VISIT SEOUL API를 통해 서울의 관광 장소 정보를 수집하고, 데이터베이스에 저장한 후 퀘스트를 자동 생성합니다. 선택적으로 이미지 임베딩도 생성하여 Pinecone 벡터 DB에 저장할 수 있습니다.

## 주요 기능

- **카테고리별 장소 수집**: 9개 카테고리(Attractions, History, Culture, Nature, Food, Drinks, Shopping, Activities, Events)에서 장소 수집
- **자동 퀘스트 생성**: 수집된 장소에 대해 자동으로 퀘스트 생성
- **이미지 임베딩 생성**: 장소 이미지의 벡터 임베딩 생성 및 Pinecone 저장
- **일괄 처리**: 모든 카테고리를 자동으로 순차 처리

## 사전 준비

```bash
# 환경 변수 설정 (.env 파일)
VISIT_SEOUL_API_KEY=your_api_key_here
```

## 사용법

### 단일 카테고리 수집

```bash
# 특정 카테고리 수집
python scripts/collect_places.py --category Attractions

# 최대 10개 장소만 수집
python scripts/collect_places.py --category Culture --max-places 10

# 이미지 임베딩 생성 제외
python scripts/collect_places.py --category History --no-embeddings
```

### 모든 카테고리 수집

```bash
# 카테고리 옵션 없이 실행하면 모든 카테고리 자동 수집
python scripts/collect_places.py

# 카테고리별 최대 50개씩 수집
python scripts/collect_places.py --max-places 50
```

## 명령줄 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--category` | 수집할 카테고리 (Attractions, History, Culture, Nature, Food, Drinks, Shopping, Activities, Events). 지정하지 않으면 모든 카테고리 수집 | None (모든 카테고리) |
| `--max-places` | 카테고리별 최대 수집 장소 수 | None (전체) |
| `--delay` | API 호출 간 지연 시간 (초) | 1.0 |
| `--lang-code` | VISIT SEOUL 언어 코드 | en |
| `--no-embeddings` | 이미지 임베딩 생성 건너뛰기 | False |
| `--delay-between-categories` | 카테고리 간 지연 시간 (초) | 2.0 |

## 처리 과정

1. **Step 1**: VISIT SEOUL API에서 카테고리별 장소 목록 수집
2. **Step 2**: 각 장소의 상세 정보 조회
3. **Step 3**: 데이터베이스에 저장 및 퀘스트 생성
   - 장소 정보를 DB에 저장
   - 각 장소에 대해 퀘스트 자동 생성
   - 이미지 임베딩 생성 및 Pinecone 저장 (옵션)

## 출력 예시

```
=== Starting collection for category: Attractions ===
Configured target for Attractions: 100 item(s) (lang: en)
Step 1: Collecting VISIT SEOUL places for Attractions...
Mapped category 'Attractions' to 3 VISIT SEOUL category_sn(s): ['1', '2', '3']
Collected 100 unique VISIT SEOUL places
Step 2: Fetching VISIT SEOUL place details...
Processed 100 VISIT SEOUL places with details
Step 3: Saving places...
Saved place: abc123 (Gyeongbokgung Palace)
Created quest: xyz789 for place: abc123
=== Collection completed for Attractions ===
Summary: 100 places saved, 100 quests created, 95 embeddings created
```

## 반환 통계

스크립트는 수집 결과에 대한 통계를 반환합니다:

- `visit_seoul_places_collected`: VISIT SEOUL에서 수집한 장소 수
- `places_saved`: 데이터베이스에 저장된 장소 수
- `quests_created`: 생성된 퀘스트 수
- `embeddings_created`: 생성된 이미지 임베딩 수
- `errors`: 발생한 오류 목록

## 주의사항

- API 호출 제한을 고려하여 `--delay` 옵션으로 적절한 지연 시간을 설정하세요
- 대량 수집 시 시간이 오래 걸릴 수 있습니다
- 네트워크 오류 시 자동으로 재시도합니다
- 이미지 임베딩 생성은 추가 시간이 소요됩니다
