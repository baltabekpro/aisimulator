# Скрипт для запуска проекта с автоматическим применением всех необходимых исправлений
# Запускать из корневой директории проекта (PowerShell)

# Цвета для вывода
$Green = "Green"
$Yellow = "Yellow"
$Red = "Red"
$White = "White"

Write-Host "=== Запуск AI-симулятора с автоматическими исправлениями ===" -ForegroundColor $Green

# Проверка, запущен ли Docker
try {
    docker info | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker не запущен"
    }
} catch {
    Write-Host "Docker не запущен. Пожалуйста, запустите Docker Desktop и повторите попытку." -ForegroundColor $Red
    exit 1
}

# Остановка всех существующих контейнеров проекта
Write-Host "Останавливаем существующие контейнеры..." -ForegroundColor $Yellow
docker-compose down

# Сборка и запуск новых контейнеров
Write-Host "Запускаем проект с применением всех необходимых исправлений..." -ForegroundColor $Yellow
docker-compose up --build -d

Write-Host "=== Все контейнеры успешно запущены ===" -ForegroundColor $Green
Write-Host "Проверка статуса контейнеров:" -ForegroundColor $Yellow
docker-compose ps

Write-Host ""
Write-Host "Сервисы доступны по следующим URL:" -ForegroundColor $Green
Write-Host "- API: http://localhost:8000" -ForegroundColor $White
Write-Host "- Админ-панель: http://localhost:5000" -ForegroundColor $White

Write-Host ""
Write-Host "Для просмотра логов используйте команду:" -ForegroundColor $Yellow
Write-Host "docker-compose logs -f [postgres|db-init|api|admin|telegram]" -ForegroundColor $White

Write-Host ""
Write-Host "Готово!" -ForegroundColor $Green