#!/bin/bash
# Скрипт для быстрого развертывания AI Simulator через Docker на сервере Ubuntu

set -e  # Прерывать выполнение при ошибках

echo "[$(date +'%Y-%m-%d %H:%M:%S')] Начинаем установку AI Simulator через Docker..."

# Проверяем наличие Docker
if ! command -v docker &> /dev/null; then
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Docker не установлен. Устанавливаем Docker..."
    
    # Установка Docker
    sudo apt update
    sudo apt install -y apt-transport-https ca-certificates curl software-properties-common
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
    sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
    sudo apt update
    sudo apt install -y docker-ce docker-ce-cli containerd.io
    
    # Добавляем текущего пользователя в группу docker
    sudo usermod -aG docker $USER
    
    # Применяем изменения
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Docker установлен. Чтобы применить изменения группы, перезайдите в систему или выполните: newgrp docker"
else
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Docker уже установлен."
fi

# Проверяем наличие Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Docker Compose не установлен. Устанавливаем Docker Compose..."
    
    # Установка Docker Compose
    sudo curl -L "https://github.com/docker/compose/releases/download/v2.17.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Docker Compose установлен."
else
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Docker Compose уже установлен."
fi

# Устанавливаем Nginx, если нужен
read -p "Установить Nginx как обратный прокси? (y/n): " install_nginx
if [[ "$install_nginx" == "y" ]]; then
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Устанавливаем Nginx..."
    sudo apt update
    sudo apt install -y nginx
    
    # Создаем конфигурации
    read -p "Введите домен или IP для API (или оставьте пустым для локального доступа): " api_domain
    read -p "Введите домен или IP для Admin панели (или оставьте пустым для локального доступа): " admin_domain
    
    if [[ -n "$api_domain" ]]; then
        # Создаем конфигурацию для API
        cat > /tmp/aibot-api << EOL
server {
    listen 80;
    server_name ${api_domain};

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOL
        sudo mv /tmp/aibot-api /etc/nginx/sites-available/
        sudo ln -sf /etc/nginx/sites-available/aibot-api /etc/nginx/sites-enabled/
    fi
    
    if [[ -n "$admin_domain" ]]; then
        # Создаем конфигурацию для Admin панели
        cat > /tmp/aibot-admin << EOL
server {
    listen 80;
    server_name ${admin_domain};

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOL
        sudo mv /tmp/aibot-admin /etc/nginx/sites-available/
        sudo ln -sf /etc/nginx/sites-available/aibot-admin /etc/nginx/sites-enabled/
    fi
    
    # Проверяем и перезапускаем Nginx
    sudo nginx -t && sudo systemctl restart nginx
    
    # Настраиваем UFW (брандмауэр)
    read -p "Настроить брандмауэр UFW? (y/n): " setup_ufw
    if [[ "$setup_ufw" == "y" ]]; then
        sudo apt install -y ufw
        sudo ufw allow ssh
        sudo ufw allow http
        sudo ufw allow https
        
        if [[ -z "$api_domain" ]]; then
            sudo ufw allow 8000
        fi
        
        if [[ -z "$admin_domain" ]]; then
            sudo ufw allow 5000
        fi
        
        # Включаем UFW
        sudo ufw --force enable
    fi
    
    # Настраиваем SSL с Let's Encrypt
    read -p "Настроить SSL с Let's Encrypt? (y/n): " setup_ssl
    if [[ "$setup_ssl" == "y" ]]; then
        sudo apt install -y certbot python3-certbot-nginx
        
        domains=""
        if [[ -n "$api_domain" ]]; then
            domains="$domains -d $api_domain"
        fi
        
        if [[ -n "$admin_domain" ]]; then
            domains="$domains -d $admin_domain"
        fi
        
        if [[ -n "$domains" ]]; then
            sudo certbot --nginx $domains
        fi
    fi
fi

# Настраиваем .env файл
if [ ! -f .env ]; then
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Создаем файл .env из примера..."
    cp .env.example .env
    
    # Запрашиваем необходимые настройки
    read -p "Введите OPENROUTER_API_KEY: " openrouter_key
    read -p "Введите TELEGRAM_TOKEN: " telegram_token
    
    # Обновляем .env файл
    sed -i "s|OPENROUTER_API_KEY=.*|OPENROUTER_API_KEY=$openrouter_key|g" .env
    sed -i "s|TELEGRAM_TOKEN=.*|TELEGRAM_TOKEN=$telegram_token|g" .env
    sed -i "s|DATABASE_URL=.*|DATABASE_URL='postgresql://aibot:postgres@postgres:5432/aibot?client_encoding=utf8'|g" .env
    sed -i "s|API_BASE_URL=.*|API_BASE_URL=http://api:8000/api/v1|g" .env
    
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Файл .env создан."
else
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Файл .env уже существует."
fi

# Запускаем приложение через Docker Compose
echo "[$(date +'%Y-%m-%d %H:%M:%S')] Запускаем AI Simulator через Docker Compose..."
docker-compose up -d

# Проверяем, что все сервисы запущены
echo "[$(date +'%Y-%m-%d %H:%M:%S')] Проверяем статус контейнеров..."
docker-compose ps

echo "[$(date +'%Y-%m-%d %H:%M:%S')] Установка завершена!"
echo ""
echo "API доступен по адресу: http://localhost:8000"
echo "Admin панель доступна по адресу: http://localhost:5000"
echo "Telegram бот запущен в фоновом режиме"
echo ""
echo "Для просмотра логов API: docker-compose logs -f api"
echo "Для просмотра логов Admin: docker-compose logs -f admin"
echo "Для просмотра логов Telegram бота: docker-compose logs -f telegram"
echo ""
echo "Для остановки: docker-compose down"
