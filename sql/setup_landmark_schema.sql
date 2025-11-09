-- Insert sample quests (Seoul landmarks)
INSERT INTO quests (name, description, lat, lon, reward_point) VALUES
  ('경복궁 (Gyeongbokgung Palace)', '조선왕조의 법궁으로, 서울의 대표적인 역사 유적지입니다.', 37.5796, 126.9770, 100),
  ('남산타워 (N Seoul Tower)', '서울의 상징적인 랜드마크로, 도시 전경을 한눈에 볼 수 있습니다.', 37.5512, 126.9882, 150),
  ('명동 (Myeongdong)', '서울의 쇼핑과 먹거리의 중심지입니다.', 37.5636, 126.9865, 80),
  ('인사동 (Insadong)', '전통 문화와 예술이 살아있는 거리입니다.', 37.5730, 126.9856, 90),
  ('홍대 (Hongdae)', '젊음과 문화가 넘치는 예술의 거리입니다.', 37.5563, 126.9236, 70);

-- Insert sample rewards
INSERT INTO rewards (name, type, point_cost, description, is_active) VALUES
  ('서울 여행 뱃지', 'badge', 50, '첫 퀘스트 완료 기념 뱃지', true),
  ('카페 할인 쿠폰', 'coupon', 100, '서울 내 제휴 카페 20% 할인', true),
  ('경복궁 입장권', 'coupon', 200, '경복궁 무료 입장권', true),
  ('서울 투어 마스터 뱃지', 'badge', 500, '모든 퀘스트 완료 기념 뱃지', true),
  ('한복 체험 쿠폰', 'coupon', 300, '한복 대여 50% 할인', true);

-- Verify the data
SELECT * FROM quests;
SELECT * FROM rewards;
