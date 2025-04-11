#!/bin/bash
# Скрипт для запуска проекта с автоматическим применением всех необходимых исправлений
# Запускать из корневой директории проекта

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Запуск AI-симулятора с автоматическими исправлениями ===${NC}"

# Проверка, запущен ли Docker
if ! docker info > /dev/null 2>&1; then
  echo -e "${RED}Docker не запущен. Пожалуйста, запустите Docker и повторите попытку.${NC}"
  exit 1
fi

# Остановка всех существующих контейнеров проекта
echo -e "${YELLOW}Останавливаем существующие контейнеры...${NC}"
docker-compose down

# Сборка и запуск новых контейнеров
echo -e "${YELLOW}Запускаем проект с применением всех необходимых исправлений...${NC}"
docker-compose up --build -d

echo -e "${GREEN}=== Все контейнеры успешно запущены ===${NC}"
echo -e "${YELLOW}Проверка статуса контейнеров:${NC}"
docker-compose ps

echo -e "\n${GREEN}Сервисы доступны по следующим URL:${NC}"
echo -e "- API: http://localhost:8000"
echo -e "- Админ-панель: http://localhost:5000"

echo -e "\n${YELLOW}Для просмотра логов используйте команду:${NC}"
echo -e "docker-compose logs -f [postgres|db-init|api|admin|telegram]"

echo -e "\n${GREEN}Готово!${NC}"