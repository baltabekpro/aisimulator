-- Миграция для добавления таблиц для работы с мобильным приложением iOS

-- 1. Создаем таблицу device_tokens для push-уведомлений
CREATE TABLE IF NOT EXISTS device_tokens (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    device_token VARCHAR(255) NOT NULL,
    device_type VARCHAR(20) NOT NULL,
    app_version VARCHAR(20),
    os_version VARCHAR(20),
    device_model VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Создаем индекс на device_token для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_device_tokens_device_token ON device_tokens(device_token);

-- Создаем индекс на user_id для быстрого поиска устройств пользователя
CREATE INDEX IF NOT EXISTS idx_device_tokens_user_id ON device_tokens(user_id);

-- 2. Создаем таблицу purchase_products для хранения информации о доступных товарах
CREATE TABLE IF NOT EXISTS purchase_products (
    id UUID PRIMARY KEY,
    product_id VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    type VARCHAR(20) NOT NULL,
    price_tier VARCHAR(20) NOT NULL,
    price_usd FLOAT NOT NULL,
    stars_amount INTEGER,
    duration_days INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- 3. Создаем таблицу in_app_purchases для хранения информации о покупках
CREATE TABLE IF NOT EXISTS in_app_purchases (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    product_id VARCHAR(100) NOT NULL,
    transaction_id VARCHAR(100) NOT NULL UNIQUE,
    receipt_data TEXT NOT NULL,
    purchase_date TIMESTAMP WITH TIME ZONE NOT NULL,
    expiration_date TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) NOT NULL DEFAULT 'completed',
    quantity INTEGER NOT NULL DEFAULT 1,
    price FLOAT,
    currency VARCHAR(10),
    environment VARCHAR(20) NOT NULL DEFAULT 'production',
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Создаем индекс на user_id для быстрого поиска покупок пользователя
CREATE INDEX IF NOT EXISTS idx_in_app_purchases_user_id ON in_app_purchases(user_id);

-- Создаем индекс на product_id для быстрого поиска покупок по товару
CREATE INDEX IF NOT EXISTS idx_in_app_purchases_product_id ON in_app_purchases(product_id);

-- Создаем индекс на transaction_id для быстрого поиска по ID транзакции
CREATE INDEX IF NOT EXISTS idx_in_app_purchases_transaction_id ON in_app_purchases(transaction_id);

-- 4. Добавляем параметр настройки для секрета покупок в приложении
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                  WHERE table_name='settings' AND column_name='iap_secret') THEN
        ALTER TABLE settings ADD COLUMN iap_secret VARCHAR(100);
    END IF;
END $$;