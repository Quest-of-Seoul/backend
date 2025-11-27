-- Add quiz scoring system columns to user_quest_progress table

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

-- Add comment for clarity
COMMENT ON COLUMN user_quest_progress.score IS 'Total quiz score (max 100 points)';
COMMENT ON COLUMN user_quest_progress.correct_count IS 'Number of correct answers';
COMMENT ON COLUMN user_quest_progress.used_hint IS 'Whether hint was used in current question';
COMMENT ON COLUMN user_quest_progress.current_quiz IS 'Current quiz number (0-4 for 5 questions)';



