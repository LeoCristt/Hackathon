# Chat Service - Микросервисная архитектура

WebSocket сервис для чата с интеграцией RabbitMQ, Redis и AI-агента.

## 🚀 Быстрый старт

```bash
# 1. Запуск сервисов
docker-compose up -d chat-service redis rabbitmq

# 2. Открыть тестовый клиент
start C:\Users\Crist\Desktop\Hakaton\backend\chat-client-test.html

# 3. Смотреть логи (в отдельном терминале)
docker-compose logs -f chat-service
```

## 📊 Мониторинг

| Что | Команда/URL |
|-----|-------------|
| **Логи chat-service** | `docker-compose logs -f chat-service` |
| **Redis** | `docker exec -it redis redis-cli` |
| **RabbitMQ UI** | http://localhost:15672 (guest/guest) |
| **Просмотр сообщений в Redis** | `docker exec -it redis redis-cli` → `LRANGE chat:test-chat-123:messages 0 -1` |
| **Sequence счетчик** | `docker exec -it redis redis-cli` → `GET chat:test-chat-123:sequence` |

## Архитектура

```
┌─────────────┐

│   Клиент    │
│  (Browser)  │
└──────┬──────┘
       │ WebSocket
       ▼
┌─────────────────────────────────────┐
│        Chat Service (NestJS)        │
│  - WebSocket Gateway                │
│  - Redis для кэша сообщений         │
│  - RabbitMQ для микросервисов       │
└────┬─────────────┬──────────────────┘
     │             │
     │             │
     ▼             ▼
┌─────────┐   ┌──────────────┐
│RabbitMQ │   │    Redis     │
│         │   │  (кэш N msg) │
└────┬────┘   └──────────────┘
     │
     ├──────────────┐
     │              │
     ▼              ▼
┌──────────┐   ┌──────────┐
│ БД       │   │ AI       │
│ Сервис   │   │ Сервис   │
└──────────┘   └────┬─────┘
                    │
                    │ (ответ)
                    ▼
              [Chat Service]
```

## Функциональность

### 1. Получение сообщения от пользователя

Когда пользователь отправляет сообщение через WebSocket:

1. **WebSocket Gateway** получает сообщение
2. **Отправка всем участникам чата** через WebSocket
3. **Кэширование в Redis** - сохраняет последние N сообщений
4. **Отправка в БД сервис** (RabbitMQ `db_messages`) - одно сообщение
5. **Отправка в AI сервис** (RabbitMQ `ai_requests`) с параметрами:
   - `chatId` - ID чата
   - `message` - текущее сообщение
   - `messageHistory` - последние N сообщений из Redis
   - `aiId` - ID модели AI (опционально)

### 2. Получение ответа от AI

AI-сервис обрабатывает запрос и отправляет ответ в `ai_responses`:

1. **Chat Service** получает ответ от AI
2. **Кэширование ответа AI в Redis**
3. **Сохранение ответа в БД** через RabbitMQ
4. **Отправка ответа пользователям** через WebSocket

## Очереди RabbitMQ

### `db_messages`
**Назначение**: Сохранение каждого сообщения в БД

**Формат**:
```json
{
  "messageId": "chat123-1705315800000-abc123xyz",
  "sequence": 1,
  "username": "Пользователь",
  "message": "Привет!",
  "timestamp": "2025-01-15T10:30:00Z",
  "chatId": "chat123"
}
```

### `ai_requests`
**Назначение**: Запросы к AI-сервисуя

**Формат**:
```json
{
  "chatId": "chat123",
  "message": "Как дела?",
  "messageHistory": [
    {
      "messageId": "chat123-1705315800000-abc123xyz",
      "sequence": 1,
      "username": "Пользователь",
      "message": "Привет!",
      "timestamp": "2025-01-15T10:30:00Z",
      "chatId": "chat123"
    }
  ],
  "aiId": "gpt-4"
}
```

### `ai_responses`
**Назначение**: Ответы от AI-сервиса

**Формат**:
```json
{
  "chatId": "chat123",
  "response": "Привет! У меня всё отлично, спасибо!"
}
```

## Redis кэширование

Для каждого чата хранится список последних N сообщений:

- **Ключ сообщений**: `chat:{chatId}:messages`
- **Тип**: Redis List
- **TTL**: 24 часа
- **Максимум**: Настраивается через `REDIS_MAX_MESSAGES` (по умолчанию 50)

### Sequence (порядковый номер)

Для гарантии правильного порядка сообщений используется атомарный счетчик:

- **Ключ**: `chat:{chatId}:sequence`
- **Тип**: Redis Counter (INCR)
- **TTL**: 7 дней
- **Значения**: 1, 2, 3, 4... (инкрементируются атомарно)

Это решает проблему race condition, когда:
- Сообщение пользователя отправляется в БД
- Ответ AI приходит раньше
- БД может определить правильный порядок по `sequence`

## Переменные окружения

```env
PORT=3001
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672
REDIS_URL=redis://redis:6379
REDIS_MAX_MESSAGES=50
```

## Запуск и тестирование

### 1. Запуск сервисов

```bash
# Запуск всех сервисов
docker-compose up -d chat-service redis rabbitmq

# Проверка статуса
docker-compose ps
```

### 2. Тестирование через веб-клиент

Откройте файл `chat-client-test.html` в браузере:

```bash
# Windows
start C:\Users\Crist\Desktop\Hakaton\backend\chat-client-test.html

# Linux/Mac
open /path/to/chat-client-test.html
```

**Что можно протестировать:**
- ✅ Анонимный чат (без username)
- ✅ Менеджер с именем (указать username)
- ✅ Разные AI модели (указать aiId)
- ✅ Sequence и messageId в каждом сообщении

### 3. Локальная разработка

```bash
cd chat-service
npm install
npm run start:dev
```

## API WebSocket

### События от клиента к серверу

**join** - Присоединиться к чату
```javascript
// Обычный пользователь (анонимный)
socket.emit('join', {
  chatId: 'chat123'
});

// Менеджер или AI с именем
socket.emit('join', {
  username: 'Менеджер Иван',
  chatId: 'chat123'
});
```

**message** - Отправить сообщение
```javascript
socket.emit('message', {
  message: 'Привет!',
  aiId: 'gpt-4' // опционально
});
```

### События от сервера к клиенту

**message** - Новое сообщение в чате
```javascript
socket.on('message', (data) => {
  // { messageId, sequence, username, message, timestamp, chatId }
  // messageId: уникальный ID сообщения
  // sequence: порядковый номер в чате (1, 2, 3...)
  // username: "Пользователь" (анонимы), "AI Ассистент", "Менеджер Иван" и т.д.
});
```

## Мониторинг и отладка

### Логи Chat Service

Для просмотра подробных логов работы сервиса:

```bash
docker-compose logs -f chat-service
```

### Структура логов

#### 1. Отправка сообщения пользователя в БД

```
📦 ═══ ОТПРАВКА В БД СЕРВИС ═══
Очередь: db_messages
Данные: {
  "messageId": "chat123-1705315800000-abc123xyz",
  "sequence": 1,
  "username": "Пользователь",
  "message": "Привет!",
  "timestamp": "2025-01-15T10:30:00.000Z",
  "chatId": "chat123"
}
✅ Сообщение отправлено в БД
```

#### 2. Отправка запроса в AI сервис

```
🤖 ═══ ОТПРАВКА В AI СЕРВИС ═══
Очередь: ai_requests
Chat ID: chat123
Текущее сообщение: Привет!
История сообщений: 5 шт.
AI Model ID: gpt-4
Полные данные: {
  "chatId": "chat123",
  "message": "Привет!",
  "messageHistory": [...],
  "aiId": "gpt-4"
}
✅ Запрос отправлен в AI сервис
```

#### 3. Получение ответа от AI

```
🎯 ═══ ПОЛУЧЕН ОТВЕТ ОТ AI СЕРВИСА ═══
Очередь: ai_responses
Chat ID: chat123
Ответ AI: Привет! Чем могу помочь?
Полные данные: {
  "chatId": "chat123",
  "response": "Привет! Чем могу помочь?"
}

📝 Сформированное сообщение AI:
  Message ID: chat123-1705315802000-xyz789
  Sequence: 2
  Username: AI Ассистент
✅ Ответ AI закэширован в Redis

📦 ═══ ОТПРАВКА ОТВЕТА AI В БД ═══
Очередь: db_messages
Данные: {...}
✅ Ответ AI отправлен в БД

🌐 Отправка ответа AI через WebSocket
  Количество подключенных клиентов: 1
✅ Ответ AI отправлен всем участникам чата
```

### RabbitMQ Management UI

Просмотр очередей и сообщений: http://localhost:15672

**Логин**: guest
**Пароль**: guest

**Очереди для проверки:**
- `db_messages` - сообщения для БД
- `ai_requests` - запросы к AI
- `ai_responses` - ответы от AI

### Redis CLI

Проверка кэша и счетчиков:

```bash
# Подключение к Redis
docker exec -it redis redis-cli

# Просмотр сообщений чата
LRANGE chat:chat123:messages 0 -1

# Проверка текущего sequence
GET chat:chat123:sequence

# Количество сообщений в кэше
LLEN chat:chat123:messages
```

## Интеграция с другими сервисами

### БД Сервис
Подписаться на `db_messages` и сохранять каждое сообщение.

### AI Сервис
1. Подписаться на `ai_requests`
2. Обработать с учетом `messageHistory` и `aiId`
3. Отправить ответ в `ai_responses` с `chatId` и `response`
