# Быстрый запуск AI Simulator на сервере

Если у вас уже есть настроенный проект AI Simulator, вот как быстро запустить его на новом сервере Ubuntu.

## Предварительные требования

- Сервер Ubuntu 20.04 или новее
- Права sudo для установки программ

## Быстрая установка (5 минут)

### 1. Установка Docker и Docker Compose

```bash
# Установка Docker в одну команду
curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh

# Добавление пользователя в группу docker
sudo usermod -aG docker $USER
newgrp docker

# Установка Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.17.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 2. Клонирование и запуск проекта

```bash
# Клонирование репозитория
git clone https://your-repository.git /opt/aibot

# Переход в директорию проекта
cd /opt/aibot

# Запуск через Docker Compose
docker-compose up -d
```

### 3. Проверка статуса

```bash
# Проверка статуса контейнеров
docker-compose ps

# Проверка логов
docker-compose logs
```

## Доступ к сервисам

После запуска вы можете получить доступ к сервисам по следующим URL:

- **API сервер**: http://ваш_ip:8000
- **Админ-панель**: http://ваш_ip:5000
- **Telegram бот**: автоматически запускается и работает в фоновом режиме

## Настройка доменов (опционально)

Если у вас есть домен и вы хотите настроить доступ через него:

```bash
# Установка Nginx
sudo apt install -y nginx

# Генерация конфигурации Nginx
sudo bash -c 'cat > /etc/nginx/sites-available/aibot << EOL
server {
    listen 80;
    server_name api.ваш-домен.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}

server {
    listen 80;
    server_name admin.ваш-домен.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOL'

# Активация конфигурации
sudo ln -sf /etc/nginx/sites-available/aibot /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl restart nginx

# SSL сертификат (опционально)
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d api.ваш-домен.com -d admin.ваш-домен.com
```

## Часто используемые команды

```bash
# Посмотреть логи определенного сервиса
docker-compose logs -f api    # API сервер
docker-compose logs -f admin  # Админ-панель
docker-compose logs -f telegram  # Telegram бот

# Перезапустить все сервисы
docker-compose restart

# Остановить все сервисы
docker-compose down

# Обновить и перезапустить (при обновлении кода)
git pull
docker-compose build  # пересборка образов
docker-compose up -d  # запуск обновленных контейнеров
```

## Проверка доступности

Чтобы убедиться, что API сервер работает и доступен извне, выполните:

```bash
curl http://localhost:8000/api/v1/health
```

Вы должны получить ответ с информацией о состоянии сервера.
