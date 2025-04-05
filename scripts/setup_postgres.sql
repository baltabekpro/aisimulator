-- Скрипт для настройки базы данных PostgreSQL

-- Создание пользователя aibot если не существует
DO
$$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'aibot') THEN
    CREATE USER aibot WITH PASSWORD 'postgres';
  END IF;
END
$$;

-- Даем пользователю необходимые привилегии
ALTER USER aibot WITH SUPERUSER;

-- Создаем базу данных aibot если не существует
SELECT 'CREATE DATABASE aibot OWNER aibot'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'aibot');

-- Подключаемся к базе данных aibot
\c aibot

-- Создаем расширение для UUID если не существует
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Настраиваем параметры для работы с UUID и JSON
ALTER DATABASE aibot SET timezone TO 'UTC';
