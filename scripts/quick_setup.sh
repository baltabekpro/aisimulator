#!/bin/bash
# Быстрая установка Docker и запуск AI Simulator на Ubuntu

echo "=== Быстрая установка AI Simulator на Ubuntu ==="
echo "Этот скрипт установит Docker и запустит AI Simulator"

# 1. Установка Docker и Docker Compose
echo "[+] Установка Docker и Docker Compose..."
sudo apt update
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io
sudo curl -L "https://github.com/docker/compose/releases/download/v2.17.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
sudo usermod -aG docker $USER

# 2. Открытие портов (необходимо для внешнего доступа)
echo "[+] Настройка брандмауэра..."
sudo apt install -y ufw
sudo ufw allow ssh
sudo ufw allow 8000  # API
sudo ufw allow 5000  # Admin
sudo ufw --force enable

# 3. Запуск Docker контейнеров
echo "[+] Запуск AI Simulator через Docker..."
docker-compose up -d

echo "=== Установка завершена! ==="
echo "API доступен по адресу: http://YOUR_SERVER_IP:8000"
echo "Admin панель доступна по адресу: http://YOUR_SERVER_IP:5000"
echo "Telegram бот запущен в фоновом режиме"
echo
echo "Для просмотра логов:"
echo "  docker-compose logs -f api     # Логи API"
echo "  docker-compose logs -f admin   # Логи Admin панели"
echo "  docker-compose logs -f telegram # Логи Telegram бота"
echo
echo "ВНИМАНИЕ: Для применения изменений в группе docker перезайдите в систему"
echo "или выполните команду: newgrp docker"
