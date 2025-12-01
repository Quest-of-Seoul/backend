-- Quest of Seoul - Supabase (PostgreSQL) Schema (No Sample Data)

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

-- GIN indexes for JSONB fields
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
    score INTEGER DEFAULT 0,
    correct_count INTEGER DEFAULT 0,
    used_hint BOOLEAN DEFAULT FALSE,
    current_quiz INTEGER DEFAULT 0,
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
    type VARCHAR(20) NOT NULL CHECK (type IN ('badge', 'coupon', 'item', 'food', 'cafe', 'shopping', 'ticket', 'activity', 'entertainment', 'beauty', 'wellness')),
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
    quest_step INT4,
    options JSONB,
    selected_districts JSONB,
    selected_theme TEXT,
    include_cart BOOLEAN DEFAULT FALSE,
    prompt_step_text TEXT,
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
    
    match_result := regexp_match(addr, '[가-힣]+구');
    IF match_result IS NOT NULL AND array_length(match_result, 1) > 0 THEN
        district_name := match_result[1];
        RETURN district_name;
    END IF;
    
    match_result := regexp_match(addr, '[A-Za-z]+-gu', 'i');
    IF match_result IS NOT NULL AND array_length(match_result, 1) > 0 THEN
        district_name := match_result[1];
        RETURN district_name;
    END IF;
    
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

-- Table Comments
COMMENT ON TABLE users IS 'User information';
COMMENT ON COLUMN users.password_hash IS 'bcrypt hashed password for authentication';
COMMENT ON TABLE places IS 'Seoul major landmarks that can be photographed with AR camera';
COMMENT ON TABLE quests IS 'Place-based quests';
COMMENT ON TABLE quest_quizzes IS 'Quiz questions for each quest';
COMMENT ON TABLE user_quests IS 'User quest progress';
COMMENT ON TABLE user_quest_progress IS 'User quest & quiz detailed progress';
COMMENT ON COLUMN user_quest_progress.score IS 'Total quiz score';
COMMENT ON COLUMN user_quest_progress.correct_count IS 'Number of correct answers';
COMMENT ON COLUMN user_quest_progress.used_hint IS 'Whether hint was used in current question';
COMMENT ON COLUMN user_quest_progress.current_quiz IS 'Current quiz number';
COMMENT ON TABLE points IS 'Point transaction log';
COMMENT ON TABLE rewards IS 'Rewards that can be redeemed with points';
COMMENT ON TABLE user_rewards IS 'List of rewards obtained by users';
COMMENT ON TABLE chat_logs IS 'AI docent conversation history';
COMMENT ON COLUMN chat_logs.mode IS 'Chat mode: explore, quest';
COMMENT ON COLUMN chat_logs.function_type IS 'Function type: rag_chat, vlm_chat, route_recommend, image_similarity';
COMMENT ON COLUMN chat_logs.image_url IS 'Image URL';
COMMENT ON COLUMN chat_logs.chat_session_id IS 'Chat session ID';
COMMENT ON COLUMN chat_logs.title IS 'Chat session title';
COMMENT ON COLUMN chat_logs.is_read_only IS 'Read-only status';
COMMENT ON TABLE vlm_logs IS 'VLM image analysis log';

-- Column Comments for places table
COMMENT ON COLUMN places.source IS 'Data source: manual, tour_api, visit_seoul, both';
COMMENT ON COLUMN places.metadata IS 'Detailed metadata: tour_api, visit_seoul, rag_text, etc.';
COMMENT ON COLUMN places.images IS 'Image URL array';
COMMENT ON COLUMN places.district IS 'District';

-- Update table statistics for query optimization
ANALYZE places;
ANALYZE quests;
