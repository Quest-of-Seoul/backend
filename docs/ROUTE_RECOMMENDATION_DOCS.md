# 여행 일정 추천 시스템 문서

## 개요
여행 일정 추천 시스템은 사용자의 취향, GPS 위치, 출발 지점을 기반으로 최적의 여행 일정(4개의 퀘스트)을 추천하는 시스템입니다.

## Input Data

### API 엔드포인트
```
POST /ai-station/route-recommend
```

### Request Body
```json
{
  "preferences": {
    "theme": ["Culture", "History", "Food"], // 선택적: 테마 (다중 선택 가능, 3~4개 권장)
                                             // 단일 선택도 지원: "Culture" 또는 ["Culture"]
    "category": {                            // 선택적: 카테고리 정보
      "name": "history"                      // 카테고리 이름 (예: history, culture, attractions 등)
    },
    "districts": ["Jongno-gu"],              // 선택적: 선호하는 구/지역 (다중 선택 가능)
    "include_cart": false                    // 선택적: 장바구니 포함 여부
  },
  "latitude": 37.5665,                     // 선택적: 사용자 현재 위도
  "longitude": 126.9780,                   // 선택적: 사용자 현재 경도
  "start_latitude": 37.5665,               // 선택적: 출발 지점 위도 (서울역, 강남역 등)
  "start_longitude": 126.9780,             // 선택적: 출발 지점 경도
  "must_visit_place_id": "uuid"            // 선택적: 필수 방문 장소 ID
}
```

### 입력 데이터 설명

#### 1. 위치 정보
- **현재 위치** (`latitude`, `longitude`): 사용자의 현재 GPS 위치
  - 제공 시: 반경 15km 내 퀘스트를 후보로 수집
  - 미제공 시: 전체 활성 퀘스트 중 상위 50개를 후보로 수집

- **출발 지점** (`start_latitude`, `start_longitude`): 사용자가 지정한 출발 장소
  - 예: 서울역, 강남역, 홍대 등
  - 지정 시: 출발 지점 기준으로 거리순 정렬
  - 미지정 시: 현재 GPS 위치를 출발 지점으로 사용

#### 2. 사용자 선호도 (`preferences`)
- **theme**: 테마 (다중 선택 가능, 3~4개 권장)
  - 리스트 형식: `["Culture", "History", "Food"]`
  - 단일 선택도 지원: `"Culture"` (하위 호환성)
  - 여러 테마 중 하나라도 매칭되면 높은 점수 부여
- **category**: 카테고리 정보
  - `name`: 카테고리 이름 (history, culture, attractions, religion, park 등)
- **districts**: 선호하는 구/지역 리스트 (다중 선택 가능)
- **include_cart**: 장바구니 포함 여부

#### 3. 필수 방문 장소 (`must_visit_place_id`)
- 사용자가 반드시 방문하고 싶은 장소의 ID
- 이 장소는 항상 추천 결과에 포함됨
- 출발 위치 기준 거리순 정렬에 포함되어 자연스럽게 배치됨 (첫 번째에 고정되지 않음)
- 1~4번째 중 출발 위치 기준으로 적절한 위치에 배치

## Output Data

### Response
```json
{
  "success": true,
  "quests": [
    {
      "id": 1,
      "name": "Gyeongbokgung Palace",
      "title": "경복궁 탐험",
      "description": "조선왕조의 대표 궁궐",
      "category": "history",
      "latitude": 37.5796,
      "longitude": 126.9770,
      "reward_point": 150,
      "points": 10,
      "difficulty": "easy",
      "completion_count": 42,
      "recommendation_score": 0.85,
      "score_breakdown": {
        "category": 1.0,
        "distance": 0.8,
        "diversity": 1.0,
        "popularity": 0.42,
        "reward": 0.75
      },
      "distance_from_start": 0.5,
      "district": "Jongno-gu",
      "place_image_url": "https://...",
      "place_id": "uuid",
      "created_at": "2024-01-01T00:00:00Z"
    },
    // ... 총 4개의 퀘스트
  ],
  "count": 4,
  "session_id": "uuid"
}
```

### 출력 데이터 설명

#### 1. 추천 퀘스트 정보
- **기본 정보**: id, name, title, description, category
- **위치 정보**: latitude, longitude, district
- **보상 정보**: reward_point, points
- **난이도**: difficulty
- **인기도**: completion_count (완료한 사용자 수)

#### 2. 추천 점수
- **recommendation_score**: 종합 추천 점수 (0.0 ~ 1.0)
- **score_breakdown**: 각 요소별 점수
  - `category`: 카테고리 매칭 점수
  - `distance`: 거리 점수
  - `diversity`: 다양성 점수
  - `popularity`: 인기도 점수
  - `reward`: 포인트 점수

#### 3. 거리 정보
- **distance_from_start**: 출발 지점으로부터의 거리 (km)

#### 4. 세션 정보
- **session_id**: 추천 세션 ID (채팅 로그 저장용)

## 사용자 플로우

```
[사용자 입력]
    ↓
[현재 위치 또는 출발 장소 지정]
    ├─ GPS 위치 제공 또는
    └─ 출발 장소 지정 (서울역, 강남역, 홍대 등)
    ↓
[선호도 정보 입력]
    ├─ 테마 선택 (다중 선택 가능: Culture, History, Food 등, 3~4개 권장)
    ├─ 카테고리 선택 (history, culture 등)
    └─ 지역 선택 (다중 선택 가능: Jongno-gu 등)
    ↓
[후보 퀘스트 수집]
    ├─ GPS 위치 있음: 반경 15km 내 퀘스트 조회
    └─ GPS 위치 없음: 전체 활성 퀘스트 중 상위 50개
    ↓
[점수 계산 및 정렬]
    ├─ 카테고리 매칭 점수 (30%)
    ├─ 거리 점수 (25%)
    ├─ 다양성 점수 (20%)
    ├─ 인기도 점수 (15%)
    └─ 포인트 점수 (10%)
    ↓
[최종 추천]
    ├─ 필수 방문 장소가 있으면: 필수 방문 장소 1개 + 일반 퀘스트 2개 + 야경 특별 장소 1개 = 4개
    │  (필수 방문 장소는 출발 위치 기준 거리순으로 자연스럽게 배치, 1~4번째 중 적절한 위치)
    └─ 필수 방문 장소가 없으면: 일반 퀘스트 3개 + 야경 특별 장소 1개 = 4개
       (야경 장소가 없으면 일반 퀘스트로 채워서 4개 유지)
    ↓
[중복 체크 (place_id 기준)]
    ↓
[4개 퀘스트 반환 (야경 장소는 항상 마지막, 최대 4개 제한)]
```

## 사용 기술 및 알고리즘

### 1. 추천 시스템 유형

현재 시스템은 **하이브리드 추천 시스템**입니다:

#### 1.1 컨텐츠 기반 필터링 (Content-Based Filtering)
- **이미지 기반 유사도 검색**: `/recommend/similar-places` 엔드포인트에서 사용
  - 사용자가 업로드한 이미지를 임베딩으로 변환
  - Pinecone 벡터 데이터베이스에서 유사한 장소 검색
  - 이미지 유사도 기반 추천

#### 1.2 협업 필터링 요소 (Collaborative Filtering)
- **인기도 기반 추천**: `completion_count`를 활용한 인기도 점수 계산
  - 많은 사용자가 완료한 퀘스트를 우선 추천

#### 1.3 사용자 선호도 기반 필터링
- **카테고리 매칭**: 사용자가 선택한 카테고리와 퀘스트 카테고리 일치도 계산
- **다양성 점수**: 사용자가 완료한 카테고리와 다른 퀘스트 우선 추천

#### 1.4 지리적 필터링
- **거리 기반 필터링**: GPS 위치 기반 반경 내 퀘스트만 후보로 수집
- **거리 점수**: 출발 지점 또는 현재 위치로부터의 거리 기반 점수 계산

### 2. 점수 계산 알고리즘

#### 2.1 카테고리 매칭 점수 (가중치: 30%)
```python
def calculate_category_score(quest_category: str, preferred_categories: List[str]) -> float:
    # 여러 테마 중 가장 높은 점수 반환
    # 정확히 일치: 1.0
    # 유사 카테고리: 0.7
    # 관련 없음: 0.3
    # 매칭 없음: 0.5 (중간 점수)
```

**다중 선택 지원**:
- `theme`을 리스트로 전달하면 여러 테마 중 하나라도 매칭되면 높은 점수 부여
- 예: `["Culture", "History", "Food"]` 중 하나라도 매칭되면 점수 부여
- 여러 테마 중 가장 높은 매칭 점수를 사용

**카테고리 그룹**:
- History: history, historical, 역사, 역사유적, 문화재, 궁궐, 유적지
- Attractions: attractions, landmark, tourist, 관광지, 명소, 전망대
- Culture: culture, traditional, 문화, 문화마을, 한옥마을, 전통마을
- Religion: religion, temple, 종교, 종교시설, 사찰, 성당, 교회
- Park: park, square, outdoor, 공원, 광장, 야외공간

#### 2.2 거리 점수 (가중치: 25%)
```python
def calculate_distance_score(lat1, lon1, lat2, lon2) -> float:
    # 15km 이내: 1.0 - (distance_km / 15.0)
    # 15km 초과: 0.1
```

**거리 계산 방법**:
- Haversine 공식을 사용하여 지구상의 두 지점 간 거리 계산
- 출발 지점 지정 시: `start_latitude`, `start_longitude` 사용
- 미지정 시: 현재 GPS 위치(`latitude`, `longitude`) 사용

#### 2.3 다양성 점수 (가중치: 20%)
```python
def calculate_diversity_score(quest_category: str, completed_categories: set) -> float:
    # 완료한 카테고리와 다름: 1.0
    # 완료한 카테고리와 같음: 0.3
```

**다양성 계산 방법**:
- 사용자가 완료한 퀘스트의 카테고리를 수집
- 새로운 카테고리의 퀘스트를 우선 추천하여 다양한 경험 제공

#### 2.4 인기도 점수 (가중치: 15%)
```python
def calculate_popularity_score(completion_count: int) -> float:
    # completion_count / 100.0 (최대 1.0)
    return min(1.0, completion_count / 100.0)
```

**인기도 데이터 출처**:
- `quests` 테이블의 `completion_count` 컬럼
- 사용자가 퀘스트를 완료할 때마다 증가
- 업데이트 위치:
  - `routers/recommend.py:450-452`: 퀘스트 퀴즈 정답 시 증가
  - `routers/quest.py`: 퀘스트 완료 시 증가

#### 2.5 포인트 점수 (가중치: 10%)
```python
def calculate_reward_score(reward_point: int) -> float:
    # reward_point / 200.0 (최대 1.0)
    return min(1.0, reward_point / 200.0)
```

**포인트 데이터 출처**:
- `quests` 테이블의 `reward_point` 컬럼
- 퀘스트 생성 시 설정되는 기본값 (기본값: 100)
- 데이터베이스 스키마: `reward_point INTEGER DEFAULT 100`

### 3. 종합 점수 계산

```python
final_score = (
    category_score * 0.3 +      # 카테고리 매칭: 30%
    distance_score * 0.25 +      # 거리: 25%
    diversity_score * 0.2 +      # 다양성: 20%
    popularity_score * 0.15 +    # 인기도: 15%
    reward_score * 0.1           # 포인트: 10%
)
```

### 4. 정렬 및 필터링

#### 4.1 출발 지점 기준 정렬
- 출발 지점이 지정되거나 GPS 위치가 있으면 거리순 정렬
  - 필수 방문 장소도 출발 지점 기준 거리순 정렬에 포함됨
  - 앵커(기준점)는 출발 위치로 설정됨
- 없으면 점수순 정렬 (`recommendation_score` 기준)

#### 4.2 야경 특별 장소 분리
야경 특별 장소 판별 기준:
- `metadata`에 "night_view", "night_scene", "night_viewing", "야경", "야경명소" 포함
- `description`에 "night view", "night scene", "야경", "야경명소", "야경 포인트" 포함
- `name`에 "night view", "야경" 포함

#### 4.3 최종 추천
**기본 로직**:
- 필수 방문 장소(`must_visit_place_id`)가 있는 경우:
  - 필수 방문 장소 1개 + 일반 퀘스트 2개 + 야경 특별 장소 1개 = 총 4개
  - 야경 장소가 없으면 일반 퀘스트 3개로 대체
- 필수 방문 장소가 없는 경우:
  - 일반 퀘스트 3개 + 야경 특별 장소 1개 = 총 4개
  - 야경 장소가 없으면 일반 퀘스트 4개로 대체

**추천 순서**:
1. 필수 방문 장소가 있으면 `regular_quests`에 포함하여 출발 지점 기준 거리순 정렬에 포함
   - 필수 방문 장소는 첫 번째에 고정되지 않고, 출발 위치 기준 거리순으로 자연스럽게 배치됨
   - 1~4번째 중 출발 위치 기준으로 적절한 위치에 배치
2. 일반 퀘스트를 출발 지점 기준 가까운 순으로 선택 (야경 장소 제외, 필수 방문 장소 포함)
   - 필수 방문 장소가 있으면: 일반 퀘스트 3개 선택 (필수 방문 장소 포함)
   - 필수 방문 장소가 없으면: 일반 퀘스트 3개 선택
3. **야경 특별 장소를 항상 마지막 장소로 추가** (가능한 경우)
4. 야경 장소가 없으면 일반 퀘스트로 채워서 총 4개 유지
5. **중복 체크**: `place_id` 기준으로 중복된 장소는 제외
6. 최종적으로 총 4개 퀘스트 반환 (최대 4개 제한)

## 데이터 출처

### 1. 선호도 데이터
- **출처**: 사용자 입력 (`preferences` 객체)
- **저장 위치**: 요청 시 전달되는 데이터 (DB 저장 안 함)
- **사용 위치**: `routers/ai_station.py:890-901`

### 2. 인기도 데이터 (`completion_count`)
- **출처**: `quests` 테이블의 `completion_count` 컬럼
- **초기값**: 0
- **업데이트 시점**:
  - 퀘스트 퀴즈 정답 시: `routers/recommend.py:450-452`
  - 퀘스트 완료 시: `routers/quest.py` (추정)
- **사용 위치**: `routers/ai_station.py:1098, 1109`

### 3. 포인트 데이터 (`reward_point`)
- **출처**: `quests` 테이블의 `reward_point` 컬럼
- **초기값**: 100 (데이터베이스 기본값)
- **설정 시점**: 퀘스트 생성 시
- **사용 위치**: `routers/ai_station.py:1099, 1111`

### 4. 완료한 퀘스트 데이터
- **출처**: `user_quests` 테이블
- **조회 조건**: `user_id`와 `status = 'completed'`
- **사용 위치**: `routers/ai_station.py:904-975`
- **용도**: 다양성 점수 계산 및 완료한 퀘스트 제외

### 5. 위치 데이터
- **출처**: 사용자 입력 (`latitude`, `longitude`, `start_latitude`, `start_longitude`)
- **저장 위치**: 요청 시 전달되는 데이터
- **사용 위치**: 거리 계산 및 후보 퀘스트 수집

## AI 기반 추천 (선택적)

환경 변수 `USE_AI_ROUTE_RECOMMENDATION=true`일 경우:
- 상위 20개 후보를 AI(Gemini)에 전달
- AI가 최적의 4개 퀘스트 선택
- AI 추천 실패 시 점수 기반 추천으로 폴백

## 성능 최적화

1. **후보 수집 제한**: 최대 50개 후보만 처리
2. **인덱스 활용**: GPS 위치 기반 인덱스 사용 (`idx_quests_location`)
3. **DB 검증**: 실제 존재하는 장소만 추천 (`is_active = TRUE`)

## 향후 개선 방향

1. **실시간 교통 정보 반영**: 거리 계산 시 교통 상황 고려
2. **시간대별 추천**: 오전/오후/저녁 시간대별 최적 경로
3. **그룹 추천**: 여러 사용자 취향을 종합한 그룹 일정
4. **동적 가중치**: 사용자 피드백 기반 가중치 조정
