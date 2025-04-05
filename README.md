# AI Simulator

A simulator for AI character interactions.

## Setup

1. Create a virtual environment:
   ```
   python -m venv venv
   ```

2. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Unix/MacOS: `source venv/bin/activate`

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up environment variables in a `.env` file (copy from `.env.example`).

5. Initialize the database:
   ```
   python -m core.db.init_db
   ```

6. Run the application:
   ```
   python -m app.main
   ```

## Setting Up API Keys

### OpenRouter API Key (Required)

The AI Simulator uses OpenRouter API for generating AI responses. Follow these steps to set up your API key:

1. Sign up at [OpenRouter](https://openrouter.ai)
2. Create an API key in your OpenRouter dashboard
3. Create a `.env` file in the project root (you can copy from `.env.example`)
4. Add your API key to the `.env` file:
   ```
   OPENROUTER_API_KEY=your_api_key_here
   ```

### Automatic Environment Setup

You can use the included helper script to set up your environment automatically:

```bash
python create_env_file.py
```

This script will create a `.env` file with all the necessary settings.

### Verifying Your API Key

To check if your OpenRouter API key is working correctly:

```bash
python check_openrouter_key.py
```

If successful, you should see confirmation that your API key is valid.

## Database

The application uses PostgreSQL. Use the following scripts to manage the database:

```bash
# Initialize the database tables
python -m core.db.init_db

# Fix common database issues (PostgreSQL compatibility, UUIDs, etc.)
python scripts/fix_all_db_issues.py

# Generate database documentation
python scripts/generate_database_docs.py

# Validate database models
python scripts/validate_db_models.py
```

## Troubleshooting

If you encounter database-related issues, run the comprehensive fix script:

```bash
python scripts/fix_all_db_issues.py
```

This script addresses common issues like:
- UUID handling in PostgreSQL
- Telegram ID compatibility with UUID fields
- Table schema constraints
- Transaction failures
- Missing indexes

For detailed information on the fixes, see the [Database Fixes Documentation](docs/database_fixes.md).

# AI Симулятор

## Модели Базы Данных

Модели базы данных используются совместно между админ-панелью и основным приложением, обеспечивая согласованность во всей системе.

### Организация Моделей

- Основные модели находятся в `core/db/models/`
- Админ-панель и основное приложение импортируют эти общие модели
- Миграции базы данных управляются с помощью Alembic

### Сервисы CRUD-операций

Для каждой модели реализован сервисный класс, предоставляющий стандартные CRUD-операции:
- **Create** - создание новых записей
- **Read** - чтение существующих записей
- **Update** - обновление данных
- **Delete** - удаление записей

Пример использования:
```python
# Получение экземпляра сервиса
from core.services import UserService
user_service = UserService(db_session)

# Создание нового пользователя
new_user = user_service.create_user(
    username="user1",
    email="user@example.com",
    password_hash="hashed_password"
)

# Получение пользователя по ID
user = user_service.get(user_id)

# Обновление данных
updated_user = user_service.update(
    id=user_id,
    obj_in={"name": "Новое имя"}
)

# Удаление
user_service.delete(id=user_id)
```

### Выполнение Миграций

Для создания новой миграции:

```bash
python -m alembic revision --autogenerate -м "Описание изменений"
```

Для применения миграций:

```bash
python -m alembic upgrade head
```

### Тестирование

Тесты базы данных и сервисов используют SQLite в памяти для более быстрого выполнения:

```bash
# Запуск всех тестов сервисов
pytest tests/services

# Запуск конкретного теста
pytest tests/services/test_user_service.py
```

## Настройка Разработки

1. Установка зависимостей: `pip install -r requirements.txt`
2. Применение миграций: `python -m alembic upgrade head`
3. Запуск приложения: `python -m app.main`
4. Запуск админ-панели: `python -m admin_panel.main`

## Автоматическая Установка

Для автоматизации процесса установки и настройки всех компонентов AI Simulator, мы предоставляем скрипты развертывания.

### Linux/Ubuntu

```bash
# Скопируйте проект на сервер
git clone <URL_репозитория> /tmp/aibot

# Выполните скрипт развертывания
sudo bash /tmp/aibot/scripts/deploy_all.sh
```

### Windows

```powershell
# Запустите PowerShell от имени администратора
# Перейдите в директорию проекта
cd C:\path\to\aibot

# Запустите скрипт развертывания
.\scripts\deploy_windows.ps1
```

### Docker (Контейнеризация)

Для запуска в Docker:

```bash
# Build и запуск с помощью docker-compose
docker-compose up -d
```

Это настроит и запустит все компоненты AI Simulator в контейнерах Docker.

## Компоненты Системы

AI Simulator состоит из следующих компонентов:

1. **API сервер** - FastAPI приложение, обрабатывающее запросы от клиентов
2. **Admin Panel** - Веб-интерфейс для управления персонажами, пользователями и мониторинга 
3. **Telegram Bot** - Бот для взаимодействия с пользователями через Telegram
4. **База данных PostgreSQL** - Хранение всех данных системы

