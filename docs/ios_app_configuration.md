# Конфигурация iOS-приложения

В этом документе описаны необходимые настройки для корректной работы мобильного приложения для iOS.

## 1. Настройки Info.plist

Добавьте следующие ключи в файл Info.plist вашего iOS-приложения:

```xml
<!-- Поддержка Sign In with Apple -->
<key>com.apple.developer.applesignin</key>
<array>
    <string>Default</string>
</array>

<!-- Поддержка Push-уведомлений -->
<key>UIBackgroundModes</key>
<array>
    <string>remote-notification</string>
</array>

<!-- Настройки App Transport Security -->
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsArbitraryLoads</key>
    <false/>
    <key>NSExceptionDomains</key>
    <dict>
        <key>yourapiserver.com</key>
        <dict>
            <key>NSIncludesSubdomains</key>
            <true/>
            <key>NSTemporaryExceptionAllowsInsecureHTTPLoads</key>
            <false/>
            <key>NSTemporaryExceptionMinimumTLSVersion</key>
            <string>TLSv1.2</string>
        </dict>
    </dict>
</dict>

<!-- Настройки для камеры и доступа к фотографиям -->
<key>NSCameraUsageDescription</key>
<string>Приложение использует камеру для создания фотографий профиля</string>

<key>NSPhotoLibraryUsageDescription</key>
<string>Приложение использует библиотеку фотографий для выбора фотографий профиля</string>

<!-- Настройки для геолокации (если нужна) -->
<key>NSLocationWhenInUseUsageDescription</key>
<string>Приложение использует геолокацию для улучшения поиска совпадений</string>
```

## 2. Настройки StoreKit

### 2.1. Идентификаторы продуктов

Для корректной работы внутриигровых покупок используйте следующие идентификаторы продуктов:

| Product ID | Тип | Описание |
|------------|-----|----------|
| `com.yourdomain.app.stars.small` | Consumable | 100 звезд |
| `com.yourdomain.app.stars.medium` | Consumable | 500 звезд |
| `com.yourdomain.app.stars.large` | Consumable | 1000 звезд |
| `com.yourdomain.app.premium.1month` | Auto-Renewable Subscription | Premium подписка на 1 месяц |
| `com.yourdomain.app.premium.3months` | Auto-Renewable Subscription | Premium подписка на 3 месяца |
| `com.yourdomain.app.premium.1year` | Auto-Renewable Subscription | Premium подписка на 1 год |

### 2.2. Группы подписок

Создайте группу подписок с ID `com.yourdomain.app.premium_group` для управления Premium-подписками разной длительности.

## 3. Настройка Push-уведомлений

### 3.1. Certificates

1. Создайте APNs сертификат в Apple Developer Console
2. Экспортируйте его в формате .p8
3. Сохраните сертификат в папке проекта по пути `keys/AuthKey_Apple.p8`
4. Укажите ID ключа в переменной окружения `APPLE_KEY_ID`

### 3.2. Категории уведомлений

В приложении используются следующие категории уведомлений:

| Категория | Описание | Действия |
|-----------|----------|----------|
| `message` | Новое сообщение | Просмотр, Ответить |
| `match` | Новое совпадение | Просмотр профиля |
| `event` | Новое событие | Принять, Отклонить |

## 4. Обработка глубоких ссылок (Deep Links)

Настройте схему URL для вашего приложения:

```xml
<key>CFBundleURLTypes</key>
<array>
    <dict>
        <key>CFBundleTypeRole</key>
        <string>Editor</string>
        <key>CFBundleURLName</key>
        <string>com.yourdomain.app</string>
        <key>CFBundleURLSchemes</key>
        <array>
            <string>yourapp</string>
        </array>
    </dict>
</array>
```

### 4.1. Структура глубоких ссылок

Приложение поддерживает следующие форматы глубоких ссылок:

- `yourapp://character/{character_id}` - открыть профиль персонажа
- `yourapp://chat/{character_id}` - открыть чат с персонажем
- `yourapp://profile` - открыть профиль пользователя
- `yourapp://event/{event_id}` - открыть страницу события

## 5. Политика конфиденциальности

При интеграции с iOS-приложением обязательно укажите ссылку на политику конфиденциальности в App Store Connect.

Стандартный URL для политики конфиденциальности:
`https://yourdomain.com/privacy-policy`

## 6. Требования App Store

### 6.1. Возрастной рейтинг

Рекомендуемый возрастной рейтинг для приложения: 17+

### 6.2. Скриншоты

Для публикации в App Store подготовьте скриншоты следующих размеров:
- iPhone 6.5" (1284 x 2778 px)
- iPhone 5.5" (1242 x 2208 px)
- iPad Pro 12.9" (2048 x 2732 px)

### 6.3. Видео превью

Подготовьте видео превью в соответствии с требованиями App Store:
- Формат: H.264
- Разрешение: 1080p или 4K
- Длительность: 15-30 секунд