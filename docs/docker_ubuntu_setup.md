# Установка Docker и запуск AI Simulator на Ubuntu-сервере

Это руководство поможет вам установить Docker на сервер Ubuntu и настроить AI Simulator для доступа извне.

## 1. Установка Docker на Ubuntu

```bash
# Обновление пакетов
sudo apt update
sudo apt upgrade -y

# Установка необходимых пакетов
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common

# Добавление официального GPG-ключа Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -

# Добавление репозитория Docker
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"

# Обновление списка пакетов
sudo apt update

# Установка Docker
sudo apt install -y docker-ce docker-ce-cli containerd.io

# Проверка установки Docker
sudo docker --version

# Добавление текущего пользователя в группу docker (чтобы запускать docker без sudo)
sudo usermod -aG docker $USER

# Применение изменений (требуется перелогиниться)
# Перезагрузите сервер или выполните следующую команду:
newgrp docker
```

## 2. Установка Docker Compose

```bash
# Установка Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.17.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# Установка прав на выполнение
sudo chmod +x /usr/local/bin/docker-compose

# Проверка установки Docker Compose
docker-compose --version
```

## 3. Клонирование репозитория AI Simulator

```bash
# Клонирование репозитория
git clone <URL_репозитория> /opt/aibot

# Переход в директорию проекта
cd /opt/aibot
```

## 4. Настройка .env файла

```bash
# Создание файла .env из примера
cp .env.example .env

# Редактирование файла .env
nano .env
```

Убедитесь, что в файле .env настроены все необходимые параметры:
- `DATABASE_URL` (будет автоматически переопределен в docker-compose)
- `OPENROUTER_API_KEY` для AI функциональности
- `TELEGRAM_TOKEN` для Telegram бота
- Другие параметры по необходимости

## 5. Настройка Docker Compose для внешнего доступа

Создайте файл `docker-compose.yml` (или используйте существующий):

```yaml
version: '3.8'

services:
  # База данных PostgreSQL
  postgres:
    image: postgres:13
    container_name: aibot-postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_USER=aibot
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=aibot
    restart: unless-stopped

  # API сервер (FastAPI + Uvicorn)
  api:
    build:
      context: .
      dockerfile: Dockerfile.api
    container_name: aibot-api
    depends_on:
      - postgres
    volumes:
      - ./:/app
    env_file:
      - .env
    environment:
      - DATABASE_URL=postgresql://aibot:postgres@postgres:5432/aibot?client_encoding=utf8
    ports:
      - "8000:8000"  # Меняем на ваш внешний порт, если нужно
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000
    restart: unless-stopped

  # Admin панель (Flask + Gunicorn)
  admin:
    build:
      context: .
      dockerfile: Dockerfile.admin
    container_name: aibot-admin
    depends_on:
      - postgres
      - api
    volumes:
      - ./:/app
    env_file:
      - .env
    environment:
      - DATABASE_URL=postgresql://aibot:postgres@postgres:5432/aibot?client_encoding=utf8
      - API_BASE_URL=http://api:8000/api/v1
    ports:
      - "5000:5000"  # Меняем на ваш внешний порт, если нужно
    command: gunicorn -w 2 -b 0.0.0.0:5000 "admin_panel.app:app"
    restart: unless-stopped

  # Telegram бот
  telegram:
    build:
      context: .
      dockerfile: Dockerfile.bot
    container_name: aibot-telegram
    depends_on:
      - postgres
      - api
    volumes:
      - ./:/app
    env_file:
      - .env
    environment:
      - DATABASE_URL=postgresql://aibot:postgres@postgres:5432/aibot?client_encoding=utf8
      - API_BASE_URL=http://api:8000/api/v1
    restart: unless-stopped

volumes:
  postgres_data:
```

## 6. Создание Dockerfile для компонентов (если их еще нет)

### Dockerfile.api

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install uvicorn gunicorn

# Копирование исходного кода
COPY . .

# Команда запуска
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Dockerfile.admin

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn

# Копирование исходного кода
COPY . .

# Команда запуска
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "admin_panel.app:app"]
```

### Dockerfile.bot

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY . .

# Команда запуска
CMD ["python", "-m", "bots.bot"]
```

## 7. Запуск приложения

```bash
# Запуск всех сервисов в фоновом режиме
docker-compose up -d

# Проверка статуса контейнеров
docker-compose ps

# Просмотр логов API сервера
docker-compose logs -f api

# Просмотр логов Admin панели
docker-compose logs -f admin

# Просмотр логов Telegram бота
docker-compose logs -f telegram
```

## 8. Настройка Nginx для доступа из внешней сети (опционально)

Если вы хотите настроить красивые URL и SSL, рекомендуется использовать Nginx как обратный прокси:

```bash
# Установка Nginx
sudo apt install -y nginx

# Создание конфигурации для API
sudo nano /etc/nginx/sites-available/aibot-api
```

Содержимое файла конфигурации Nginx для API:
