-- https://www.notion.so/Supabase-2b86e0ddd21d80b9bb1aed5b40ee3ca7 스키마 수정 사항 적용
-- 이 파일은 temp/363b126a-cc37-4da3-a726-6028c30d2dec_Supabase_스키마_수정.pdf의 내용을 반영합니다

-- 명동 성당 퀴즈 3개 추가 (5개 맞추기 위함)
INSERT INTO quest_quizzes
(quest_id, question, options, correct_answer, hint, explanation, difficulty) 
VALUES
((SELECT id FROM quests WHERE name = 'Myeongdong Cathedral' LIMIT 1),
'명동성당은 일제강점기 당시 어떤 역할을 했나요?',
'["독립운동 비밀 회합 장소", "한국 최초의 은행 역할", "외국 공사관 숙소", "기상 관측소 역할"]'::jsonb,
0,
'민족운동의 상징적 공간.',
'명동성당은 독립운동가들의 비밀 회합 장소로 사용되며 민주-인권 운동의 상징적 공간이 되었다.',
'medium'),
((SELECT id FROM quests WHERE name = 'Myeongdong Cathedral' LIMIT 1),
'명동성당 내부 스테인드글라스는 주로 어떤 내용을 담고 있나요?',
'["예수와 성모 마리아의 생애", "한국 전통 민속 그림", "세계 4대 문명", "십자군 전쟁"]'::jsonb,
0,
'종교적 의미가 중심.',
'스테인드글라스는 예수-성모 마리아의 생애 등 성경 장면을 묘사한 것이 대부분이다.',
'medium'),
((SELECT id FROM quests WHERE name = 'Myeongdong Cathedral' LIMIT 1),
'명동성당이 한국 천주교의 상징으로 자리 잡은 이유는 무엇인가요?',
'["순교자 정신을 기리고 한국 천주교의 중심 역할을 했기 때문", "정부의 국교 건물로 지정되었기 때문", "세계 최초로 건립된 천주교 성당이기 때문", "유네스코 세계유산 등재 때문"]'::jsonb,
0,
'천주교·민주화 운동 상징성.',
'명동성당은 한국 천주교의 중심이며 민주화·인권 운동의 핵심 공간으로서 큰 상징성을 가진다.',
'hard')
ON CONFLICT DO NOTHING;

-- user_quest_progress 테이블에 퀴즈 점수 컬럼 추가
-- Add score column (총 퀴즈 점수)
ALTER TABLE user_quest_progress
ADD COLUMN IF NOT EXISTS score INTEGER DEFAULT 0;

-- Add correct_count column (맞춘 문제 개수)
ALTER TABLE user_quest_progress
ADD COLUMN IF NOT EXISTS correct_count INTEGER DEFAULT 0;

-- Add used_hint column (힌트 사용 여부)
ALTER TABLE user_quest_progress
ADD COLUMN IF NOT EXISTS used_hint BOOLEAN DEFAULT FALSE;

-- Add current_quiz column (현재 진행 중인 퀴즈 번호)
ALTER TABLE user_quest_progress
ADD COLUMN IF NOT EXISTS current_quiz INTEGER DEFAULT 0;

-- Add quiz_attempts column (이미 있으면 스킵)
ALTER TABLE user_quest_progress
ADD COLUMN IF NOT EXISTS quiz_attempts INTEGER DEFAULT 0;

-- Add comments for clarity
COMMENT ON COLUMN user_quest_progress.score IS 'Total quiz score (max 100 points)';
COMMENT ON COLUMN user_quest_progress.correct_count IS 'Number of correct answers';
COMMENT ON COLUMN user_quest_progress.used_hint IS 'Whether hint was used in current question';
COMMENT ON COLUMN user_quest_progress.current_quiz IS 'Current quiz number (0-4 for 5 questions)';

-- Rewards 테이블 type 제약조건 수정
-- 기존 제약 조건 삭제
ALTER TABLE rewards
DROP CONSTRAINT IF EXISTS rewards_type_check;

-- 새로운 제약 조건 추가
ALTER TABLE rewards
ADD CONSTRAINT rewards_type_check
CHECK (
    type IN (
        'food',
        'cafe',
        'shopping',
        'ticket',
        'activity',
        'entertainment',
        'beauty',
        'wellness',
        'badge',  -- 기존 값 유지
        'coupon', -- 기존 값 유지
        'item'    -- 기존 값 유지
    )
) NOT VALID;

-- 제약 조건 검증
ALTER TABLE rewards VALIDATE CONSTRAINT rewards_type_check;

-- 쿠폰 20개 INSERT
INSERT INTO rewards (name, type, point_cost, description, image_url, expire_date, is_active)
VALUES
-- FOOD
('Shrimp Gyoza Dumpling', 'food', 200, 'Fresh handmade shrimp dumplings', 'https://placehold.co/300×300?text=Reward', now() + interval '60 days', true),
('Bibimbap Meal Kit', 'food', 250, 'Korean traditional bibimbap set', 'https://placehold.co/300×300?text=Reward', now() + interval '60 days', true),
('Tteokbokki Cup', 'food', 120, 'Spicy rice cake cup', 'https://placehold.co/300×300?text=Reward', now() + interval '60 days', true),
('Korean Fried Chicken Snack', 'food', 180, 'Small crispy chicken set', 'https://placehold.co/300×300?text=Reward', now() + interval '60 days', true),

-- CAFE
('Americano (Hot/Iced)', 'cafe', 150, 'Standard Americano coffee', 'https://placehold.co/300×300?text=Reward', now() + interval '60 days', true),
('Vanilla Latte', 'cafe', 190, 'Sweet vanilla latte drink', 'https://placehold.co/300×300?text=Reward', now() + interval '60 days', true),
('Matcha Latte', 'cafe', 200, 'Japanese matcha green latte', 'https://placehold.co/300×300?text=Reward', now() + interval '60 days', true),
('Cheesecake Slice', 'cafe', 220, 'New York cheesecake slice', 'https://placehold.co/300×300?text=Reward', now() + interval '60 days', true),

-- SHOPPING
('Korean Flag Keychain', 'shopping', 100, 'Korean themed souvenir keychain', 'https://placehold.co/300×300?text=Reward', now() + interval '60 days', true),
('Hanbok Mini Figure', 'shopping', 300, 'Miniature Hanbok doll figure', 'https://placehold.co/300×300?text=Reward', now() + interval '60 days', true),
('City Postcard Set', 'shopping', 80, 'Seoul city postcard set', 'https://placehold.co/300×300?text=Reward', now() + interval '60 days', true),
('Korean Socks Pack', 'shopping', 140, 'Funny Korean socks 1-pack', 'https://placehold.co/300×300?text=Reward', now() + interval '60 days', true),

-- TICKET
('Museum Entry Ticket', 'ticket', 350, 'Entry ticket for museum', 'https://placehold.co/300×300?text=Reward', now() + interval '60 days', true),
('Han River Cruise Ticket', 'ticket', 500, '30-minute Han river cruise', 'https://placehold.co/300×300?text=Reward', now() + interval '60 days', true),

-- ACTIVITY
('Pottery Experience Class', 'activity', 600, '1-hour pottery class experience', 'https://placehold.co/300×300?text=Reward', now() + interval '60 days', true),
('Korean Calligraphy Class', 'activity', 450, 'Traditional Korean calligraphy class', 'https://placehold.co/300×300?text=Reward', now() + interval '60 days', true),

-- ENTERTAINMENT
('VR Arcade Ticket', 'entertainment', 400, 'VR arcade shooting game ticket', 'https://placehold.co/300×300?text=Reward', now() + interval '60 days', true),
('Karaoke 30-Min Pass', 'entertainment', 250, '30 minutes at Karaoke room', 'https://placehold.co/300×300?text=Reward', now() + interval '60 days', true),

-- BEAUTY & WELLNESS
('Hand Spa Treatment', 'beauty', 350, 'Relaxing hand spa treatment', 'https://placehold.co/300×300?text=Reward', now() + interval '60 days', true),
('Fitness 1-Day Pass', 'wellness', 300, 'Gym access for one day', 'https://placehold.co/300×300?text=Reward', now() + interval '60 days', true)
ON CONFLICT DO NOTHING;

-- Chat_logs 테이블 확장 (이미 일부 있지만 확인)
-- image_url, function_type, mode는 이미 있음 (확인용)
-- 추가 컬럼들 확인 및 추가

-- quest_step: 단계 번호 저장
ALTER TABLE chat_logs
ADD COLUMN IF NOT EXISTS quest_step INT4;

-- options: 선택지 리스트 저장 (JSON 배열)
ALTER TABLE chat_logs
ADD COLUMN IF NOT EXISTS options JSONB;

-- selected_districts: ["강남구", "송파구"] 같은 리스트 저장
ALTER TABLE chat_logs
ADD COLUMN IF NOT EXISTS selected_districts JSONB;

-- selected_theme: 선택된 테마(text)
ALTER TABLE chat_logs
ADD COLUMN IF NOT EXISTS selected_theme TEXT;

-- include_cart: 장바구니 포함 여부
ALTER TABLE chat_logs
ADD COLUMN IF NOT EXISTS include_cart BOOL DEFAULT FALSE;

-- prompt_step_text: "지역을 선택해주세요" 같은 프롬프트 텍스트
ALTER TABLE chat_logs
ADD COLUMN IF NOT EXISTS prompt_step_text TEXT;

-- Storage 정책 추가 (Supabase Storage)
-- Note: 이 부분은 Supabase 대시보드에서 직접 실행해야 할 수 있습니다.
-- SQL로 실행하려면:
-- create policy "Allow authenticated uploads"
-- on storage.objects
-- for insert
-- to authenticated
-- with check (bucket_id = 'images');

DO $$
BEGIN
    RAISE NOTICE 'PDF 스키마 수정 사항 적용 완료!';
    RAISE NOTICE '1. 명동성당 퀴즈 3개 추가';
    RAISE NOTICE '2. user_quest_progress 컬럼 추가 (score, correct_count, used_hint, current_quiz)';
    RAISE NOTICE '3. rewards type 제약조건 수정';
    RAISE NOTICE '4. 쿠폰 20개 추가';
    RAISE NOTICE '5. chat_logs 컬럼 추가 (quest_step, options, selected_districts, selected_theme, include_cart, prompt_step_text)';
    RAISE NOTICE '6. Storage 정책은 Supabase 대시보드에서 수동으로 설정해야 합니다.';
END $$;
