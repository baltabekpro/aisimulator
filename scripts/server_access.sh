#!/bin/bash
# Утилиты для быстрого доступа к компонентам AI Simulator на сервере
# Запускайте из директории проекта

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

function show_help {
    echo -e "${BLUE}=== AI Simulator - Утилиты сервера ===${NC}"
    echo "Использование: $0 [команда]"
    echo
    echo "Команды:"
    echo "  logs     - Просмотр логов (all, api, admin, telegram)"
    echo "  restart  - Перезапуск всех или указанного сервиса"
    echo "  status   - Проверка статуса всех сервисов"
    echo "  update   - Обновление проекта из репозитория и перезапуск"
    echo "  backup   - Создание резервной копии данных PostgreSQL"
    echo "  restore  - Восстановление из резервной копии"
    echo "  shell    - Запуск оболочки в контейнере"
    echo
    echo "Примеры:"
    echo "  $0 logs api        - Показать логи API сервера"
    echo "  $0 restart admin   - Перезапустить админ-панель"
    echo "  $0 update          - Обновить код и перезапустить все сервисы"
    echo "  $0 shell telegram  - Запустить оболочку в контейнере Telegram бота"
}

function check_docker {
    if ! command -v docker &> /dev/null || ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}Ошибка: Docker и/или Docker Compose не установлены${NC}"
        echo "Установите их с помощью скрипта quick_deploy.sh"
        exit 1
    fi
}

function view_logs {
    service="$1"
    if [ "$service" == "all" ] || [ -z "$service" ]; then
        echo -e "${GREEN}Просмотр логов всех сервисов (Ctrl+C для выхода)...${NC}"
        docker-compose logs -f
    else
        if docker-compose ps | grep -q "$service"; then
            echo -e "${GREEN}Просмотр логов $service (Ctrl+C для выхода)...${NC}"
            docker-compose logs -f "$service"
        else
            echo -e "${RED}Ошибка: Сервис $service не найден${NC}"
            echo "Доступные сервисы: api, admin, telegram, postgres"
        fi
    fi
}

function restart_service {
    service="$1"
    if [ "$service" == "all" ] || [ -z "$service" ]; then
        echo -e "${GREEN}Перезапуск всех сервисов...${NC}"
        docker-compose restart
    else
        if docker-compose ps | grep -q "$service"; then
            echo -e "${GREEN}Перезапуск $service...${NC}"
            docker-compose restart "$service"
        else
            echo -e "${RED}Ошибка: Сервис $service не найден${NC}"
            echo "Доступные сервисы: api, admin, telegram, postgres"
        fi
    fi
}

function check_status {
    echo -e "${GREEN}Статус контейнеров:${NC}"
    docker-compose ps
    
    echo -e "\n${GREEN}Использование ресурсов:${NC}"
    docker stats --no-stream $(docker-compose ps -q)
}

function update_system {
    echo -e "${GREEN}Обновление кода из репозитория...${NC}"
    git pull
    
    echo -e "${GREEN}Пересборка Docker-образов...${NC}"
    docker-compose build
    
    echo -e "${GREEN}Перезапуск обновленных контейнеров...${NC}"
    docker-compose up -d
    
    echo -e "${GREEN}Обновление завершено!${NC}"
}

function create_backup {
    BACKUP_FILE="aibot_backup_$(date +%Y%m%d_%H%M%S).sql"
    echo -e "${GREEN}Создание резервной копии базы данных в $BACKUP_FILE...${NC}"
    docker-compose exec postgres pg_dump -U aibot aibot > $BACKUP_FILE
    
    if [ -f "$BACKUP_FILE" ]; then
        echo -e "${GREEN}Резервная копия успешно создана: $BACKUP_FILE${NC}"
        echo "Размер: $(du -h $BACKUP_FILE | cut -f1)"
    else
        echo -e "${RED}Ошибка при создании резервной копии${NC}"
    fi
}

function restore_backup {
    if [ -z "$1" ]; then
        echo -e "${RED}Ошибка: Укажите файл резервной копии${NC}"
        echo "Пример: $0 restore aibot_backup_20240420_120000.sql"
        return 1
    fi
    
    BACKUP_FILE="$1"
    if [ ! -f "$BACKUP_FILE" ]; then
        echo -e "${RED}Ошибка: Файл $BACKUP_FILE не найден${NC}"
        return 1
    fi
    
    echo -e "${YELLOW}ВНИМАНИЕ: Это действие перезапишет текущую базу данных!${NC}"
    read -p "Продолжить? (y/n): " confirm
    if [ "$confirm" != "y" ]; then
        echo "Отмена восстановления"
        return 0
    fi
    
    echo -e "${GREEN}Восстановление из резервной копии $BACKUP_FILE...${NC}"
    cat $BACKUP_FILE | docker-compose exec -T postgres psql -U aibot aibot
    
    echo -e "${GREEN}Восстановление завершено!${NC}"
}

function run_shell {
    service="$1"
    if [ -z "$service" ]; then
        echo -e "${RED}Ошибка: Укажите сервис (api, admin, telegram, postgres)${NC}"
        return 1
    fi
    
    if docker-compose ps | grep -q "$service"; then
        echo -e "${GREEN}Запуск оболочки в контейнере $service...${NC}"
        if [ "$service" == "postgres" ]; then
            docker-compose exec $service bash -c "psql -U aibot aibot"
        else
            docker-compose exec $service bash
        fi
    else
        echo -e "${RED}Ошибка: Сервис $service не найден${NC}"
        echo "Доступные сервисы: api, admin, telegram, postgres"
    fi
}

# Проверка наличия Docker
check_docker

# Обработка команд
case "$1" in
    logs)
        view_logs "$2"
        ;;
    restart)
        restart_service "$2"
        ;;
    status)
        check_status
        ;;
    update)
        update_system
        ;;
    backup)
        create_backup
        ;;
    restore)
        restore_backup "$2"
        ;;
    shell)
        run_shell "$2"
        ;;
    *)
        show_help
        ;;
esac
