# API Test Scripts

## test_api.py

모든 API 엔드포인트를 테스트하는 통합 스크립트

### 사용법

#### 기본 테스트

```bash
# 서버 실행 확인 (모든 서비스 health check)
python scripts/test_api.py --health

# 모든 테스트 실행 (이미지 기반 테스트 제외)
python scripts/test_api.py --all
```

#### VLM (Vision-Language Model) 테스트

```bash
# VLM 이미지 분석
python scripts/test_api.py --vlm scripts/test_images/mydo_cathedral1.jpg

# 유사 이미지 검색
python scripts/test_api.py --similar scripts/test_images/mydo_cathedral1.jpg
```

#### AI 도슨트 테스트

```bash
# 채팅 테스트
python scripts/test_api.py --chat

# 퀴즈 생성 테스트
python scripts/test_api.py --quiz

# TTS 음성 합성 테스트
python scripts/test_api.py --tts
```

#### 추천 시스템 테스트

```bash
# 추천 서비스 상태 확인
python scripts/test_api.py --recommend-health

# 사용 가능한 카테고리 목록 조회
python scripts/test_api.py --recommend-categories

# 이미지 기반 장소 추천 (역사유적)
python scripts/test_api.py --recommend scripts/test_images/bukchon_hokvillage1.jpg

# 이미지 기반 장소 추천 (카테고리 지정)
python scripts/test_api.py --recommend scripts/test_images/mydo_cathedral1.jpg --recommend-category 종교시설

# 특정 장소와 유사한 장소 추천
python scripts/test_api.py --recommend-similar place-001-gyeongbokgung
```

#### 고급 옵션

```bash
# 다른 서버 URL 지정 (프로덕션 환경 테스트)
python scripts/test_api.py --health --url https://your-production-url.com

# 여러 테스트 조합
python scripts/test_api.py --health --chat --recommend-health
```

### 사용 가능한 카테고리

추천 시스템에서 사용 가능한 카테고리:
- `역사유적` (Historical Sites) - 기본값
- `관광지` (Tourist Attractions)
- `문화마을` (Cultural Villages)
- `종교시설` (Religious Sites)
- `광장` (Squares & Parks)

### 테스트 이미지

`test_images/` 폴더에 샘플 이미지 제공:
- `bukchon_hokvillage1.jpg`, `bukchon_hokvillage2.jpg` - 북촌한옥마을
- `mydo_cathedral1.jpg`, `mydo_cathedral2.jpg` - 명동성당

### 필요 조건

- 서버가 실행 중이어야 함: `python main.py`
- 이미지 기반 테스트는 이미지 파일 경로 필요
- API 키가 `.env` 파일에 설정되어 있어야 함

### 전체 옵션

```bash
python scripts/test_api.py --help
```

옵션 목록:
- `--health` - 전체 서비스 health check
- `--vlm IMAGE_PATH` - VLM 이미지 분석
- `--similar IMAGE_PATH` - 유사 이미지 검색
- `--chat` - 도슨트 채팅
- `--quiz` - 퀴즈 생성
- `--tts` - TTS 음성 합성
- `--recommend-health` - 추천 서비스 상태
- `--recommend-categories` - 추천 카테고리 목록
- `--recommend IMAGE_PATH` - 이미지 기반 장소 추천
- `--recommend-category CATEGORY` - 추천 카테고리 지정 (기본: 역사유적)
- `--recommend-similar PLACE_ID` - 유사 장소 추천
- `--all` - 모든 테스트 실행
- `--url URL` - 서버 URL 지정 (기본: http://localhost:8000)
