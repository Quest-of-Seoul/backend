-- Quest of Seoul Database Schema
-- Run this in Supabase SQL Editor

-- Enable UUID extension
create extension if not exists "uuid-ossp";

-- Users table
create table users (
  id uuid primary key default uuid_generate_v4(),
  email text unique not null,
  nickname text,
  joined_at timestamp default now()
);

-- Quests table
create table quests (
  id serial primary key,
  name text not null,
  description text,
  lat float8 not null,
  lon float8 not null,
  reward_point int default 100,
  created_at timestamp default now()
);

-- User Quest Log (tracks quest progress)
create table user_quests (
  id serial primary key,
  user_id uuid references users(id) on delete cascade,
  quest_id int references quests(id) on delete cascade,
  status text default 'in_progress' check (status in ('in_progress', 'completed', 'failed')),
  started_at timestamp default now(),
  completed_at timestamp,
  unique(user_id, quest_id)
);

-- Points table (transaction log)
create table points (
  id serial primary key,
  user_id uuid references users(id) on delete cascade,
  value int not null,
  reason text,
  created_at timestamp default now()
);

-- Chat Logs (AI docent conversation history)
create table chat_logs (
  id serial primary key,
  user_id uuid references users(id) on delete cascade,
  landmark text,
  user_message text,
  ai_response text,
  created_at timestamp default now()
);

-- Rewards table (items available for redemption)
create table rewards (
  id serial primary key,
  name text not null,
  type text not null check (type in ('badge', 'coupon', 'item')),
  point_cost int not null,
  description text,
  image_url text,
  expire_date date,
  is_active boolean default true,
  created_at timestamp default now()
);

-- User Rewards (claimed rewards)
create table user_rewards (
  id serial primary key,
  user_id uuid references users(id) on delete cascade,
  reward_id int references rewards(id) on delete cascade,
  claimed_at timestamp default now(),
  used_at timestamp,
  qr_code text
);

-- Indexes for performance
create index idx_user_quests_user_id on user_quests(user_id);
create index idx_user_quests_quest_id on user_quests(quest_id);
create index idx_points_user_id on points(user_id);
create index idx_chat_logs_user_id on chat_logs(user_id);
create index idx_user_rewards_user_id on user_rewards(user_id);

-- Function to get user total points
create or replace function get_user_points(user_uuid uuid)
returns int as $$
  select coalesce(sum(value), 0)::int from points where user_id = user_uuid;
$$ language sql stable;

-- Row Level Security (RLS) policies
alter table users enable row level security;
alter table user_quests enable row level security;
alter table points enable row level security;
alter table chat_logs enable row level security;
alter table user_rewards enable row level security;

-- Users can only read/update their own data
create policy "Users can view own data" on users
  for select using (auth.uid() = id);

create policy "Users can update own data" on users
  for update using (auth.uid() = id);

create policy "Users can view own quests" on user_quests
  for select using (auth.uid() = user_id);

create policy "Users can view own points" on points
  for select using (auth.uid() = user_id);

create policy "Users can view own chat logs" on chat_logs
  for select using (auth.uid() = user_id);

create policy "Users can view own rewards" on user_rewards
  for select using (auth.uid() = user_id);

-- Public read access for quests and rewards
alter table quests enable row level security;
alter table rewards enable row level security;

create policy "Anyone can view quests" on quests
  for select using (true);

create policy "Anyone can view active rewards" on rewards
  for select using (is_active = true);
