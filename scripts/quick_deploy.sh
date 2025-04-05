#!/bin/bash
# Быстрое развертывание AI Simulator на новом сервере Ubuntu
# Запускайте с sudo: sudo bash quick_deploy.sh

set -e  # Остановка при любой ошибке

echo "=== Быстрое развертывание AI Simulator ==="
echo "Этот скрипт настроит сервер и запустит AI Simulator"
echo

# Создаем директорию установки
INSTALL_DIR="/opt/aibot"
mkdir -p $INSTALL_DIR

# 1. Установка Docker
echo "[+] Установка Docker..."
curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh
usermod -aG docker $USER

# 2. Установка Docker Compose
echo "[+] Установка Docker Compose..."
curl -L "https://github.com/docker/compose/releases/download/v2.17.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# 3. Копирование файлов проекта
echo "[+] Копирование файлов проекта..."
cp -r $(dirname "$0")/../* $INSTALL_DIR/
cd $INSTALL_DIR

# 4. Настройка брандмауэра
echo "[+] Настройка брандмауэра..."
apt install -y ufw
ufw allow ssh
ufw allow 8000  # API
ufw allow 5000  # Admin
ufw --force enable

# 5. Запуск Docker контейнеров
echo "[+] Запуск AI Simulator через Docker..."
docker-compose up -d

echo
echo "=== Установка завершена! ==="
echo "API доступен по адресу: http://YOUR_SERVER_IP:8000"
echo "Admin панель доступна по адресу: http://YOUR_SERVER_IP:5000"
echo "Telegram бот запущен в фоновом режиме"
echo
echo "Для просмотра логов: docker-compose logs -f"
echo "Для управления: cd $INSTALL_DIR && docker-compose [command]"
