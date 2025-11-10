-- Quest of Seoul - Quest & Quiz Schema Extension
-- 기존 quests 테이블에 필드 추가 및 퀴즈 시스템 구축

-- 기존 quests 테이블에 VLM 관련 필드 추가
ALTER TABLE quests ADD COLUMN IF NOT EXISTS place_id UUID REFERENCES places(id) ON DELETE CASCADE;
ALTER TABLE quests ADD COLUMN IF NOT EXISTS title TEXT;
ALTER TABLE quests ADD COLUMN IF NOT EXISTS category TEXT;
ALTER TABLE quests ADD COLUMN IF NOT EXISTS difficulty TEXT DEFAULT 'easy';
ALTER TABLE quests ADD COLUMN IF NOT EXISTS points INTEGER DEFAULT 10;
ALTER TABLE quests ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT true;
ALTER TABLE quests ADD COLUMN IF NOT EXISTS completion_count INTEGER DEFAULT 0;

-- quest_quizzes 테이블 (퀘스트별 퀴즈)
CREATE TABLE IF NOT EXISTS quest_quizzes (
    id SERIAL PRIMARY KEY,
    quest_id INTEGER REFERENCES quests(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    options TEXT[] NOT NULL,
    correct_answer INTEGER NOT NULL CHECK (correct_answer >= 0 AND correct_answer < 4),
    hint TEXT,
    explanation TEXT,
    difficulty TEXT DEFAULT 'easy',
    created_at TIMESTAMP DEFAULT NOW()
);

-- user_quest_progress 테이블 (사용자별 진행상황)
CREATE TABLE IF NOT EXISTS user_quest_progress (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    quest_id INTEGER REFERENCES quests(id) ON DELETE CASCADE,
    status TEXT DEFAULT 'in_progress',
    quiz_attempts INTEGER DEFAULT 0,
    quiz_correct BOOLEAN DEFAULT false,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, quest_id)
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_quests_place_id ON quests(place_id);
CREATE INDEX IF NOT EXISTS idx_quests_category ON quests(category);
CREATE INDEX IF NOT EXISTS idx_quests_is_active ON quests(is_active);
CREATE INDEX IF NOT EXISTS idx_quest_quizzes_quest_id ON quest_quizzes(quest_id);
CREATE INDEX IF NOT EXISTS idx_user_quest_progress_user_id ON user_quest_progress(user_id);
CREATE INDEX IF NOT EXISTS idx_user_quest_progress_quest_id ON user_quest_progress(quest_id);
CREATE INDEX IF NOT EXISTS idx_user_quest_progress_status ON user_quest_progress(status);

-- 퀘스트가 있는 장소 조회 함수
CREATE OR REPLACE FUNCTION get_places_with_quests(
    category_filter TEXT DEFAULT NULL,
    limit_count INT DEFAULT 100
)
RETURNS TABLE (
    place_id UUID,
    place_name TEXT,
    category TEXT,
    latitude DECIMAL,
    longitude DECIMAL,
    quest_id INTEGER,
    quest_title TEXT,
    quest_points INTEGER
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id AS place_id,
        p.name AS place_name,
        p.category,
        p.latitude,
        p.longitude,
        q.id AS quest_id,
        q.name AS quest_title,
        q.points AS quest_points
    FROM places p
    INNER JOIN quests q ON p.id = q.place_id
    WHERE q.is_active = true
        AND (category_filter IS NULL OR p.category = category_filter)
    ORDER BY q.completion_count ASC
    LIMIT limit_count;
END;
$$;

-- 주변 퀘스트 검색 함수
CREATE OR REPLACE FUNCTION search_nearby_quests(
    lat DECIMAL,
    lon DECIMAL,
    radius_km FLOAT DEFAULT 5.0,
    limit_count INT DEFAULT 10
)
RETURNS TABLE (
    place_id UUID,
    place_name TEXT,
    category TEXT,
    distance_km FLOAT,
    quest_id INTEGER,
    quest_points INTEGER
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id AS place_id,
        p.name AS place_name,
        p.category,
        earth_distance(
            ll_to_earth(lat, lon),
            ll_to_earth(p.latitude, p.longitude)
        ) / 1000.0 AS distance_km,
        q.id AS quest_id,
        q.points AS quest_points
    FROM places p
    INNER JOIN quests q ON p.id = q.place_id
    WHERE earth_box(ll_to_earth(lat, lon), radius_km * 1000) @> ll_to_earth(p.latitude, p.longitude)
        AND q.is_active = true
        AND p.is_active = true
    ORDER BY earth_distance(
        ll_to_earth(lat, lon),
        ll_to_earth(p.latitude, p.longitude)
    )
    LIMIT limit_count;
END;
$$;

-- 코멘트
COMMENT ON TABLE quest_quizzes IS '퀘스트별 객관식 퀴즈';
COMMENT ON TABLE user_quest_progress IS '사용자별 퀘스트 진행 상황';
COMMENT ON COLUMN quests.place_id IS 'VLM places 테이블 연동';
COMMENT ON COLUMN quest_quizzes.correct_answer IS '정답 인덱스 (0-3)';
COMMENT ON COLUMN quest_quizzes.hint IS '간접적인 힌트 문장';
