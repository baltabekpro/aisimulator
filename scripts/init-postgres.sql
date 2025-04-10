-- PostgreSQL initialization script

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create users table if it doesn't exist
CREATE TABLE IF NOT EXISTS users (
  user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  username VARCHAR(50) UNIQUE NOT NULL,
  email VARCHAR(100) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  name VARCHAR(100),
  is_active BOOLEAN DEFAULT TRUE,
  is_admin BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP
);

-- Create characters table
CREATE TABLE IF NOT EXISTS characters (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name VARCHAR(100) NOT NULL,
  age INTEGER,
  gender VARCHAR(20) DEFAULT 'female' NOT NULL,
  personality JSONB DEFAULT '{}',
  background TEXT,
  interests JSONB DEFAULT '[]',
  appearance JSONB DEFAULT '{}',
  system_prompt TEXT,
  greeting_message TEXT,
  avatar_url TEXT,
  creator_id UUID,
  is_active BOOLEAN DEFAULT TRUE,
  character_metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP,
  CONSTRAINT fk_creator
    FOREIGN KEY(creator_id) 
    REFERENCES users(user_id)
    ON DELETE SET NULL
);

-- Create messages table
CREATE TABLE IF NOT EXISTS messages (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  sender_id UUID NOT NULL,
  sender_type VARCHAR(50) NOT NULL,
  recipient_id UUID NOT NULL,
  recipient_type VARCHAR(50) NOT NULL,
  content TEXT NOT NULL,
  emotion VARCHAR(50),
  is_read BOOLEAN DEFAULT FALSE,
  is_gift BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP
);

-- Create index to improve joins on sender and recipient IDs
CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_id, sender_type);
CREATE INDEX IF NOT EXISTS idx_messages_recipient ON messages(recipient_id, recipient_type);

-- Create memory_entries table for character memories
CREATE TABLE IF NOT EXISTS memory_entries (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  character_id UUID NOT NULL,
  user_id UUID NOT NULL,
  type VARCHAR(50) NOT NULL,
  content TEXT NOT NULL,
  importance INTEGER DEFAULT 5,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP,
  CONSTRAINT fk_character
    FOREIGN KEY(character_id) 
    REFERENCES characters(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_user
    FOREIGN KEY(user_id) 
    REFERENCES users(user_id)
    ON DELETE CASCADE
);

-- Update to add matches table for character interactions

-- Create matches table if doesn't exist
CREATE TABLE IF NOT EXISTS matches (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL,
  character_id UUID NOT NULL,
  match_strength FLOAT DEFAULT 0.5,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP,
  CONSTRAINT fk_user
    FOREIGN KEY(user_id) 
    REFERENCES users(user_id)
    ON DELETE CASCADE,
  CONSTRAINT fk_character
    FOREIGN KEY(character_id) 
    REFERENCES characters(id)
    ON DELETE CASCADE
);

-- Create interactions table if doesn't exist
CREATE TABLE IF NOT EXISTS interactions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL,
  character_id UUID NOT NULL,
  interaction_type VARCHAR(50) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_interaction_user
    FOREIGN KEY(user_id) 
    REFERENCES users(user_id)
    ON DELETE CASCADE,
  CONSTRAINT fk_interaction_character
    FOREIGN KEY(character_id) 
    REFERENCES characters(id)
    ON DELETE CASCADE
);

-- Create indexes to improve query performance
CREATE INDEX IF NOT EXISTS idx_matches_user ON matches(user_id);
CREATE INDEX IF NOT EXISTS idx_matches_character ON matches(character_id);
CREATE INDEX IF NOT EXISTS idx_interactions_user ON interactions(user_id);
CREATE INDEX IF NOT EXISTS idx_interactions_character ON interactions(character_id);

-- Create test admin user (password: admin123)
INSERT INTO users (username, email, password_hash, name, is_admin, is_active)
SELECT 'admin', 'admin@example.com', crypt('admin123', gen_salt('bf')), 'Admin User', TRUE, TRUE
WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = 'admin');

-- Create test user (password: password123)
INSERT INTO users (username, email, password_hash, name, is_admin, is_active)
SELECT 'user', 'user@example.com', crypt('password123', gen_salt('bf')), 'Test User', FALSE, TRUE
WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = 'user');

-- Create test character if none exists
INSERT INTO characters (id, name, age, gender, personality, background, interests)
SELECT 
  '8c054f20-4a77-4eef-83e6-245d3456bdf1', 
  'Алиса', 
  24, 
  'female', 
  '["дружелюбная", "общительная", "веселая"]', 
  'Алиса - творческая личность, которая любит путешествовать и знакомиться с новыми людьми.', 
  '["музыка", "искусство", "путешествия"]'
WHERE NOT EXISTS (SELECT 1 FROM characters);

-- Add a second character
INSERT INTO characters (name, age, gender, personality, background, interests)
SELECT 
  'София', 
  22, 
  'female', 
  '["энергичная", "амбициозная", "уверенная"]', 
  'София - целеустремленная девушка, увлеченная саморазвитием и новыми технологиями.', 
  '["спорт", "бизнес", "технологии"]'
WHERE (SELECT COUNT(*) FROM characters) < 2;

-- Add a third character
INSERT INTO characters (name, age, gender, personality, background, interests)
SELECT 
  'Мария', 
  26, 
  'female', 
  '["умная", "спокойная", "загадочная"]', 
  'Мария - глубокая и философски настроенная натура, интересующаяся духовным развитием.', 
  '["чтение", "психология", "йога"]'
WHERE (SELECT COUNT(*) FROM characters) < 3;
