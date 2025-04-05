#!/bin/bash
# Скрипт быстрого запуска AI Simulator через Docker

# Проверяем наличие Docker и Docker Compose
command -v docker >/dev/null 2>&1 || { echo "Docker не установлен. Установите его и попробуйте снова."; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "Docker Compose не установлен. Установите его и попробуйте снова."; exit 1; }

echo "[$(date +'%Y-%m-%d %H:%M:%S')] Запускаем AI Simulator через Docker..."

# Проверяем наличие .env файла
if [ ! -f .env ]; then
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Создаем файл .env из образца..."
    cp .env.example .env
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Файл .env создан. Пожалуйста, проверьте и настройте его при необходимости."
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Обратите особое внимание на настройку OPENROUTER_API_KEY и TELEGRAM_TOKEN."
fi

# Запускаем через Docker Compose
echo "[$(date +'%Y-%m-%d %H:%M:%S')] Запускаем контейнеры..."
docker-compose up -d

# Проверяем, что все контейнеры запущены
echo "[$(date +'%Y-%m-%d %H:%M:%S')] Проверяем статус контейнеров..."
docker-compose ps

echo "[$(date +'%Y-%m-%d %H:%M:%S')] AI Simulator успешно запущен!"
echo "API доступен по адресу: http://localhost:8000"
echo "Admin панель доступна по адресу: http://localhost:5000"
echo "Telegram бот запущен в фоновом режиме"
echo ""
echo "Для просмотра логов:"
echo "  docker-compose logs -f api    # Логи API сервера"
echo "  docker-compose logs -f admin  # Логи Admin панели"
echo "  docker-compose logs -f telegram # Логи Telegram бота"
echo ""
echo "Для остановки: docker-compose down"
