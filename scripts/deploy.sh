#!/bin/bash
# Скрипт для развертывания AI Simulator на сервере

# Проверяем наличие необходимых команд
command -v python3 >/dev/null 2>&1 || { echo "Python3 не установлен. Установите его и попробуйте снова."; exit 1; }
command -v psql >/dev/null 2>&1 || { echo "PostgreSQL не установлен. Установите его и попробуйте снова."; exit 1; }

# Директория установки
INSTALL_DIR="/opt/aibot"
echo "Устанавливаем AI Simulator в $INSTALL_DIR"

# Создаем директорию если она не существует
mkdir -p $INSTALL_DIR
cp -r ./* $INSTALL_DIR/
cd $INSTALL_DIR

# Создаем виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# Устанавливаем зависимости
pip install -r requirements.txt
pip install uvicorn gunicorn

# Проверяем и настраиваем .env файл
if [ ! -f .env ]; then
    echo "Создаем .env файл из примера..."
    cp .env.example .env
    echo "Настройте параметры в файле .env"
    exit 1
fi

# Настройка PostgreSQL
echo "Настраиваем базу данных..."
DB_NAME="aibot"
DB_USER="aibot"
DB_PASS="postgres"

# Предполагаем, что у нас есть права на создание БД
sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';" || true
sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" || true
sudo -u postgres psql -c "ALTER USER $DB_USER WITH SUPERUSER;" || true

# Инициализируем базу данных
echo "Инициализируем базу данных..."
python -m core.db.init_db
python -m alembic upgrade head

# Создаем systemd-сервисы
echo "Создаем systemd-сервисы..."

# API сервис
cat > /tmp/aibot-api.service << EOL
[Unit]
Description=AI Bot API Server
After=network.target postgresql.service

[Service]
User=$(whoami)
Group=$(whoami)
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=5
Environment="PATH=$INSTALL_DIR/venv/bin"
EnvironmentFile=$INSTALL_DIR/.env

[Install]
WantedBy=multi-user.target
EOL

# Admin сервис
cat > /tmp/aibot-admin.service << EOL
[Unit]
Description=AI Bot Admin Panel
After=network.target postgresql.service

[Service]
User=$(whoami)
Group=$(whoami)
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 "admin_panel.app:app"
Restart=always
RestartSec=5
Environment="PATH=$INSTALL_DIR/venv/bin"
EnvironmentFile=$INSTALL_DIR/.env

[Install]
WantedBy=multi-user.target
EOL

# Telegram Bot сервис
cat > /tmp/aibot-telegram.service << EOL
[Unit]
Description=AI Bot Telegram Bot
After=network.target postgresql.service aibot-api.service

[Service]
User=$(whoami)
Group=$(whoami)
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python -m bots.bot
Restart=always
RestartSec=5
Environment="PATH=$INSTALL_DIR/venv/bin"
EnvironmentFile=$INSTALL_DIR/.env

[Install]
WantedBy=multi-user.target
EOL

# Копируем в systemd
sudo mv /tmp/aibot-api.service /etc/systemd/system/
sudo mv /tmp/aibot-admin.service /etc/systemd/system/
sudo mv /tmp/aibot-telegram.service /etc/systemd/system/

# Перезагружаем systemd
sudo systemctl daemon-reload

# Запускаем сервисы
echo "Запускаем сервисы..."
sudo systemctl enable aibot-api.service
sudo systemctl start aibot-api.service

sudo systemctl enable aibot-admin.service
sudo systemctl start aibot-admin.service

sudo systemctl enable aibot-telegram.service
sudo systemctl start aibot-telegram.service

echo "Установка завершена!"
echo "API сервер работает на порту 8000"
echo "Админ-панель работает на порту 5000"
echo "Telegram Bot работает в фоновом режиме"
echo ""
echo "Проверьте логи с помощью:"
echo "  sudo journalctl -u aibot-api.service -f"
echo "  sudo journalctl -u aibot-admin.service -f"
echo "  sudo journalctl -u aibot-telegram.service -f"
