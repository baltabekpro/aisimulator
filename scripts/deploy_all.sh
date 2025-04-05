#!/bin/bash
# Полный скрипт развертывания AI Simulator
# Автоматически настраивает PostgreSQL, API сервер, Admin панель и Telegram Bot

set -e  # Прерывать выполнение при ошибках

# Проверка запуска от sudo
if [ "$EUID" -ne 0 ]; then
  echo "Этот скрипт требует привилегий root. Запустите с sudo."
  exit 1
fi

# Получаем имя пользователя, от которого запущен sudo
SUDO_USER_HOME=$(eval echo ~${SUDO_USER})
REAL_USER=${SUDO_USER}

# Директория установки
INSTALL_DIR="/opt/aibot"
LOG_FILE="/tmp/aibot_deploy.log"

# Функция логирования
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a $LOG_FILE
}

log "Начинаем установку AI Simulator в $INSTALL_DIR"

# Устанавливаем необходимые пакеты
log "Устанавливаем необходимые пакеты..."
apt update
apt install -y python3-pip python3-venv postgresql postgresql-contrib nginx
apt install -y build-essential libssl-dev libffi-dev python3-dev

# Настройка PostgreSQL
log "Настраиваем PostgreSQL..."
systemctl start postgresql
systemctl enable postgresql

# Определяем версию PostgreSQL
PG_VERSION=$(psql --version | grep -oE '[0-9]{1,2}' | head -1)
log "Обнаружена PostgreSQL версии $PG_VERSION"

# Создаем пользователя и базу данных
su -c "psql -c \"CREATE USER aibot WITH PASSWORD 'postgres';\"" postgres || log "Пользователь БД уже существует"
su -c "psql -c \"CREATE DATABASE aibot OWNER aibot;\"" postgres || log "База данных уже существует"
su -c "psql -c \"ALTER USER aibot WITH SUPERUSER;\"" postgres || log "Пользователь БД уже суперпользователь"

# Настраиваем pg_hba.conf для разрешения MD5 аутентификации
PG_HBA_PATH="/etc/postgresql/$PG_VERSION/main/pg_hba.conf"
if [ -f "$PG_HBA_PATH" ]; then
    log "Настраиваем доступ к PostgreSQL (MD5 аутентификация)..."
    cp $PG_HBA_PATH ${PG_HBA_PATH}.bak  # Бэкап оригинального файла
    
    # Заменяем методы аутентификации на md5
    sed -i '/^host.*all.*all.*127.0.0.1\/32/ s/peer\|ident\|scram-sha-256/md5/' $PG_HBA_PATH
    sed -i '/^host.*all.*all.*::1\/128/ s/peer\|ident\|scram-sha-256/md5/' $PG_HBA_PATH
    
    # Перезапускаем PostgreSQL
    systemctl restart postgresql
else
    log "ВНИМАНИЕ: Не найден файл конфигурации PostgreSQL. Возможно, требуется ручная настройка."
fi

# Создаем директорию установки
log "Создаем директорию установки..."
mkdir -p $INSTALL_DIR
cd $INSTALL_DIR

# Копируем файлы проекта (если они в текущей директории)
log "Копируем файлы проекта..."
if [ -d "/home/$REAL_USER/aibot" ]; then
    cp -r /home/$REAL_USER/aibot/* $INSTALL_DIR/
elif [ -d "$SUDO_USER_HOME/aibot" ]; then
    cp -r $SUDO_USER_HOME/aibot/* $INSTALL_DIR/
else
    log "ВНИМАНИЕ: Директория проекта не найдена. Пожалуйста, укажите путь к проекту:"
    read -p "Путь к файлам проекта: " PROJECT_PATH
    cp -r $PROJECT_PATH/* $INSTALL_DIR/
fi

# Устанавливаем правильные права на файлы
chown -R $REAL_USER:$REAL_USER $INSTALL_DIR

# Создаем и активируем виртуальное окружение
log "Создаем виртуальное окружение..."
su - $REAL_USER -c "cd $INSTALL_DIR && python3 -m venv venv"
VENV_ACTIVATE="$INSTALL_DIR/venv/bin/activate"

# Устанавливаем зависимости
log "Устанавливаем зависимости проекта..."
su - $REAL_USER -c "cd $INSTALL_DIR && source $VENV_ACTIVATE && pip install -r requirements.txt"
su - $REAL_USER -c "cd $INSTALL_DIR && source $VENV_ACTIVATE && pip install uvicorn gunicorn"

# Проверяем наличие .env файла
if [ ! -f "$INSTALL_DIR/.env" ]; then
    log "Создаем файл .env из файла-образца..."
    cp $INSTALL_DIR/.env.example $INSTALL_DIR/.env
    
    # Настраиваем подключение к БД в .env
    sed -i "s|DATABASE_URL=.*|DATABASE_URL='postgresql://aibot:postgres@localhost:5432/aibot?client_encoding=utf8'|g" $INSTALL_DIR/.env
    
    log "Файл .env создан. Пожалуйста, проверьте и отредактируйте настройки если необходимо."
else
    log "Файл .env уже существует, оставляем без изменений."
fi

# Инициализируем базу данных
log "Инициализируем базу данных..."
su - $REAL_USER -c "cd $INSTALL_DIR && source $VENV_ACTIVATE && python -m core.db.init_db"

# Применяем миграции
log "Применяем миграции..."
su - $REAL_USER -c "cd $INSTALL_DIR && source $VENV_ACTIVATE && python -m alembic upgrade head"

# Создаем systemd-сервисы
log "Создаем systemd-сервисы..."

# API сервис
cat > /etc/systemd/system/aibot-api.service << EOL
[Unit]
Description=AI Bot API Server
After=network.target postgresql.service

[Service]
User=$REAL_USER
Group=$REAL_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=5
EnvironmentFile=$INSTALL_DIR/.env

[Install]
WantedBy=multi-user.target
EOL

# Admin сервис
cat > /etc/systemd/system/aibot-admin.service << EOL
[Unit]
Description=AI Bot Admin Panel
After=network.target postgresql.service

[Service]
User=$REAL_USER
Group=$REAL_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/gunicorn -w 2 -b 0.0.0.0:5000 "admin_panel.app:app"
Restart=always
RestartSec=5
EnvironmentFile=$INSTALL_DIR/.env

[Install]
WantedBy=multi-user.target
EOL

# Telegram Bot сервис
cat > /etc/systemd/system/aibot-telegram.service << EOL
[Unit]
Description=AI Bot Telegram Bot
After=network.target postgresql.service aibot-api.service

[Service]
User=$REAL_USER
Group=$REAL_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python -m bots.bot
Restart=always
RestartSec=5
EnvironmentFile=$INSTALL_DIR/.env

[Install]
WantedBy=multi-user.target
EOL

# Перезагружаем systemd
log "Перезагружаем systemd..."
systemctl daemon-reload

# Запускаем сервисы
log "Запускаем сервисы..."
systemctl enable aibot-api.service
systemctl start aibot-api.service

systemctl enable aibot-admin.service
systemctl start aibot-admin.service

systemctl enable aibot-telegram.service
systemctl start aibot-telegram.service

# Настраиваем Nginx как обратный прокси (опционально)
log "Настраиваем Nginx как обратный прокси..."

# API конфигурация
cat > /etc/nginx/sites-available/aibot-api << EOL
server {
    listen 80;
    server_name api.localhost;  # Замените на ваш домен для API

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOL

# Admin конфигурация
cat > /etc/nginx/sites-available/aibot-admin << EOL
server {
    listen 80;
    server_name admin.localhost;  # Замените на ваш домен для Admin панели

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOL

# Активируем конфигурации Nginx
ln -sf /etc/nginx/sites-available/aibot-api /etc/nginx/sites-enabled/
ln -sf /etc/nginx/sites-available/aibot-admin /etc/nginx/sites-enabled/

# Проверяем конфигурацию Nginx и перезапускаем
nginx -t && systemctl restart nginx

# Финальное сообщение
log "Установка завершена!"
log "API работает на http://localhost:8000 (через Nginx: http://api.localhost)"
log "Admin панель работает на http://localhost:5000 (через Nginx: http://admin.localhost)"
log "Telegram Bot запущен в фоновом режиме"
log ""
log "Для проверки статуса сервисов:"
log "  systemctl status aibot-api.service"
log "  systemctl status aibot-admin.service"
log "  systemctl status aibot-telegram.service"
log ""
log "Для просмотра логов сервисов:"
log "  journalctl -u aibot-api.service -f"
log "  journalctl -u aibot-admin.service -f"
log "  journalctl -u aibot-telegram.service -f"
log ""
log "Для доступа к API через Nginx: http://api.localhost"
log "Для доступа к Admin панели через Nginx: http://admin.localhost"
log ""
log "Примечание: Если вы не планируете использовать Nginx или хотите использовать"
log "свои домены, отредактируйте конфигурации в /etc/nginx/sites-available/"
