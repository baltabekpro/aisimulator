-- Миграция для добавления внешнего ID в таблицу пользователей и создания таблиц профилей

-- 1. Добавляем колонку external_id в таблицу users, если ее еще нет
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                  WHERE table_name='users' AND column_name='external_id') THEN
        ALTER TABLE users ADD COLUMN external_id VARCHAR(100);
        CREATE INDEX idx_users_external_id ON users(external_id);
    END IF;
END $$;

-- 2. Создаем таблицу user_profiles, если ее еще нет
CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    name VARCHAR(100),
    age INTEGER,
    gender VARCHAR(20),
    location VARCHAR(100),
    bio TEXT,
    interests JSONB DEFAULT '[]'::jsonb,
    matching_preferences JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Создаем уникальный индекс на user_id
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_profiles_user_id ON user_profiles(user_id);

-- 3. Создаем таблицу user_photos, если ее еще нет
CREATE TABLE IF NOT EXISTS user_photos (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    url VARCHAR(500) NOT NULL,
    filename VARCHAR(200) NOT NULL,
    content_type VARCHAR(100),
    size INTEGER,
    is_primary BOOLEAN DEFAULT FALSE,
    is_moderated BOOLEAN DEFAULT FALSE,
    "order" INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Создаем индекс на user_id для быстрого поиска фотографий пользователя
CREATE INDEX IF NOT EXISTS idx_user_photos_user_id ON user_photos(user_id);