-- Quest of Seoul

-- 데이터베이스 생성
-- CREATE DATABASE IF NOT EXISTS quest_of_seoul CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- USE quest_of_seoul;

-- Users 테이블
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    email VARCHAR(255) NOT NULL UNIQUE,
    nickname VARCHAR(100),
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_users_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Places 테이블
CREATE TABLE IF NOT EXISTS places (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    name VARCHAR(255) NOT NULL,
    name_en VARCHAR(255),
    description TEXT,
    category VARCHAR(50),
    address VARCHAR(500),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    image_url TEXT,
    images JSON,
    metadata JSON,
    source VARCHAR(20) DEFAULT 'manual',
    is_active BOOLEAN DEFAULT TRUE,
    view_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_places_category (category),
    INDEX idx_places_name (name),
    INDEX idx_places_name_en (name_en),
    INDEX idx_places_location (latitude, longitude),
    INDEX idx_places_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Quests 테이블
CREATE TABLE IF NOT EXISTS quests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    place_id VARCHAR(36),
    name VARCHAR(255) NOT NULL,
    title VARCHAR(255),
    description TEXT,
    category VARCHAR(50),
    lat DOUBLE NOT NULL,
    lon DOUBLE NOT NULL,
    reward_point INT DEFAULT 100,
    points INT DEFAULT 10,
    difficulty VARCHAR(20) DEFAULT 'easy',
    is_active BOOLEAN DEFAULT TRUE,
    completion_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (place_id) REFERENCES places(id) ON DELETE CASCADE,
    INDEX idx_quests_place_id (place_id),
    INDEX idx_quests_category (category),
    INDEX idx_quests_is_active (is_active),
    INDEX idx_quests_location (lat, lon)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Quest Quizzes 테이블
CREATE TABLE IF NOT EXISTS quest_quizzes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    quest_id INT NOT NULL,
    question TEXT NOT NULL,
    options JSON NOT NULL,
    correct_answer INT NOT NULL CHECK (correct_answer >= 0 AND correct_answer < 4),
    hint TEXT,
    explanation TEXT,
    difficulty VARCHAR(20) DEFAULT 'easy',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (quest_id) REFERENCES quests(id) ON DELETE CASCADE,
    INDEX idx_quest_quizzes_quest_id (quest_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- User Quests 테이블
CREATE TABLE IF NOT EXISTS user_quests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    quest_id INT NOT NULL,
    status VARCHAR(20) DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'completed', 'failed')),
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    UNIQUE KEY unique_user_quest (user_id, quest_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (quest_id) REFERENCES quests(id) ON DELETE CASCADE,
    INDEX idx_user_quests_user_id (user_id),
    INDEX idx_user_quests_quest_id (quest_id),
    INDEX idx_user_quests_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- User Quest Progress 테이블
CREATE TABLE IF NOT EXISTS user_quest_progress (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    quest_id INT NOT NULL,
    status VARCHAR(20) DEFAULT 'in_progress',
    quiz_attempts INT DEFAULT 0,
    quiz_correct BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_user_quest_progress (user_id, quest_id),
    FOREIGN KEY (quest_id) REFERENCES quests(id) ON DELETE CASCADE,
    INDEX idx_user_quest_progress_user_id (user_id),
    INDEX idx_user_quest_progress_quest_id (quest_id),
    INDEX idx_user_quest_progress_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Points 테이블
CREATE TABLE IF NOT EXISTS points (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    value INT NOT NULL,
    reason VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_points_user_id (user_id),
    INDEX idx_points_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Rewards 테이블
CREATE TABLE IF NOT EXISTS rewards (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(20) NOT NULL CHECK (type IN ('badge', 'coupon', 'item')),
    point_cost INT NOT NULL,
    description TEXT,
    image_url TEXT,
    expire_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_rewards_type (type),
    INDEX idx_rewards_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- User Rewards 테이블
CREATE TABLE IF NOT EXISTS user_rewards (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    reward_id INT NOT NULL,
    claimed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    used_at TIMESTAMP NULL,
    qr_code VARCHAR(500),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (reward_id) REFERENCES rewards(id) ON DELETE CASCADE,
    INDEX idx_user_rewards_user_id (user_id),
    INDEX idx_user_rewards_reward_id (reward_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Chat Logs 테이블
CREATE TABLE IF NOT EXISTS chat_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    landmark VARCHAR(255),
    user_message TEXT,
    ai_response TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_chat_logs_user_id (user_id),
    INDEX idx_chat_logs_landmark (landmark),
    INDEX idx_chat_logs_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- VLM Logs 테이블
CREATE TABLE IF NOT EXISTS vlm_logs (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    user_id VARCHAR(36) NOT NULL,
    image_url TEXT,
    image_hash VARCHAR(64),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    vlm_response TEXT,
    final_description TEXT,
    matched_place_id VARCHAR(36),
    similar_places JSON,
    confidence_score DECIMAL(3, 2),
    processing_time_ms INT,
    pinecone_vector_id VARCHAR(255),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (matched_place_id) REFERENCES places(id) ON DELETE SET NULL,
    INDEX idx_vlm_logs_user_id (user_id),
    INDEX idx_vlm_logs_place_id (matched_place_id),
    INDEX idx_vlm_logs_image_hash (image_hash),
    INDEX idx_vlm_logs_created_at (created_at),
    INDEX idx_vlm_logs_location (latitude, longitude),
    INDEX idx_vlm_logs_pinecone_id (pinecone_vector_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Stored Procedures & Functions
-- 사용자 총 포인트 조회 함수
DELIMITER //
CREATE FUNCTION IF NOT EXISTS get_user_points(user_uuid VARCHAR(36))
RETURNS INT
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE total_points INT;
    SELECT COALESCE(SUM(value), 0) INTO total_points
    FROM points
    WHERE user_id = user_uuid;
    RETURN total_points;
END//
DELIMITER ;

-- 반경 내 장소 검색 프로시저
DELIMITER //
CREATE PROCEDURE IF NOT EXISTS search_places_by_radius(
    IN lat DECIMAL(10, 8),
    IN lon DECIMAL(11, 8),
    IN radius_km FLOAT,
    IN limit_count INT
)
BEGIN
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
        ) AS distance_km
    FROM places p
    WHERE p.is_active = TRUE
    HAVING distance_km <= radius_km
    ORDER BY distance_km
    LIMIT limit_count;
END//
DELIMITER ;

-- 주변 퀘스트 검색 프로시저
DELIMITER //
CREATE PROCEDURE IF NOT EXISTS search_nearby_quests(
    IN lat DECIMAL(10, 8),
    IN lon DECIMAL(11, 8),
    IN radius_km FLOAT,
    IN limit_count INT
)
BEGIN
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
        ) AS distance_km,
        q.id AS quest_id,
        q.points AS quest_points
    FROM places p
    INNER JOIN quests q ON p.id = q.place_id
    WHERE q.is_active = TRUE
        AND p.is_active = TRUE
    HAVING distance_km <= radius_km
    ORDER BY distance_km
    LIMIT limit_count;
END//
DELIMITER ;

-- VLM 로그 조회 프로시저
DELIMITER //
CREATE PROCEDURE IF NOT EXISTS get_user_vlm_logs(
    IN user_uuid VARCHAR(36),
    IN limit_count INT
)
BEGIN
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
END//
DELIMITER ;

-- 이미지 해시로 캐시된 VLM 결과 조회
DELIMITER //
CREATE PROCEDURE IF NOT EXISTS get_cached_vlm_result(
    IN hash VARCHAR(64)
)
BEGIN
    SELECT
        v.*,
        p.name AS matched_place_name
    FROM vlm_logs v
    LEFT JOIN places p ON v.matched_place_id = p.id
    WHERE v.image_hash = hash
        AND v.error_message IS NULL
    ORDER BY v.created_at DESC
    LIMIT 1;
END//
DELIMITER ;

-- 샘플 데이터 삽입
-- Places 샘플 데이터
INSERT INTO places (id, name, name_en, description, category, address, latitude, longitude, image_url, metadata)
VALUES
    (UUID(), '경복궁', 'Gyeongbokgung Palace', '조선시대 대표 궁궐로, 1395년에 창건되었습니다. 근정전, 경회루 등 아름다운 전통 건축물을 감상할 수 있습니다.', '역사유적', '서울특별시 종로구 사직로 161', 37.579617, 126.977041, 'https://ak-d.tripcdn.com/images/0104p120008ars39uB986_W_1440_810_Q80.webp?proc=source%2ftrip&proc=source%2ftrip', JSON_OBJECT('opening_hours', '09:00-18:00', 'closed', '화요일', 'admission_fee', '3000원')),
    (UUID(), '남산서울타워', 'N Seoul Tower', '서울의 랜드마크로 해발 479.7m에 위치한 전망대입니다. 서울 시내 전경을 한눈에 볼 수 있습니다.', '관광지', '서울특별시 용산구 남산공원길 105', 37.551169, 126.988227, 'https://ak-d.tripcdn.com/images/1lo5r12000jt8ej8cD340_W_1440_810_Q80.webp?proc=source%2ftrip&proc=source%2ftrip', JSON_OBJECT('opening_hours', '10:00-23:00', 'admission_fee', '16000원')),
    (UUID(), '광화문광장', 'Gwanghwamun Square', '세종대왕과 이순신 장군 동상이 있는 서울의 대표 광장입니다.', '광장', '서울특별시 종로구 세종대로 172', 37.572889, 126.976849, 'https://ak-d.tripcdn.com/images/01051120008c32dlbE44A_W_1440_810_Q80.webp?proc=source%2ftrip&proc=source%2ftrip', JSON_OBJECT('opening_hours', '24시간', 'admission_fee', '무료')),
    (UUID(), '명동성당', 'Myeongdong Cathedral', '1898년에 완공된 한국 최초의 고딕 양식 성당입니다.', '종교시설', '서울특별시 중구 명동길 74', 37.563600, 126.986870, 'https://ak-d.tripcdn.com/images/100f1f000001gqchv1B53_W_1440_810_Q80.webp?proc=source%2ftrip&proc=source%2ftrip', JSON_OBJECT('opening_hours', '09:00-21:00', 'admission_fee', '무료')),
    (UUID(), '북촌한옥마을', 'Bukchon Hanok Village', '전통 한옥이 밀집한 역사적 주거지역으로 조선시대 양반들의 집이 보존되어 있습니다.', '문화마을', '서울특별시 종로구 계동길 37', 37.582306, 126.985302, 'https://ak-d.tripcdn.com/images/100p11000000r4rhv9EF4_C_1200_800_Q70.jpg?proc=source%2ftrip', JSON_OBJECT('opening_hours', '24시간', 'admission_fee', '무료'))
ON DUPLICATE KEY UPDATE id=id;

-- Quests 샘플 데이터
INSERT INTO quests (name, description, lat, lon, reward_point)
VALUES
    ('경복궁 (Gyeongbokgung Palace)', '조선왕조의 법궁으로, 서울의 대표적인 역사 유적지입니다.', 37.5796, 126.9770, 100),
    ('남산타워 (N Seoul Tower)', '서울의 상징적인 랜드마크로, 도시 전경을 한눈에 볼 수 있습니다.', 37.5512, 126.9882, 150),
    ('명동 (Myeongdong)', '서울의 쇼핑과 먹거리의 중심지입니다.', 37.5636, 126.9865, 80),
    ('인사동 (Insadong)', '전통 문화와 예술이 살아있는 거리입니다.', 37.5730, 126.9856, 90),
    ('홍대 (Hongdae)', '젊음과 문화가 넘치는 예술의 거리입니다.', 37.5563, 126.9236, 70);

-- Rewards 샘플 데이터
INSERT INTO rewards (name, type, point_cost, description, is_active)
VALUES
    ('서울 여행 뱃지', 'badge', 50, '첫 퀘스트 완료 기념 뱃지', TRUE),
    ('카페 할인 쿠폰', 'coupon', 100, '서울 내 제휴 카페 20% 할인', TRUE),
    ('경복궁 입장권', 'coupon', 200, '경복궁 무료 입장권', TRUE),
    ('서울 투어 마스터 뱃지', 'badge', 500, '모든 퀘스트 완료 기념 뱃지', TRUE),
    ('한복 체험 쿠폰', 'coupon', 300, '한복 대여 50% 할인', TRUE);

-- 테이블 코멘트
ALTER TABLE users COMMENT = '사용자 정보';
ALTER TABLE places COMMENT = 'AR 카메라로 촬영 가능한 서울 주요 장소 정보';
ALTER TABLE quests COMMENT = '장소 기반 퀘스트 (VLM places 연동 가능)';
ALTER TABLE quest_quizzes COMMENT = '퀘스트별 객관식 퀴즈';
ALTER TABLE user_quests COMMENT = '사용자별 퀘스트 진행 상황';
ALTER TABLE user_quest_progress COMMENT = '사용자별 퀘스트 & 퀴즈 상세 진행 상황';
ALTER TABLE points COMMENT = '포인트 트랜잭션 로그';
ALTER TABLE rewards COMMENT = '포인트로 교환 가능한 리워드 아이템';
ALTER TABLE user_rewards COMMENT = '사용자가 획득한 리워드 목록';
ALTER TABLE chat_logs COMMENT = 'AI 도슨트 대화 기록';

SELECT 'Quest of Seoul MySQL Schema Setup Complete!' AS Status;
SELECT 'Total Tables: 11 (벡터 검색은 Pinecone 사용)' AS Info;
