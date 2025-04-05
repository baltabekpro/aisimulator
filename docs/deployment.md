# Руководство по Развертыванию AI Simulator на Сервере

## Системные Требования

- Python 3.9+ 
- PostgreSQL 13+
- 2GB RAM минимум (рекомендуется 4GB+)
- 10GB свободного места на диске

## 1. Установка Необходимых Пакетов

### Ubuntu/Debian

```bash
# Обновим пакеты и установим необходимые зависимости
sudo apt update
sudo apt install -y python3-pip python3-venv postgresql postgresql-contrib

# Установим инструменты для работы с Python
sudo apt install -y build-essential libssl-dev libffi-dev python3-dev
```

### CentOS/RHEL

```bash
# Обновим пакеты и установим необходимые зависимости
sudo yum update -y
sudo yum install -y python3-pip postgresql-server postgresql-contrib

# Инициализируем базу данных PostgreSQL
sudo postgresql-setup --initdb --unit postgresql
```

## 2. Настройка PostgreSQL

```bash
# Запустим PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Создадим пользователя и базу данных
sudo -u postgres psql -c "CREATE USER aibot WITH PASSWORD 'postgres';"
sudo -u postgres psql -c "CREATE DATABASE aibot OWNER aibot;"
sudo -u postgres psql -c "ALTER USER aibot WITH SUPERUSER;"
```

Настройка доступа к PostgreSQL (изменим метод аутентификации):

```bash
# Откроем файл конфигурации
sudo nano /etc/postgresql/13/main/pg_hba.conf
```

Найдем строки для local connections и изменим их на:

