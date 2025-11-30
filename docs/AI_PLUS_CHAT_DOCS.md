# AI Plus 챗 (Quest RAG 챗) 문서

## 개요
AI Plus 챗은 Quest 모드에서 제공되는 맞춤형 여행 가이드 기능입니다. 특정 Quest_id에 해당하는 DB 데이터만을 사용하여 해당 장소에 대한 정확하고 맞춤형 답변을 제공합니다.

## 핵심 원칙

### 1. Quest_id 기반 데이터 필터링
- **오직 해당 Quest_id의 데이터만 사용**: Quest RAG 챗은 `quest_id`를 필수 파라미터로 받아 해당 퀘스트와 연결된 Place 데이터만 사용합니다.
- **데이터 범위 제한**: 다른 Quest나 Place의 데이터는 절대 사용하지 않습니다.
- **정확한 컨텍스트 제공**: 사용자가 현재 작업 중인 Quest의 장소 정보만을 기반으로 답변합니다.

### 2. 데이터 기반 답변
- **DB 데이터 기반**: Quest와 Place 테이블에서 가져온 실제 데이터만 사용합니다.
- **RAG 검색 제한**: 향후 RAG 검색을 추가할 경우에도 반드시 `quest_id`로 필터링해야 합니다.
- **외부 데이터 제한**: Quest와 관련 없는 일반적인 지식이나 다른 장소 정보는 사용하지 않습니다.

### 3. DB 분리 설계 (추후 고도화)
- **Quest별 독립 데이터베이스**: 추후 맞춤형 여행 가이드 고도화를 위해 Quest별로 별도의 RAG 데이터베이스나 벡터 스토어를 분리해야 합니다.
- **확장성 고려**: 각 Quest가 독립적인 데이터베이스를 가지면 더 정확하고 맞춤형 답변을 제공할 수 있습니다.

## 현재 구현

### API 엔드포인트
```
POST /ai-station/quest/rag-chat
```

### Request Body
```json
{
  "quest_id": 1,                    // 필수: Quest ID
  "user_message": "이 장소에 대해 알려주세요",
  "landmark": "경복궁",              // 선택적: 장소 이름
  "language": "en",                  // 선택적: 언어 (기본: "en")
  "prefer_url": false,               // 선택적: TTS URL 선호 여부
  "enable_tts": true,                // 선택적: TTS 활성화 여부
  "chat_session_id": "uuid"         // 선택적: 채팅 세션 ID
}
```

### 데이터 흐름

```
[Request]
    ↓
[Quest ID 검증]
    ↓
[Quest 데이터 조회]
    ├─ quests 테이블: id, name, title, description, category, reward_point 등
    └─ places 테이블: name, address, district, category, description, metadata 등
    ↓
[컨텍스트 구성]
    ├─ Quest Place 정보
    ├─ 주소, 지역, 카테고리
    ├─ 보상 포인트
    └─ 장소 설명
    ↓
[AI 응답 생성]
    └─ Quest 데이터만을 기반으로 답변 생성
    ↓
[응답 반환]
```

### 코드 구조

#### 1. Quest 데이터 조회
```python
def fetch_quest_context(quest_id: int, db=None) -> Dict[str, Any]:
    """Fetch quest and associated place metadata for quest mode chat."""
    db = db or get_db()
    quest_result = db.table("quests").select("*, places(*)").eq("id", quest_id).single().execute()
    # quest_id로만 필터링하여 해당 Quest의 데이터만 가져옴
```

#### 2. 컨텍스트 구성
```python
def build_quest_context_block(quest: Dict[str, Any]) -> str:
    """Build structured context text for LLM prompts."""
    # Quest와 Place 데이터만 사용하여 컨텍스트 구성
    # 다른 Quest나 Place의 데이터는 포함하지 않음
```

#### 3. AI 응답 생성
```python
# Quest 데이터만을 프롬프트에 포함
user_prompt = f"""The following is information about the quest place the user is currently working on:
{context_block}

Please answer the following question based on the above information.
Question: {request.user_message}"""
```

## 데이터 필터링 규칙

### 현재 구현
1. **Quest ID 필수**: `quest_id`가 없으면 400 에러 반환
2. **단일 Quest 조회**: `quests` 테이블에서 `id = quest_id`로 조회
3. **관련 Place 조회**: Quest와 연결된 `place_id`로 `places` 테이블 조회
4. **데이터 범위 제한**: 오직 해당 Quest와 Place 데이터만 사용

### 향후 RAG 검색 추가 시 필수 사항
1. **Quest_id 필터링**: RAG 검색 시 반드시 `quest_id` 또는 `place_id`로 필터링
2. **벡터 스토어 필터**: Pinecone 등 벡터 스토어에서 검색할 때도 `quest_id` 메타데이터로 필터링
3. **데이터 소스 제한**: Quest와 관련 없는 외부 데이터 소스는 사용하지 않음

## DB 분리 설계 (추후 고도화)

### 목적
- **맞춤형 여행 가이드 고도화**: 각 Quest별로 독립적인 데이터베이스를 가지면 더 정확하고 맞춤형 답변 제공 가능
- **확장성**: Quest별로 다른 데이터 소스나 벡터 스토어를 사용할 수 있음
- **성능 최적화**: Quest별로 최적화된 인덱스와 검색 전략 사용 가능

### 설계 방안

#### 옵션 1: Quest별 벡터 스토어 분리
```
quest_1_vectors/
quest_2_vectors/
quest_3_vectors/
...
```
- 각 Quest별로 독립적인 벡터 스토어 네임스페이스 사용
- Quest_id를 네임스페이스로 사용하여 자동 필터링

#### 옵션 2: Quest별 RAG 데이터베이스 분리
```
quest_rag_data/
  ├─ quest_1/
  │   ├─ documents/
  │   ├─ embeddings/
  │   └─ metadata/
  ├─ quest_2/
  │   ├─ documents/
  │   ├─ embeddings/
  │   └─ metadata/
  ...
```
- 각 Quest별로 독립적인 RAG 데이터베이스 디렉토리 구조
- Quest_id로 데이터베이스 경로 결정

#### 옵션 3: 메타데이터 기반 필터링
```python
# 벡터 스토어에 quest_id 메타데이터 포함
vector_metadata = {
    "quest_id": 1,
    "place_id": "uuid",
    "category": "history",
    ...
}

# 검색 시 quest_id로 필터링
filter_dict = {"quest_id": {"$eq": quest_id}}
```

### 구현 고려사항

1. **데이터 마이그레이션**: 기존 데이터를 Quest별로 분리하는 마이그레이션 전략 필요
2. **인덱스 관리**: Quest별로 독립적인 인덱스 관리 전략 필요
3. **검색 성능**: Quest별 데이터베이스 분리 시 검색 성능 최적화 필요
4. **데이터 일관성**: Quest 데이터와 RAG 데이터 간 일관성 유지 필요

## 현재 제한사항

1. **RAG 검색 미구현**: 현재는 Quest 데이터만 프롬프트에 포함하여 AI에게 전달
2. **벡터 검색 없음**: 사용자 질문에 대한 벡터 검색을 통한 관련 문서 검색 기능 없음
3. **단일 데이터 소스**: Quest와 Place 테이블의 데이터만 사용

## 향후 개선 방향

1. **Quest별 RAG 검색 추가**: 사용자 질문에 대한 벡터 검색을 Quest_id로 필터링하여 구현
2. **Quest별 벡터 스토어 분리**: 각 Quest별로 독립적인 벡터 스토어 네임스페이스 사용
3. **맞춤형 데이터 소스**: Quest별로 다른 데이터 소스(문서, 이미지, 비디오 등) 추가 가능
4. **컨텍스트 확장**: Quest별로 더 풍부한 컨텍스트 정보 제공

## 보안 및 데이터 보호

1. **데이터 격리**: Quest_id로 데이터를 격리하여 다른 Quest의 데이터에 접근 불가
2. **권한 검증**: 사용자가 해당 Quest에 접근 권한이 있는지 확인 필요
3. **데이터 무결성**: Quest 데이터와 RAG 데이터 간 일관성 유지

## API 문서

자세한 API 문서는 `API_DOCS.md`의 `POST /ai-station/quest/rag-chat` 섹션을 참조하세요.
