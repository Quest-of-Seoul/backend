-- Quest of Seoul - VLM Image Analysis Schema
-- AR 카메라 기반 이미지 분석 및 장소 추천 시스템
-- 벡터 검색: Pinecone / 메타데이터: Supabase

-- 실행 방법:
-- 1. Supabase Dashboard → SQL Editor
-- 2. 이 파일 내용 복사 & 붙여넣기 → Run

-- 지리 공간 확장 설치 (GPS 기반 검색용)
CREATE EXTENSION IF NOT EXISTS cube;
CREATE EXTENSION IF NOT EXISTS earthdistance;

-- places 테이블 (장소 메타데이터)
CREATE TABLE IF NOT EXISTS places (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,                        -- 장소명 (한글)
    name_en TEXT,                              -- 영문명
    description TEXT,                          -- 장소 설명
    category TEXT,                             -- 카테고리 (관광지, 음식점, 카페 등)
    address TEXT,                              -- 주소
    latitude DECIMAL(10, 8),                   -- 위도
    longitude DECIMAL(11, 8),                  -- 경도
    image_url TEXT,                            -- 대표 이미지 URL
    images TEXT[],                             -- 추가 이미지 URL 배열
    metadata JSONB DEFAULT '{}'::jsonb,        -- 추가 메타정보 (운영시간, 입장료, 태그 등)
    source TEXT DEFAULT 'manual',              -- 데이터 출처 (manual, api, dataset)
    is_active BOOLEAN DEFAULT true,            -- 활성화 상태
    view_count INTEGER DEFAULT 0,              -- 조회수
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 위치 기반 검색 인덱스 (반경 검색)
CREATE INDEX IF NOT EXISTS idx_places_location 
ON places USING gist(ll_to_earth(latitude, longitude));

-- 카테고리 검색 인덱스
CREATE INDEX IF NOT EXISTS idx_places_category ON places(category);

-- 이름 검색 인덱스 (단순 텍스트 검색용)
CREATE INDEX IF NOT EXISTS idx_places_name ON places(name);
CREATE INDEX IF NOT EXISTS idx_places_name_en ON places(name_en);

-- vlm_logs 테이블 (VLM 분석 로그)
CREATE TABLE IF NOT EXISTS vlm_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,                     -- 사용자 ID
    image_url TEXT,                            -- 업로드된 이미지 URL
    image_hash TEXT,                           -- 이미지 해시 (캐싱용)
    latitude DECIMAL(10, 8),                   -- 촬영 위치 (위도)
    longitude DECIMAL(11, 8),                  -- 촬영 위치 (경도)
    vlm_provider TEXT,                         -- VLM 제공자 (gpt4v)
    vlm_response TEXT,                         -- VLM 원본 응답
    final_description TEXT,                    -- 최종 설명 (Gemini 보강)
    matched_place_id UUID REFERENCES places(id),  -- 매칭된 장소
    similar_places JSONB,                      -- 유사 장소 목록
    confidence_score DECIMAL(3, 2),            -- 신뢰도 점수 (0.0 - 1.0)
    processing_time_ms INTEGER,                -- 처리 시간 (밀리초)
    error_message TEXT,                        -- 에러 메시지 (실패시)
    metadata JSONB DEFAULT '{}'::jsonb,        -- 추가 정보
    created_at TIMESTAMP DEFAULT NOW()
);

-- 사용자별 로그 조회 인덱스
CREATE INDEX IF NOT EXISTS idx_vlm_logs_user_id ON vlm_logs(user_id);

-- 장소별 로그 조회 인덱스
CREATE INDEX IF NOT EXISTS idx_vlm_logs_place_id ON vlm_logs(matched_place_id);

-- 이미지 해시 인덱스 (캐싱 조회)
CREATE INDEX IF NOT EXISTS idx_vlm_logs_image_hash ON vlm_logs(image_hash);

-- 날짜별 조회 인덱스
CREATE INDEX IF NOT EXISTS idx_vlm_logs_created_at ON vlm_logs(created_at DESC);

-- 유틸리티 함수: 반경 내 장소 검색 (GPS 기반)
CREATE OR REPLACE FUNCTION search_places_by_radius(
    lat DECIMAL,
    lon DECIMAL,
    radius_km FLOAT DEFAULT 1.0,
    limit_count INT DEFAULT 10
)
RETURNS TABLE (
    id UUID,
    name TEXT,
    category TEXT,
    address TEXT,
    latitude DECIMAL,
    longitude DECIMAL,
    distance_km FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id,
        p.name,
        p.category,
        p.address,
        p.latitude,
        p.longitude,
        earth_distance(
            ll_to_earth(lat, lon),
            ll_to_earth(p.latitude, p.longitude)
        ) / 1000.0 AS distance_km
    FROM places p
    WHERE earth_box(ll_to_earth(lat, lon), radius_km * 1000) @> ll_to_earth(p.latitude, p.longitude)
        AND p.is_active = true
    ORDER BY earth_distance(
        ll_to_earth(lat, lon),
        ll_to_earth(p.latitude, p.longitude)
    )
    LIMIT limit_count;
END;
$$;

-- 샘플 데이터 삽입 (테스트용)
INSERT INTO places (name, name_en, description, category, address, latitude, longitude, image_url, metadata)
VALUES
    (
        '경복궁',
        'Gyeongbokgung Palace',
        '조선시대 대표 궁궐로, 1395년에 창건되었습니다. 근정전, 경회루 등 아름다운 전통 건축물을 감상할 수 있습니다.',
        '역사유적',
        '서울특별시 종로구 사직로 161',
        37.579617,
        126.977041,
        'https://ak-d.tripcdn.com/images/0104p120008ars39uB986_W_1440_810_Q80.webp?proc=source%2ftrip&proc=source%2ftrip',
        '{"opening_hours": "09:00-18:00", "closed": "화요일", "admission_fee": "3000원"}'::jsonb
    ),
    (
        '남산서울타워',
        'N Seoul Tower',
        '서울의 랜드마크로 해발 479.7m에 위치한 전망대입니다. 서울 시내 전경을 한눈에 볼 수 있습니다.',
        '관광지',
        '서울특별시 용산구 남산공원길 105',
        37.551169,
        126.988227,
        'https://ak-d.tripcdn.com/images/1lo5r12000jt8ej8cD340_W_1440_810_Q80.webp?proc=source%2ftrip&proc=source%2ftrip',
        '{"opening_hours": "10:00-23:00", "admission_fee": "16000원"}'::jsonb
    ),
    (
        '광화문광장',
        'Gwanghwamun Square',
        '세종대왕과 이순신 장군 동상이 있는 서울의 대표 광장입니다.',
        '광장',
        '서울특별시 종로구 세종대로 172',
        37.572889,
        126.976849,
        'https://ak-d.tripcdn.com/images/01051120008c32dlbE44A_W_1440_810_Q80.webp?proc=source%2ftrip&proc=source%2ftrip',
        '{"opening_hours": "24시간", "admission_fee": "무료"}'::jsonb
    ),
    (
        '명동성당',
        'Myeongdong Cathedral',
        '1898년에 완공된 한국 최초의 고딕 양식 성당입니다.',
        '종교시설',
        '서울특별시 중구 명동길 74',
        37.563600,
        126.986870,
        'https://ak-d.tripcdn.com/images/100f1f000001gqchv1B53_W_1440_810_Q80.webp?proc=source%2ftrip&proc=source%2ftrip',
        '{"opening_hours": "09:00-21:00", "admission_fee": "무료"}'::jsonb
    ),
    (
        '북촌한옥마을',
        'Bukchon Hanok Village',
        '전통 한옥이 밀집한 역사적 주거지역으로 조선시대 양반들의 집이 보존되어 있습니다.',
        '문화마을',
        '서울특별시 종로구 계동길 37',
        37.582306,
        126.985302,
        'https://ak-d.tripcdn.com/images/100p11000000r4rhv9EF4_C_1200_800_Q70.jpg?proc=source%2ftrip',
        '{"opening_hours": "24시간", "admission_fee": "무료"}'::jsonb
    )
ON CONFLICT DO NOTHING;

-- 테이블 코멘트
COMMENT ON TABLE places IS 'AR 카메라로 촬영 가능한 서울 주요 장소 정보';
COMMENT ON TABLE vlm_logs IS 'VLM 이미지 분석 요청 및 응답 로그';

COMMENT ON COLUMN places.metadata IS '운영시간, 입장료, 태그 등 추가 JSON 정보';
COMMENT ON COLUMN vlm_logs.confidence_score IS '장소 매칭 신뢰도 (0.0=낮음, 1.0=높음)';
