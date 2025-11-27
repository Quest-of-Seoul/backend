-- Quest of Seoul - Supabase (PostgreSQL) Schema

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users Table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL UNIQUE,
    nickname VARCHAR(100),
    password_hash VARCHAR(255),
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);

-- Places Table
CREATE TABLE IF NOT EXISTS places (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    category VARCHAR(50),
    address VARCHAR(500),
    district VARCHAR(50),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    image_url TEXT,
    images JSONB,
    metadata JSONB,
    source VARCHAR(20) DEFAULT 'manual',
    is_active BOOLEAN DEFAULT TRUE,
    view_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_places_category ON places(category);
CREATE INDEX idx_places_name ON places(name);
CREATE INDEX idx_places_location ON places(latitude, longitude);
CREATE INDEX idx_places_is_active ON places(is_active);
CREATE INDEX idx_places_source ON places(source);
CREATE INDEX idx_places_category_source ON places(category, source);
CREATE INDEX idx_places_district ON places(district);

-- JSONB 필드에 대한 GIN 인덱스
CREATE INDEX idx_places_metadata_gin ON places USING GIN (metadata);
CREATE INDEX idx_places_images_gin ON places USING GIN (images);

ALTER TABLE places 
DROP CONSTRAINT IF EXISTS check_places_source;

ALTER TABLE places 
ADD CONSTRAINT check_places_source 
CHECK (source IN ('manual', 'tour_api', 'visit_seoul', 'both'));

-- Update timestamp trigger for places
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_places_updated_at BEFORE UPDATE ON places
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Trigger function to auto-extract district from address
CREATE OR REPLACE FUNCTION extract_district_trigger()
RETURNS TRIGGER AS $$
BEGIN
    -- Extract district from address if district is NULL or address changed
    IF NEW.district IS NULL AND NEW.address IS NOT NULL THEN
        NEW.district := extract_district_from_address(NEW.address);
    ELSIF OLD.address IS DISTINCT FROM NEW.address AND NEW.address IS NOT NULL THEN
        NEW.district := extract_district_from_address(NEW.address);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER extract_district_on_insert_or_update
    BEFORE INSERT OR UPDATE OF address, district ON places
    FOR EACH ROW
    EXECUTE FUNCTION extract_district_trigger();

-- Quests Table
CREATE TABLE IF NOT EXISTS quests (
    id SERIAL PRIMARY KEY,
    place_id UUID REFERENCES places(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    title VARCHAR(255),
    description TEXT,
    category VARCHAR(50),
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    reward_point INTEGER DEFAULT 100,
    points INTEGER DEFAULT 10,
    difficulty VARCHAR(20) DEFAULT 'easy',
    is_active BOOLEAN DEFAULT TRUE,
    completion_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_quests_place_id ON quests(place_id);
CREATE INDEX idx_quests_category ON quests(category);
CREATE INDEX idx_quests_is_active ON quests(is_active);
CREATE INDEX idx_quests_location ON quests(latitude, longitude);

-- Quest Quizzes Table
CREATE TABLE IF NOT EXISTS quest_quizzes (
    id SERIAL PRIMARY KEY,
    quest_id INTEGER NOT NULL REFERENCES quests(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    options JSONB NOT NULL,
    correct_answer INTEGER NOT NULL CHECK (correct_answer >= 0 AND correct_answer < 4),
    hint TEXT,
    explanation TEXT,
    difficulty VARCHAR(20) DEFAULT 'easy',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_quest_quizzes_quest_id ON quest_quizzes(quest_id);

-- User Quests Table
CREATE TABLE IF NOT EXISTS user_quests (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    quest_id INTEGER NOT NULL REFERENCES quests(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'completed', 'failed')),
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    UNIQUE(user_id, quest_id)
);

CREATE INDEX idx_user_quests_user_id ON user_quests(user_id);
CREATE INDEX idx_user_quests_quest_id ON user_quests(quest_id);
CREATE INDEX idx_user_quests_status ON user_quests(status);

-- User Quest Progress Table
CREATE TABLE IF NOT EXISTS user_quest_progress (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    quest_id INTEGER NOT NULL REFERENCES quests(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'in_progress',
    quiz_attempts INTEGER DEFAULT 0,
    quiz_correct BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, quest_id)
);

CREATE INDEX idx_user_quest_progress_user_id ON user_quest_progress(user_id);
CREATE INDEX idx_user_quest_progress_quest_id ON user_quest_progress(quest_id);
CREATE INDEX idx_user_quest_progress_status ON user_quest_progress(status);

-- Points Table
CREATE TABLE IF NOT EXISTS points (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    value INTEGER NOT NULL,
    reason VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_points_user_id ON points(user_id);
CREATE INDEX idx_points_created_at ON points(created_at);

-- Rewards Table
CREATE TABLE IF NOT EXISTS rewards (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(20) NOT NULL CHECK (type IN ('badge', 'coupon', 'item')),
    point_cost INTEGER NOT NULL,
    description TEXT,
    image_url TEXT,
    expire_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_rewards_type ON rewards(type);
CREATE INDEX idx_rewards_is_active ON rewards(is_active);

-- User Rewards Table
CREATE TABLE IF NOT EXISTS user_rewards (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    reward_id INTEGER NOT NULL REFERENCES rewards(id) ON DELETE CASCADE,
    claimed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    used_at TIMESTAMP NULL,
    qr_code VARCHAR(500)
);

CREATE INDEX idx_user_rewards_user_id ON user_rewards(user_id);
CREATE INDEX idx_user_rewards_reward_id ON user_rewards(reward_id);

-- Chat Logs Table
CREATE TABLE IF NOT EXISTS chat_logs (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    landmark VARCHAR(255),
    user_message TEXT,
    ai_response TEXT,
    mode VARCHAR(20) DEFAULT 'explore' CHECK (mode IN ('explore', 'quest')),
    function_type VARCHAR(50) DEFAULT 'rag_chat' CHECK (function_type IN ('rag_chat', 'vlm_chat', 'route_recommend', 'image_similarity')),
    image_url TEXT,
    chat_session_id UUID,
    title TEXT,
    is_read_only BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_chat_logs_user_id ON chat_logs(user_id);
CREATE INDEX idx_chat_logs_landmark ON chat_logs(landmark);
CREATE INDEX idx_chat_logs_created_at ON chat_logs(created_at);
CREATE INDEX idx_chat_logs_mode_function ON chat_logs(user_id, mode, function_type, created_at DESC);
CREATE INDEX idx_chat_logs_session ON chat_logs(chat_session_id);

-- VLM Logs Table
CREATE TABLE IF NOT EXISTS vlm_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    image_url TEXT,
    image_hash VARCHAR(64),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    vlm_response TEXT,
    final_description TEXT,
    matched_place_id UUID REFERENCES places(id) ON DELETE SET NULL,
    similar_places JSONB,
    confidence_score DECIMAL(3, 2),
    processing_time_ms INTEGER,
    pinecone_vector_id VARCHAR(255),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_vlm_logs_user_id ON vlm_logs(user_id);
CREATE INDEX idx_vlm_logs_place_id ON vlm_logs(matched_place_id);
CREATE INDEX idx_vlm_logs_image_hash ON vlm_logs(image_hash);
CREATE INDEX idx_vlm_logs_created_at ON vlm_logs(created_at);
CREATE INDEX idx_vlm_logs_location ON vlm_logs(latitude, longitude);
CREATE INDEX idx_vlm_logs_pinecone_id ON vlm_logs(pinecone_vector_id);

-- Functions

-- Extract district from address using regex
DROP FUNCTION IF EXISTS extract_district_from_address(VARCHAR);
CREATE OR REPLACE FUNCTION extract_district_from_address(addr VARCHAR(500))
RETURNS VARCHAR(50) AS $$
DECLARE
    district_name VARCHAR(50);
    match_result TEXT[];
BEGIN
    IF addr IS NULL OR addr = '' THEN
        RETURN NULL;
    END IF;
    
    -- Try Korean pattern: "종로구", "강남구" etc. (한글 + 구)
    match_result := regexp_match(addr, '[가-힣]+구');
    IF match_result IS NOT NULL AND array_length(match_result, 1) > 0 THEN
        district_name := match_result[1];
        RETURN district_name;
    END IF;
    
    -- Try English pattern: "Jongno-gu", "Gangnam-gu" etc.
    match_result := regexp_match(addr, '[A-Za-z]+-gu', 'i');
    IF match_result IS NOT NULL AND array_length(match_result, 1) > 0 THEN
        -- Convert "Jongno-gu" to "Jongno-gu" (keep as is, or can normalize)
        district_name := match_result[1];
        RETURN district_name;
    END IF;
    
    -- Try another English pattern: "Jongno gu" (with space)
    match_result := regexp_match(addr, '[A-Za-z]+\s+gu', 'i');
    IF match_result IS NOT NULL AND array_length(match_result, 1) > 0 THEN
        district_name := REPLACE(match_result[1], ' ', '-');
        RETURN district_name;
    END IF;
    
    RETURN NULL;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Get user total points
DROP FUNCTION IF EXISTS get_user_points(UUID);
CREATE OR REPLACE FUNCTION get_user_points(user_uuid UUID)
RETURNS INTEGER AS $$
DECLARE
    total_points INTEGER;
BEGIN
    SELECT COALESCE(SUM(value), 0) INTO total_points
    FROM points
    WHERE user_id = user_uuid;
    RETURN total_points;
END;
$$ LANGUAGE plpgsql;

-- Search places by radius (Haversine formula)
DROP FUNCTION IF EXISTS search_places_by_radius(DECIMAL, DECIMAL, FLOAT, INTEGER);
CREATE OR REPLACE FUNCTION search_places_by_radius(
    lat DECIMAL(10, 8),
    lon DECIMAL(11, 8),
    radius_km FLOAT,
    limit_count INTEGER
)
RETURNS TABLE (
    id UUID,
    name VARCHAR(255),
    category VARCHAR(50),
    address VARCHAR(500),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    distance_km FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id,
        p.name,
        p.category,
        p.address,
        p.latitude,
        p.longitude,
        (
            6371 * ACOS(
                COS(RADIANS(lat)) *
                COS(RADIANS(p.latitude)) *
                COS(RADIANS(p.longitude) - RADIANS(lon)) +
                SIN(RADIANS(lat)) *
                SIN(RADIANS(p.latitude))
            )
        )::FLOAT AS distance_km
    FROM places p
    WHERE p.is_active = TRUE
        AND (
            6371 * ACOS(
                COS(RADIANS(lat)) *
                COS(RADIANS(p.latitude)) *
                COS(RADIANS(p.longitude) - RADIANS(lon)) +
                SIN(RADIANS(lat)) *
                SIN(RADIANS(p.latitude))
            )
        ) <= radius_km
    ORDER BY distance_km
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Search nearby quests
DROP FUNCTION IF EXISTS search_nearby_quests(DECIMAL, DECIMAL, FLOAT, INTEGER);
CREATE OR REPLACE FUNCTION search_nearby_quests(
    lat DECIMAL(10, 8),
    lon DECIMAL(11, 8),
    radius_km FLOAT,
    limit_count INTEGER
)
RETURNS TABLE (
    place_id UUID,
    place_name VARCHAR(255),
    category VARCHAR(50),
    distance_km FLOAT,
    quest_id INTEGER,
    quest_points INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id AS place_id,
        p.name AS place_name,
        p.category,
        (
            6371 * ACOS(
                COS(RADIANS(lat)) *
                COS(RADIANS(p.latitude)) *
                COS(RADIANS(p.longitude) - RADIANS(lon)) +
                SIN(RADIANS(lat)) *
                SIN(RADIANS(p.latitude))
            )
        )::FLOAT AS distance_km,
        q.id AS quest_id,
        q.points AS quest_points
    FROM places p
    INNER JOIN quests q ON p.id = q.place_id
    WHERE q.is_active = TRUE
        AND p.is_active = TRUE
        AND (
            6371 * ACOS(
                COS(RADIANS(lat)) *
                COS(RADIANS(p.latitude)) *
                COS(RADIANS(p.longitude) - RADIANS(lon)) +
                SIN(RADIANS(lat)) *
                SIN(RADIANS(p.latitude))
            )
        ) <= radius_km
    ORDER BY distance_km
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Get user VLM logs
DROP FUNCTION IF EXISTS get_user_vlm_logs(UUID, INTEGER);
CREATE OR REPLACE FUNCTION get_user_vlm_logs(
    user_uuid UUID,
    limit_count INTEGER
)
RETURNS TABLE (
    id UUID,
    image_url TEXT,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    final_description TEXT,
    matched_place_name VARCHAR(255),
    confidence_score DECIMAL(3, 2),
    created_at TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        v.id,
        v.image_url,
        v.latitude,
        v.longitude,
        v.final_description,
        p.name AS matched_place_name,
        v.confidence_score,
        v.created_at
    FROM vlm_logs v
    LEFT JOIN places p ON v.matched_place_id = p.id
    WHERE v.user_id = user_uuid
    ORDER BY v.created_at DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Get cached VLM result by image hash
DROP FUNCTION IF EXISTS get_cached_vlm_result(VARCHAR);
CREATE OR REPLACE FUNCTION get_cached_vlm_result(hash VARCHAR(64))
RETURNS TABLE (
    id UUID,
    user_id UUID,
    image_url TEXT,
    image_hash VARCHAR(64),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    vlm_response TEXT,
    final_description TEXT,
    matched_place_id UUID,
    matched_place_name VARCHAR(255),
    similar_places JSONB,
    confidence_score DECIMAL(3, 2),
    processing_time_ms INTEGER,
    pinecone_vector_id VARCHAR(255),
    created_at TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        v.id,
        v.user_id,
        v.image_url,
        v.image_hash,
        v.latitude,
        v.longitude,
        v.vlm_response,
        v.final_description,
        v.matched_place_id,
        p.name AS matched_place_name,
        v.similar_places,
        v.confidence_score,
        v.processing_time_ms,
        v.pinecone_vector_id,
        v.created_at
    FROM vlm_logs v
    LEFT JOIN places p ON v.matched_place_id = p.id
    WHERE v.image_hash = hash
        AND v.error_message IS NULL
    ORDER BY v.created_at DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- Search places by RAG text
DROP FUNCTION IF EXISTS search_places_by_rag_text(TEXT, INTEGER);
CREATE OR REPLACE FUNCTION search_places_by_rag_text(
    search_query TEXT,
    limit_count INTEGER DEFAULT 10
)
RETURNS TABLE (
    id UUID,
    name VARCHAR(255),
    category VARCHAR(50),
    rag_text TEXT,
    similarity_score REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id,
        p.name,
        p.category,
        p.metadata->>'rag_text' AS rag_text,
        ts_rank(
            to_tsvector('simple', COALESCE(p.metadata->>'rag_text', '')),
            plainto_tsquery('simple', search_query)
        ) AS similarity_score
    FROM places p
    WHERE p.is_active = TRUE
        AND p.metadata->>'rag_text' IS NOT NULL
        AND to_tsvector('simple', p.metadata->>'rag_text') @@ plainto_tsquery('simple', search_query)
    ORDER BY similarity_score DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Get category statistics
DROP FUNCTION IF EXISTS get_category_stats();
CREATE OR REPLACE FUNCTION get_category_stats()
RETURNS TABLE (
    category VARCHAR(50),
    total_count BIGINT,
    tour_api_count BIGINT,
    visit_seoul_count BIGINT,
    both_count BIGINT,
    with_images BIGINT,
    with_embeddings BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.category,
        COUNT(*)::BIGINT AS total_count,
        COUNT(*) FILTER (WHERE p.source = 'tour_api')::BIGINT AS tour_api_count,
        COUNT(*) FILTER (WHERE p.source = 'visit_seoul')::BIGINT AS visit_seoul_count,
        COUNT(*) FILTER (WHERE p.source = 'both')::BIGINT AS both_count,
        COUNT(*) FILTER (WHERE p.image_url IS NOT NULL)::BIGINT AS with_images,
        COUNT(*) FILTER (WHERE p.metadata->>'rag_text' IS NOT NULL)::BIGINT AS with_embeddings
    FROM places p
    WHERE p.is_active = TRUE
    GROUP BY p.category
    ORDER BY total_count DESC;
END;
$$ LANGUAGE plpgsql;

-- Sample Data

-- Sample Places
INSERT INTO places (id, name, description, category, address, latitude, longitude, image_url, metadata)
VALUES
    (uuid_generate_v4(), 'Gyeongbokgung Palace', 'The main royal palace of the Joseon Dynasty, built in 1395. You can admire beautiful traditional architecture including Geunjeongjeon Hall and Gyeonghoeru Pavilion.', 'History', '161 Sajik-ro, Jongno-gu, Seoul', 37.579617, 126.977041, 'https://ak-d.tripcdn.com/images/0104p120008ars39uB986.webp', '{"opening_hours": "09:00-18:00", "closed": "Tuesday", "admission_fee": "3000 KRW"}'::jsonb),
    (uuid_generate_v4(), 'N Seoul Tower', 'A landmark observatory located at 479.7m above sea level. You can enjoy a panoramic view of Seoul.', 'Attractions', '105 Namsan Park-gil, Yongsan-gu, Seoul', 37.551169, 126.988227, 'https://ak-d.tripcdn.com/images/100v0z000000nkadwE2AA_C_1200_800_Q70.webp', '{"opening_hours": "10:00-23:00", "admission_fee": "16000 KRW"}'::jsonb),
    (uuid_generate_v4(), 'Gwanghwamun Square', 'Seoul''s representative square featuring statues of King Sejong the Great and Admiral Yi Sun-sin.', 'Attractions', '172 Sejong-daero, Jongno-gu, Seoul', 37.572889, 126.976849, 'https://ak-d.tripcdn.com/images/01051120008c32dlbE44A.webp', '{"opening_hours": "24 hours", "admission_fee": "Free"}'::jsonb),
    (uuid_generate_v4(), 'Myeongdong Cathedral', 'Korea''s first Gothic-style cathedral, completed in 1898.', 'Culture', '74 Myeongdong-gil, Jung-gu, Seoul', 37.563600, 126.986870, 'https://ak-d.tripcdn.com/images/100f1f000001gqchv1B53.webp', '{"opening_hours": "09:00-21:00", "admission_fee": "Free"}'::jsonb),
    (uuid_generate_v4(), 'Bukchon Hanok Village', 'A historic residential area with dense traditional hanok houses, preserving the homes of Joseon Dynasty aristocrats.', 'Culture', '37 Gye-dong, Jongno-gu, Seoul', 37.582306, 126.985302, 'https://ak-d.tripcdn.com/images/100p11000000r4rhv9EF4.jpg', '{"opening_hours": "24 hours", "admission_fee": "Free"}'::jsonb)
ON CONFLICT (name) DO NOTHING;

-- Sample Quests (matching places)
INSERT INTO quests (name, description, latitude, longitude, reward_point, category)
VALUES
    ('Gyeongbokgung Palace', 'The main royal palace of the Joseon Dynasty, built in 1395. You can admire beautiful traditional architecture including Geunjeongjeon Hall and Gyeonghoeru Pavilion.', 37.579617, 126.977041, 100, 'History'),
    ('N Seoul Tower', 'A landmark observatory located at 479.7m above sea level. You can enjoy a panoramic view of Seoul.', 37.551169, 126.988227, 150, 'Attractions'),
    ('Gwanghwamun Square', 'Seoul''s representative square featuring statues of King Sejong the Great and Admiral Yi Sun-sin.', 37.572889, 126.976849, 90, 'Attractions'),
    ('Myeongdong Cathedral', 'Korea''s first Gothic-style cathedral, completed in 1898.', 37.563600, 126.986870, 80, 'Culture'),
    ('Bukchon Hanok Village', 'A historic residential area with dense traditional hanok houses, preserving the homes of Joseon Dynasty aristocrats.', 37.582306, 126.985302, 100, 'Culture');

-- Update places district from address
UPDATE places
SET district = extract_district_from_address(address)
WHERE district IS NULL AND address IS NOT NULL;

-- Update quests with place_id based on location matching (within 0.01 degrees ~ 1km)
UPDATE quests q
SET place_id = (
    SELECT p.id
    FROM places p
    WHERE ABS(p.latitude - q.latitude) < 0.01
      AND ABS(p.longitude - q.longitude) < 0.01
    ORDER BY 
        ABS(p.latitude - q.latitude) + ABS(p.longitude - q.longitude)
    LIMIT 1
)
WHERE q.place_id IS NULL;

-- Sample Quest Quizzes
INSERT INTO quest_quizzes (quest_id, question, options, correct_answer, hint, explanation, difficulty)
VALUES
    -- Gyeongbokgung Palace 퀴즈
    ((SELECT id FROM quests WHERE name = 'Gyeongbokgung Palace' LIMIT 1),
     '경복궁은 몇 년에 창건되었나요?',
     '["1392년", "1395년", "1400년", "1405년"]'::jsonb,
     1,
     '조선 건국 후 3년',
     '경복궁은 조선왕조의 법궁으로 1395년(태조 4년)에 창건되었습니다.',
     'easy'),
    
    ((SELECT id FROM quests WHERE name = 'Gyeongbokgung Palace' LIMIT 1),
     '경복궁의 정전(正殿) 이름은 무엇인가요?',
     '["근정전", "사정전", "교태전", "강녕전"]'::jsonb,
     0,
     '정전은 왕이 신하들을 만나고 국가의 중요한 의식을 거행하던 곳입니다',
     '근정전은 경복궁의 정전으로, 왕이 조회를 받고 국가의 중요한 의식을 거행하던 곳입니다.',
     'medium'),
    
    -- N Seoul Tower 퀴즈
    ((SELECT id FROM quests WHERE name = 'N Seoul Tower' LIMIT 1),
     'N서울타워의 해발고도는 얼마인가요?',
     '["479.7m", "500m", "450m", "520m"]'::jsonb,
     0,
     '타워의 높이는 약 480m 정도입니다',
     'N서울타워는 해발 479.7m에 위치한 서울의 랜드마크입니다.',
     'easy'),
    
    ((SELECT id FROM quests WHERE name = 'N Seoul Tower' LIMIT 1),
     'N서울타워가 위치한 산의 이름은 무엇인가요?',
     '["북한산", "남산", "인왕산", "도봉산"]'::jsonb,
     1,
     '서울 중심부에 위치한 서울의 대표적인 산입니다',
     'N서울타워는 남산에 위치해 있으며, 서울 시내를 한눈에 내려다볼 수 있습니다.',
     'easy'),
    
    -- Gwanghwamun Square 퀴즈
    ((SELECT id FROM quests WHERE name = 'Gwanghwamun Square' LIMIT 1),
     '광화문광장에 세워진 세종대왕 동상의 특징은 무엇인가요?',
     '["한글을 발명한 왕", "조선을 건국한 왕", "임진왜란을 승리로 이끈 왕", "고려를 건국한 왕"]'::jsonb,
     0,
     '한글 창제와 관련이 있습니다',
     '세종대왕은 한글(훈민정음)을 창제한 왕으로, 광화문광장에는 세종대왕 동상이 세워져 있습니다.',
     'easy'),
    
    ((SELECT id FROM quests WHERE name = 'Gwanghwamun Square' LIMIT 1),
     '광화문광장에 함께 세워진 또 다른 동상의 주인공은 누구인가요?',
     '["이순신", "김유신", "을지문덕", "강감찬"]'::jsonb,
     0,
     '임진왜란 때 활약한 해군 장수입니다',
     '광화문광장에는 세종대왕 동상과 함께 이순신 장군 동상이 세워져 있습니다.',
     'medium'),
    
    -- Myeongdong Cathedral 퀴즈
    ((SELECT id FROM quests WHERE name = 'Myeongdong Cathedral' LIMIT 1),
     '명동성당이 완공된 연도는 언제인가요?',
     '["1895년", "1898년", "1900년", "1902년"]'::jsonb,
     1,
     '19세기 말에 완공되었습니다',
     '명동성당은 한국 최초의 고딕 양식 성당으로 1898년에 완공되었습니다.',
     'medium'),
    
    ((SELECT id FROM quests WHERE name = 'Myeongdong Cathedral' LIMIT 1),
     '명동성당의 건축 양식은 무엇인가요?',
     '["바로크 양식", "고딕 양식", "로마네스크 양식", "르네상스 양식"]'::jsonb,
     1,
     '첫 번째로 지어진 한국의 이 양식 성당입니다',
     '명동성당은 한국 최초의 고딕 양식 성당으로, 높은 첨탑과 아치형 창문이 특징입니다.',
     'easy'),
    
    -- Bukchon Hanok Village 퀴즈
    ((SELECT id FROM quests WHERE name = 'Bukchon Hanok Village' LIMIT 1),
     '북촌한옥마을이 위치한 지역은 어디인가요?',
     '["종로구", "강남구", "서초구", "용산구"]'::jsonb,
     0,
     '경복궁과 가까운 지역입니다',
     '북촌한옥마을은 종로구 계동과 가회동 일대에 위치한 전통 한옥 밀집 지역입니다.',
     'easy'),
    
    ((SELECT id FROM quests WHERE name = 'Bukchon Hanok Village' LIMIT 1),
     '북촌한옥마을의 주요 특징은 무엇인가요?',
     '["조선시대 귀족들의 주거지", "상인들의 상업지구", "궁궐의 부속 건물", "사찰 건물"]'::jsonb,
     0,
     '조선시대 상류층이 살던 곳입니다',
     '북촌한옥마을은 조선시대 양반과 귀족들이 거주하던 주거지역으로, 전통 한옥이 밀집해 있습니다.',
     'medium');

-- Sample Rewards
INSERT INTO rewards (name, type, point_cost, description, is_active)
VALUES
    ('Seoul Travel Badge', 'badge', 50, 'Commemorative badge for completing your first quest', TRUE),
    ('Cafe Discount Coupon', 'coupon', 100, '20% discount at partner cafes in Seoul', TRUE),
    ('Gyeongbokgung Palace Admission Ticket', 'coupon', 200, 'Free admission ticket to Gyeongbokgung Palace', TRUE),
    ('Seoul Tour Master Badge', 'badge', 500, 'Commemorative badge for completing all quests', TRUE),
    ('Hanbok Experience Coupon', 'coupon', 300, '50% discount on hanbok rental', TRUE);

-- Table Comments
COMMENT ON TABLE users IS '사용자 정보';
COMMENT ON COLUMN users.password_hash IS 'bcrypt hashed password for authentication';
COMMENT ON TABLE places IS 'AR 카메라로 촬영 가능한 서울 주요 장소 정보';
COMMENT ON TABLE quests IS '장소 기반 퀘스트 (VLM places 연동 가능)';
COMMENT ON TABLE quest_quizzes IS '퀘스트별 객관식 퀴즈';
COMMENT ON TABLE user_quests IS '사용자별 퀘스트 진행 상황';
COMMENT ON TABLE user_quest_progress IS '사용자별 퀘스트 & 퀴즈 상세 진행 상황';
COMMENT ON TABLE points IS '포인트 트랜잭션 로그';
COMMENT ON TABLE rewards IS '포인트로 교환 가능한 리워드 아이템';
COMMENT ON TABLE user_rewards IS '사용자가 획득한 리워드 목록';
COMMENT ON TABLE chat_logs IS 'AI 도슨트 대화 기록';
COMMENT ON COLUMN chat_logs.mode IS '채팅 모드: explore(탐색 모드), quest(퀘스트 모드)';
COMMENT ON COLUMN chat_logs.function_type IS '기능 타입: rag_chat(일반 RAG 채팅), vlm_chat(VLM 채팅), route_recommend(경로 추천), image_similarity(이미지 유사도)';
COMMENT ON COLUMN chat_logs.image_url IS '이미지 URL (퀘스트 모드 VLM 채팅용)';
COMMENT ON COLUMN chat_logs.chat_session_id IS '채팅 세션 ID (같은 대화를 묶는 UUID)';
COMMENT ON COLUMN chat_logs.title IS '채팅 세션 제목 (일반 채팅: 첫 질문, 여행 일정: 테마)';
COMMENT ON COLUMN chat_logs.is_read_only IS '읽기 전용 여부 (여행 일정은 true)';
COMMENT ON TABLE vlm_logs IS 'VLM 이미지 분석 로그';

-- Column Comments for places table
COMMENT ON COLUMN places.source IS '데이터 출처: manual(수동입력), tour_api(TourAPI), visit_seoul(VISIT SEOUL API), both(양쪽 모두)';
COMMENT ON COLUMN places.metadata IS '상세 메타데이터 (JSONB): tour_api, visit_seoul, rag_text 등 포함';
COMMENT ON COLUMN places.images IS '이미지 URL 배열 (JSONB)';
COMMENT ON COLUMN places.district IS '자치구 (주소에서 정규식으로 추출: 예: 종로구, 강남구)';

-- Update table statistics for query optimization
ANALYZE places;
ANALYZE quests;
