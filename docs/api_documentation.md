# AI Simulator API Documentation

## Содержание
1. [Аутентификация](#аутентификация)
   - [Получение токенов](#получение-токенов)
   - [Обновление токенов](#обновление-токенов)
   - [Сроки действия токенов](#сроки-действия-токенов)
2. [Ограничения и лимиты](#ограничения-и-лимиты)
   - [Rate Limits](#rate-limits)
   - [Ограничения доступа](#ограничения-доступа)
3. [Эндпоинты API](#эндпоинты-api)
   - [Аутентификация](#эндпоинты-аутентификации)
   - [Чат](#эндпоинты-чата)
   - [Персонажи](#эндпоинты-персонажей)
   - [Взаимодействия](#эндпоинты-взаимодействий)
   - [Пользователи](#эндпоинты-пользователей)
   - [Служебные](#служебные-эндпоинты)
4. [Коды ошибок](#коды-ошибок)
5. [Примеры использования](#примеры-использования)

## Аутентификация

API AI Simulator использует JWT (JSON Web Tokens) для аутентификации. Все запросы к защищенным эндпоинтам должны содержать действительный токен доступа в заголовке `Authorization`.

### Получение токенов

Для получения токена доступа необходимо предоставить учетные данные пользователя.

**Эндпоинт**: `POST /api/v1/auth/login`

**Тело запроса**:
```json
{
  "username": "user@example.com",
  "password": "password123"
}
```

**Пример ответа**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### Обновление токенов

Когда токен доступа истекает, вы можете использовать refresh_token для получения нового токена доступа без необходимости повторной аутентификации.

**Эндпоинт**: `POST /api/v1/auth/refresh`

**Заголовки**:
```
Authorization: Bearer {refresh_token}
```

**Пример ответа**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### Сроки действия токенов

| Тип токена    | Срок действия      | Конфигурация                        |
|---------------|--------------------|------------------------------------|
| access_token  | 30 минут           | ACCESS_TOKEN_EXPIRE_MINUTES=30     |
| refresh_token | 7 дней             | REFRESH_TOKEN_EXPIRE_DAYS=7        |

После истечения срока действия refresh_token вам необходимо снова выполнить полную аутентификацию.

## Ограничения и лимиты

### Rate Limits

Для предотвращения злоупотребления API установлены следующие ограничения:

| Эндпоинт                           | Лимит                              | Период восстановления |
|-----------------------------------|------------------------------------|--------------------|
| `/api/v1/auth/*`                  | 5 запросов                         | 60 секунд          |
| `/api/v1/chat/*`                  | 30 запросов                        | 60 секунд          |
| Остальные эндпоинты               | 60 запросов                        | 60 секунд          |

При превышении лимита запросов сервер вернет ответ со статусом `429 Too Many Requests`.

### Ограничения доступа

Доступ к API может быть ограничен на основе следующих критериев:

- **Уровень пользователя**: некоторые эндпоинты доступны только для пользователей с определенными правами (например, администраторы)
- **Статус активации**: неактивированные пользователи могут иметь ограниченный доступ к функциям
- **IP-адрес**: возможны географические ограничения доступа к API

## Эндпоинты API

### Эндпоинты аутентификации

#### 1. Вход пользователя

**Метод**: `POST /api/v1/auth/login`

**Описание**: Аутентификация пользователя и получение токенов доступа.

**Параметры запроса**:
```json
{
  "username": "user@example.com",
  "password": "password123"
}
```

**Успешный ответ** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

#### 2. Регистрация пользователя

**Метод**: `POST /api/v1/auth/register`

**Описание**: Создание новой учетной записи пользователя.

**Параметры запроса**:
```json
{
  "email": "newuser@example.com",
  "username": "newuser",
  "password": "password123",
  "name": "Новый пользователь"
}
```

**Успешный ответ** (201 Created):
```json
{
  "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "email": "newuser@example.com",
  "username": "newuser",
  "name": "Новый пользователь",
  "is_active": true,
  "created_at": "2023-05-10T15:30:45Z"
}
```

#### 3. Обновление токена

**Метод**: `POST /api/v1/auth/refresh`

**Описание**: Получение нового токена доступа с помощью refresh_token.

**Заголовки**:
```
Authorization: Bearer {refresh_token}
```

**Успешный ответ** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### Эндпоинты чата

#### 1. Отправка сообщения персонажу

**Метод**: `POST /api/v1/chat/characters/{character_id}/message`

**Описание**: Отправка сообщения персонажу и получение ответа.

**Заголовки**:
```
Authorization: Bearer {access_token}
```

**Параметры запроса**:
```json
{
  "message": "Привет, как дела?",
  "message_type": "text",
  "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
}
```

**Успешный ответ** (200 OK):
```json
{
  "character_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "character_name": "София",
  "response": {
    "text": "Привет! У меня всё отлично, занимаюсь своими проектами. А как твои дела?",
    "type": "text"
  },
  "message_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "timestamp": "2023-05-10T15:32:45Z"
}
```

#### 2. Получение истории чата

**Метод**: `GET /api/v1/chat/history/{user_id}/{character_id}`

**Описание**: Получение истории сообщений между пользователем и персонажем.

**Заголовки**:
```
Authorization: Bearer {access_token}
```

**Параметры запроса**:
- `limit` (query, опционально): количество сообщений (по умолчанию 50)
- `offset` (query, опционально): смещение для пагинации (по умолчанию 0)

**Успешный ответ** (200 OK):
```json
{
  "messages": [
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "sender_type": "user",
      "sender_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "content": "Привет, как дела?",
      "timestamp": "2023-05-10T15:30:45Z"
    },
    {
      "id": "4da85f64-5717-4562-b3fc-2c963f66afa6",
      "sender_type": "character",
      "sender_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "content": "Привет! У меня всё отлично, занимаюсь своими проектами. А как твои дела?",
      "timestamp": "2023-05-10T15:32:45Z"
    }
  ],
  "total": 2,
  "has_more": false
}
```

### Эндпоинты персонажей

#### 1. Получение списка персонажей

**Метод**: `GET /api/v1/characters`

**Описание**: Получение списка всех доступных персонажей.

**Заголовки**:
```
Authorization: Bearer {access_token}
```

**Параметры запроса**:
- `limit` (query, опционально): количество персонажей (по умолчанию 10)
- `offset` (query, опционально): смещение для пагинации (по умолчанию 0)

**Успешный ответ** (200 OK):
```json
{
  "characters": [
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "name": "София",
      "age": 25,
      "gender": "female",
      "personality": ["умная", "амбициозная", "добрая"],
      "background": "София - целеустремленная девушка, увлеченная саморазвитием и новыми технологиями.",
      "interests": ["спорт", "бизнес", "технологии"]
    },
    {
      "id": "4fa85f64-5717-4562-b3fc-2c963f66afa6",
      "name": "Алексей",
      "age": 28,
      "gender": "male",
      "personality": ["общительный", "креативный", "веселый"],
      "background": "Алексей - творческая личность, много путешествует и интересуется фотографией.",
      "interests": ["путешествия", "фотография", "музыка"]
    }
  ],
  "total": 2,
  "has_more": false
}
```

#### 2. Получение информации о персонаже

**Метод**: `GET /api/v1/characters/{character_id}`

**Описание**: Получение подробной информации о конкретном персонаже.

**Заголовки**:
```
Authorization: Bearer {access_token}
```

**Успешный ответ** (200 OK):
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "name": "София",
  "age": 25,
  "gender": "female",
  "personality": ["умная", "амбициозная", "добрая"],
  "background": "София - целеустремленная девушка, увлеченная саморазвитием и новыми технологиями.",
  "interests": ["спорт", "бизнес", "технологии"],
  "created_at": "2023-05-10T15:30:45Z",
  "updated_at": "2023-05-10T15:30:45Z"
}
```

### Эндпоинты взаимодействий

#### 1. Отправка подарка

**Метод**: `POST /api/v1/chat/characters/{character_id}/gift`

**Описание**: Отправка подарка персонажу.

**Заголовки**:
```
Authorization: Bearer {access_token}
```

**Параметры запроса**:
```json
{
  "gift_id": "flower_bouquet",
  "message": "Это для тебя!",
  "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
}
```

**Успешный ответ** (200 OK):
```json
{
  "character_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "character_name": "София",
  "response": {
    "text": "Ого спасибо. Ты умеешь удивлять! Очень мило с твоей стороны.",
    "type": "text",
    "reaction": "happy"
  },
  "message_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "timestamp": "2023-05-10T15:32:45Z"
}
```

#### 2. Запись события взаимодействия

**Метод**: `POST /api/v1/interactions/record`

**Описание**: Запись события взаимодействия пользователя с персонажем.

**Заголовки**:
```
Authorization: Bearer {access_token}
```

**Параметры запроса**:
```json
{
  "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "character_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "interaction_type": "gift"
}
```

**Успешный ответ** (201 Created):
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "character_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "interaction_type": "gift",
  "created_at": "2023-05-10T15:32:45Z"
}
```

### Эндпоинты пользователей

#### 1. Получение профиля пользователя

**Метод**: `GET /api/v1/users/me`

**Описание**: Получение информации о текущем пользователе.

**Заголовки**:
```
Authorization: Bearer {access_token}
```

**Успешный ответ** (200 OK):
```json
{
  "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "username": "user",
  "email": "user@example.com",
  "name": "Пользователь",
  "is_active": true,
  "created_at": "2023-05-10T15:30:45Z"
}
```

#### 2. Обновление профиля пользователя

**Метод**: `PUT /api/v1/users/me`

**Описание**: Обновление информации о текущем пользователе.

**Заголовки**:
```
Authorization: Bearer {access_token}
```

**Параметры запроса**:
```json
{
  "name": "Новое Имя",
  "email": "new.email@example.com"
}
```

**Успешный ответ** (200 OK):
```json
{
  "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "username": "user",
  "email": "new.email@example.com",
  "name": "Новое Имя",
  "is_active": true,
  "updated_at": "2023-05-10T16:30:45Z"
}
```

### Служебные эндпоинты

#### 1. Проверка состояния API

**Метод**: `GET /api/v1/health`

**Описание**: Проверка доступности и работоспособности API.

**Успешный ответ** (200 OK):
```json
{
  "status": "ok"
}
```

#### 2. Корневой эндпоинт

**Метод**: `GET /`

**Описание**: Базовая информация об API.

**Успешный ответ** (200 OK):
```json
{
  "message": "API online",
  "docs": "/docs"
}
```

#### 3. Информация о базе данных

**Метод**: `GET /database-info`

**Описание**: Получение информации о таблицах базы данных (только для разработчиков и администраторов).

**Заголовки**:
```
Authorization: Bearer {access_token}
```

**Успешный ответ** (200 OK):
```json
{
  "tables": ["users", "characters", "messages", "chat_history", "interactions", "memory_entries"],
  "table_details": {
    "users": {
      "columns": ["user_id", "username", "email", "password_hash", "name", "is_active", "created_at", "updated_at"],
      "row_count": 5
    },
    "characters": {
      "columns": ["id", "name", "age", "gender", "personality", "background", "interests", "created_at", "updated_at"],
      "row_count": 3
    }
  }
}
```

## Коды ошибок

API использует стандартные HTTP-коды состояния для индикации успеха или неудачи запроса:

| Код   | Описание                   | Типичные причины                                      |
|-------|----------------------------|------------------------------------------------------|
| 200   | OK                         | Запрос выполнен успешно                               |
| 201   | Created                    | Ресурс успешно создан                                |
| 400   | Bad Request                | Неверный формат запроса или недопустимые параметры    |
| 401   | Unauthorized               | Отсутствие или недействительный токен аутентификации  |
| 403   | Forbidden                  | Недостаточно прав для выполнения операции             |
| 404   | Not Found                  | Запрашиваемый ресурс не найден                        |
| 409   | Conflict                   | Конфликт при создании ресурса (например, дублирование)|
| 422   | Unprocessable Entity       | Данные запроса не прошли валидацию                   |
| 429   | Too Many Requests          | Превышен лимит запросов (rate limit)                 |
| 500   | Internal Server Error      | Внутренняя ошибка сервера                            |

### Примеры ошибок

#### Недействительный токен

```json
{
  "detail": "Недопустимые учетные данные"
}
```

#### Превышение лимита запросов

```json
{
  "detail": "Превышен лимит запросов. Попробуйте снова через 60 секунд."
}
```

#### Ресурс не найден

```json
{
  "detail": "Персонаж с id 3fa85f64-5717-4562-b3fc-2c963f66afa6 не найден"
}
```

## Примеры использования

### Пример 1: Аутентификация и отправка сообщения

```python
import requests
import json

# Аутентификация
auth_url = "https://api.example.com/api/v1/auth/login"
auth_data = {
    "username": "user@example.com",
    "password": "password123"
}

auth_response = requests.post(auth_url, json=auth_data)
tokens = auth_response.json()
access_token = tokens["access_token"]

# Отправка сообщения персонажу
message_url = "https://api.example.com/api/v1/chat/characters/3fa85f64-5717-4562-b3fc-2c963f66afa6/message"
message_data = {
    "message": "Привет, как дела?",
    "message_type": "text",
    "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
}
headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

response = requests.post(message_url, headers=headers, json=message_data)
print(json.dumps(response.json(), indent=2, ensure_ascii=False))
```

### Пример 2: Получение списка персонажей и истории чата

```python
import requests
import json

# Используем существующий токен доступа
access_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

# Получение списка персонажей
characters_url = "https://api.example.com/api/v1/characters"
characters_response = requests.get(characters_url, headers=headers)
characters = characters_response.json()

# Вывод информации о персонажах
print("Доступные персонажи:")
for character in characters["characters"]:
    print(f"- {character['name']} (ID: {character['id']})")

# Выбор первого персонажа для получения истории чата
character_id = characters["characters"][0]["id"]
user_id = "3fa85f64-5717-4562-b3fc-2c963f66afa6"

# Получение истории чата
history_url = f"https://api.example.com/api/v1/chat/history/{user_id}/{character_id}"
history_response = requests.get(history_url, headers=headers)
chat_history = history_response.json()

# Вывод истории сообщений
print("\nИстория сообщений:")
for message in chat_history["messages"]:
    sender_type = "Вы" if message["sender_type"] == "user" else characters["characters"][0]["name"]
    print(f"{sender_type} ({message['timestamp']}): {message['content']}")
```

### Пример 3: Отправка подарка персонажу

```bash
#!/bin/bash

# Токен доступа
ACCESS_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# ID персонажа и пользователя
CHARACTER_ID="3fa85f64-5717-4562-b3fc-2c963f66afa6"
USER_ID="3fa85f64-5717-4562-b3fc-2c963f66afa6"

# Отправка подарка
curl -X POST \
  "https://api.example.com/api/v1/chat/characters/${CHARACTER_ID}/gift" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "gift_id": "flower_bouquet",
    "message": "Это для тебя!",
    "user_id": "'${USER_ID}'"
  }'
```
```

Made changes.