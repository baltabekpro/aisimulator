# Автоматический скрипт для развертывания AI Simulator на Windows
# PowerShell скрипт для настройки и запуска AI Simulator на Windows

# Функция для вывода сообщений с временной меткой
function Log {
    param (
        [string]$Message
    )
    Write-Host "[$([DateTime]::Now.ToString('yyyy-MM-dd HH:mm:ss'))] $Message"
}

# Проверка запуска от администратора
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
if (-not $isAdmin) {
    Log "Этот скрипт требует привилегий администратора. Пожалуйста, запустите PowerShell от имени администратора."
    exit 1
}

# Параметры установки
$installDir = "C:\aibot"
$logFile = "C:\temp\aibot_deploy.log"
$pgVersion = "14"  # Версия PostgreSQL для установки
$pgUser = "aibot"
$pgPassword = "postgres"
$pgDatabase = "aibot"

# Создаем директорию для логов
if (-not (Test-Path "C:\temp")) {
    New-Item -ItemType Directory -Path "C:\temp" | Out-Null
}

# Начинаем установку
Log "Начинаем установку AI Simulator в $installDir" | Tee-Object -FilePath $logFile -Append

# Проверяем наличие chocolatey
Log "Проверяем наличие Chocolatey..." | Tee-Object -FilePath $logFile -Append
if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
    Log "Устанавливаем Chocolatey..." | Tee-Object -FilePath $logFile -Append
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
}

# Устанавливаем необходимые пакеты с помощью Chocolatey
Log "Устанавливаем необходимые пакеты..." | Tee-Object -FilePath $logFile -Append
choco install -y python --version=3.9.0
choco install -y postgresql$pgVersion
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine")

# Создаем директорию установки, если она не существует
if (-not (Test-Path $installDir)) {
    Log "Создаем директорию установки..." | Tee-Object -FilePath $logFile -Append
    New-Item -ItemType Directory -Path $installDir | Out-Null
}

# Копируем файлы проекта
Log "Копируем файлы проекта..." | Tee-Object -FilePath $logFile -Append
Copy-Item -Path "C:\Users\workb\aibot\*" -Destination $installDir -Recurse -Force
Set-Location $installDir

# Создаем и активируем виртуальное окружение
Log "Создаем виртуальное окружение..." | Tee-Object -FilePath $logFile -Append
& python -m venv venv
$venvActivate = "$installDir\venv\Scripts\Activate.ps1"
. $venvActivate

# Устанавливаем зависимости
Log "Устанавливаем зависимости проекта..." | Tee-Object -FilePath $logFile -Append
& pip install -r requirements.txt
& pip install uvicorn gunicorn psycopg2-binary

# Проверяем наличие .env файла
if (-not (Test-Path "$installDir\.env")) {
    Log "Создаем файл .env из файла-образца..." | Tee-Object -FilePath $logFile -Append
    Copy-Item "$installDir\.env.example" "$installDir\.env"
    
    # Настраиваем подключение к БД в .env
    $envContent = Get-Content "$installDir\.env" -Raw
    $envContent = $envContent -replace "DATABASE_URL=.*", "DATABASE_URL='postgresql://$pgUser`:$pgPassword@localhost:5432/$pgDatabase?client_encoding=utf8'"
    $envContent | Set-Content "$installDir\.env"
    
    Log "Файл .env создан. Пожалуйста, проверьте и отредактируйте настройки если необходимо."
}
else {
    Log "Файл .env уже существует, оставляем без изменений."
}

# Настройка PostgreSQL
Log "Настраиваем PostgreSQL..." | Tee-Object -FilePath $logFile -Append

# Перезапускаем службу PostgreSQL
Log "Перезапускаем службу PostgreSQL..." | Tee-Object -FilePath $logFile -Append
Restart-Service postgresql-x64-$pgVersion

Log "Создаем пользователя и базу данных в PostgreSQL..." | Tee-Object -FilePath $logFile -Append
$pgPath = "C:\Program Files\PostgreSQL\$pgVersion\bin"
$env:Path += ";$pgPath"

# Настройка PostgreSQL через psql
$pgSetup = @"
CREATE USER $pgUser WITH PASSWORD '$pgPassword';
CREATE DATABASE $pgDatabase OWNER $pgUser;
ALTER USER $pgUser WITH SUPERUSER;
"@

$pgSetup | Set-Content "C:\temp\pg_setup.sql"

try {
    # Выполняем SQL скрипт
    $env:PGPASSWORD = "postgres"  # Пароль пользователя postgres по умолчанию
    & psql -U postgres -f "C:\temp\pg_setup.sql"
}
catch {
    Log "Ошибка при настройке PostgreSQL: $_" | Tee-Object -FilePath $logFile -Append
    Log "Проверьте, запущен ли сервер PostgreSQL и правильно ли установлен пароль." | Tee-Object -FilePath $logFile -Append
}

# Инициализируем базу данных
Log "Инициализируем базу данных..." | Tee-Object -FilePath $logFile -Append
& python -m core.db.init_db

# Применяем миграции
Log "Применяем миграции..." | Tee-Object -FilePath $logFile -Append
& python -m alembic upgrade head

# Создаем .bat файлы для запуска сервисов
Log "Создаем скрипты запуска..." | Tee-Object -FilePath $logFile -Append

# API сервер
@"
@echo off
cd $installDir
call venv\Scripts\activate.bat
uvicorn app.main:app --host 0.0.0.0 --port 8000
"@ | Set-Content "$installDir\start_api.bat"

# Admin панель
@"
@echo off
cd $installDir
call venv\Scripts\activate.bat
python -m admin_panel.app
"@ | Set-Content "$installDir\start_admin.bat"

# Telegram Bot
@"
@echo off
cd $installDir
call venv\Scripts\activate.bat
python -m bots.bot
"@ | Set-Content "$installDir\start_telegram_bot.bat"

# Создаем ярлыки на рабочем столе
Log "Создаем ярлыки на рабочем столе..." | Tee-Object -FilePath $logFile -Append
$desktopPath = [Environment]::GetFolderPath("Desktop")

$WshShell = New-Object -ComObject WScript.Shell

# Ярлык для API сервера
$Shortcut = $WshShell.CreateShortcut("$desktopPath\AI Bot API Server.lnk")
$Shortcut.TargetPath = "$installDir\start_api.bat"
$Shortcut.WorkingDirectory = "$installDir"
$Shortcut.Description = "Запуск API сервера AI Bot"
$Shortcut.Save()

# Ярлык для Admin панели
$Shortcut = $WshShell.CreateShortcut("$desktopPath\AI Bot Admin Panel.lnk")
$Shortcut.TargetPath = "$installDir\start_admin.bat"
$Shortcut.WorkingDirectory = "$installDir"
$Shortcut.Description = "Запуск Admin панели AI Bot"
$Shortcut.Save()

# Ярлык для Telegram бота
$Shortcut = $WshShell.CreateShortcut("$desktopPath\AI Bot Telegram Bot.lnk")
$Shortcut.TargetPath = "$installDir\start_telegram_bot.bat"
$Shortcut.WorkingDirectory = "$installDir"
$Shortcut.Description = "Запуск Telegram бота AI Bot"
$Shortcut.Save()

# Создаем файлы регистрации служб Windows
Log "Создаем файлы регистрации служб Windows (опционально)..." | Tee-Object -FilePath $logFile -Append

# Устанавливаем nssm (Non-Sucking Service Manager)
choco install -y nssm

# Скрипт для регистрации служб с помощью nssm
@"
@echo off
echo Регистрация служб AI Bot...

:: API Сервер
nssm install AIBotAPI "$installDir\venv\Scripts\python.exe" "$installDir\venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000"
nssm set AIBotAPI AppDirectory "$installDir"
nssm set AIBotAPI DisplayName "AI Bot API Server"
nssm set AIBotAPI Description "API сервер AI Bot"
nssm set AIBotAPI Start SERVICE_AUTO_START

:: Admin Панель
nssm install AIBotAdmin "$installDir\venv\Scripts\python.exe" "-m admin_panel.app"
nssm set AIBotAdmin AppDirectory "$installDir"
nssm set AIBotAdmin DisplayName "AI Bot Admin Panel"
nssm set AIBotAdmin Description "Панель администратора AI Bot"
nssm set AIBotAdmin Start SERVICE_AUTO_START

:: Telegram Bot
nssm install AIBotTelegram "$installDir\venv\Scripts\python.exe" "-m bots.bot"
nssm set AIBotTelegram AppDirectory "$installDir"
nssm set AIBotTelegram DisplayName "AI Bot Telegram Bot"
nssm set AIBotTelegram Description "Telegram бот AI Bot"
nssm set AIBotTelegram Start SERVICE_AUTO_START

echo Службы зарегистрированы. Запустите службы в диспетчере служб Windows.
pause
"@ | Set-Content "$installDir\register_services.bat"

# Финальное сообщение
Log "Установка завершена!" | Tee-Object -FilePath $logFile -Append
Log "Для запуска компонентов системы используйте ярлыки на рабочем столе:" | Tee-Object -FilePath $logFile -Append
Log "  - AI Bot API Server" | Tee-Object -FilePath $logFile -Append
Log "  - AI Bot Admin Panel" | Tee-Object -FilePath $logFile -Append
Log "  - AI Bot Telegram Bot" | Tee-Object -FilePath $logFile -Append
Log "" | Tee-Object -FilePath $logFile -Append
Log "Также вы можете зарегистрировать компоненты как службы Windows, запустив:" | Tee-Object -FilePath $logFile -Append
Log "  $installDir\register_services.bat (от имени администратора)" | Tee-Object -FilePath $logFile -Append
Log "" | Tee-Object -FilePath $logFile -Append
Log "API доступен по адресу: http://localhost:8000" | Tee-Object -FilePath $logFile -Append
Log "Admin панель доступна по адресу: http://localhost:5000" | Tee-Object -FilePath $logFile -Append
Log "Telegram Bot запущен в фоновом режиме" | Tee-Object -FilePath $logFile -Append
