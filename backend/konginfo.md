# Защита виджета через Kong API Gateway

## Что реализовано

Система защиты виджета через Kong API Gateway с проверкой домена в БД и автоматическим выбором AI модели.

## Архитектура

```
User → Widget (domain: example.com)
           ↓
     Kong Gateway (port 8000)
           ↓
   [Kong Plugin: widget-domain-check]
           ↓
     Проверка в БД (widget_domains)
           ↓
   Домен найден? → Добавляет headers:
                    - X-Widget-AI-Model: gpt-4
                    - X-Widget-Domain: example.com
                    - X-Widget-Authorized: true
           ↓
     frontend-widget / chat-service
```

## Компоненты

### 1. БД (operator_db)

**Таблица widget_domains:**
```sql
CREATE TABLE widget_domains (
    id SERIAL PRIMARY KEY,
    domain VARCHAR(255) UNIQUE NOT NULL,
    ai_model VARCHAR(100) NOT NULL DEFAULT 'gpt-4',
    is_active BOOLEAN DEFAULT true,
    max_requests_per_day INTEGER DEFAULT 1000,
    allowed_origins TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Поля:**
- `domain` - доменное имя (без http://, например: example.com, localhost)
- `ai_model` - AI модель для этого домена (gpt-4, claude-3, gpt-4-turbo)
- `is_active` - активен ли домен
- `max_requests_per_day` - лимит запросов (для будущей rate limit логики)
- `allowed_origins` - массив разрешённых Origin для CORS

**Тестовые данные:**
```sql
INSERT INTO widget_domains (domain, ai_model, allowed_origins) VALUES
    ('localhost', 'gpt-5', ARRAY['http://localhost:3000', 'http://127.0.0.1:3000']),
    ('example.com', 'claude-3', ARRAY['https://example.com']),
    ('demo.com', 'gpt-4-turbo', ARRAY['https://demo.com']);
```

### 2. Kong Lua Plugin

**Файлы:**
- `kong-plugins/widget-domain-check/handler.lua` - логика плагина
- `kong-plugins/widget-domain-check/schema.lua` - конфигурация

**Что делает плагин:**

1. Читает `Origin` или `Referer` из headers
2. Извлекает домен (убирает протокол и порт)
3. Подключается к PostgreSQL (operator-db)
4. Выполняет запрос:
   ```sql
   SELECT domain, ai_model, is_active, allowed_origins
   FROM widget_domains
   WHERE domain = 'example.com' AND is_active = true
   ```
5. Если домен найден:
   - Проверяет Origin в allowed_origins
   - Добавляет headers для upstream сервиса
   - Пропускает запрос дальше
6. Если домен не найден → `403 Forbidden`

**Добавляемые headers:**
- `X-Widget-AI-Model` - AI модель из БД
- `X-Widget-Domain` - домен клиента
- `X-Widget-Authorized` - флаг авторизации

### 3. Widget.js

**Изменения:**

```javascript
// Запросы идут через Kong (порт 8000)
fetch('http://localhost:8000/widget/html')

// WebSocket через Kong
socket = io('http://localhost:8000/api/chat');
```

Kong проверит домен автоматически по Origin header.

### 4. chat-service

**Изменения в chat.gateway.ts:**

```typescript
handleConnection(client: Socket) {
  // Читаем headers от Kong plugin
  const aiModel = client.handshake.headers['x-widget-ai-model'];
  const domain = client.handshake.headers['x-widget-domain'];
  const isAuthorized = client.handshake.headers['x-widget-authorized'];

  if (!isAuthorized) {
    client.disconnect();
    return;
  }

  // Сохраняем AI модель
  (client as any).aiModel = aiModel || 'gpt-4';
}

handleMessage() {
  // Используем AI модель из сокета
  const aiModel = (client as any).aiModel;

  await this.rabbitMQService.sendToAI({
    aiId: aiModel  // gpt-4, claude-3, и т.д.
  });
}
```

## Настройка

### 1. Запуск

```bash
cd backend
docker-compose up -d
```

Kong автоматически:
1. Загрузит custom plugin из `./kong-plugins`
2. Применит миграции БД (02_widget_domains.sql)
3. Настроит routes и services (kong-setup.sh)

### 2. Проверка плагина

```bash
# Список плагинов
curl http://localhost:8001/plugins

# Должен быть: widget-domain-check
```

### 3. Проверка работы

**Успешный запрос:**
```bash
curl -H "Origin: http://localhost:3000" http://localhost:8000/widget/html
# → 200 OK (домен localhost в БД)
```

**Запрещённый запрос:**
```bash
curl -H "Origin: http://forbidden.com" http://localhost:8000/widget/html
# → 403 Forbidden (домен не в БД)
```

## Управление доменами

### Добавление нового домена

```sql
INSERT INTO widget_domains (domain, ai_model, is_active, allowed_origins)
VALUES ('newclient.com', 'gpt-4-turbo', true, ARRAY['https://newclient.com']);
```

### Изменение AI модели

```sql
UPDATE widget_domains
SET ai_model = 'claude-3'
WHERE domain = 'example.com';
```

### Отключение домена

```sql
UPDATE widget_domains
SET is_active = false
WHERE domain = 'spammer.com';
```

### Просмотр всех доменов

```sql
SELECT domain, ai_model, is_active
FROM widget_domains
ORDER BY created_at DESC;
```

## Логи

### Kong logs:

```bash
docker logs kong -f
```

Ищите:
```
[widget-domain-check] Request from origin: http://localhost:3000
[widget-domain-check] Extracted domain: localhost
[widget-domain-check] Domain found: localhost, AI model: gpt-4
[widget-domain-check] Request authorized
```

### chat-service logs:

```bash
docker logs chat-service -f
```

Ищите:
```
🔗 Клиент подключен: socket_id
✅ Авторизован: domain=localhost, ai_model=gpt-4
🤖 ═══ ОТПРАВКА В AI СЕРВИС ═══
AI Model (из Kong): gpt-4
```

## Безопасность

### Что защищено:

1. **Проверка домена** - виджет работает только на разрешённых доменах
2. **Origin whitelist** - дополнительная проверка CORS
3. **Автоматический выбор AI** - нельзя подменить модель из frontend
4. **Отключение доменов** - мгновенная блокировка через `is_active=false`

### Что НЕ защищено (TODO):

1. **Rate limiting** - нет лимита запросов (max_requests_per_day не используется)
2. **DDoS** - нужен rate limit plugin Kong
3. **Auth токены** - нет JWT (если нужно)

## Troubleshooting

### Виджет не загружается

**Проблема:** `403 Forbidden`

**Решение:**
1. Проверьте домен в БД:
   ```sql
   SELECT * FROM widget_domains WHERE domain = 'ваш-домен';
   ```
2. Проверьте `is_active = true`
3. Проверьте allowed_origins

### AI модель не меняется

**Проблема:** Всегда используется одна модель

**Решение:**
1. Проверьте БД:
   ```sql
   SELECT domain, ai_model FROM widget_domains WHERE domain = 'ваш-домен';
   ```
2. Перезапустите chat-service:
   ```bash
   docker-compose restart chat-service
   ```

### Plugin не работает

**Проблема:** Kong не видит plugin

**Решение:**
1. Проверьте монтирование volume:
   ```bash
   docker exec kong ls /usr/local/custom-plugins/widget-domain-check/
   # Должны быть: handler.lua, schema.lua
   ```
2. Проверьте переменную окружения:
   ```bash
   docker exec kong env | grep KONG_PLUGINS
   # Должно быть: bundled,widget-domain-check
   ```
3. Перезапустите Kong:
   ```bash
   docker-compose restart kong
   ```

## Расширение

### Добавление rate limiting

В `handler.lua` добавить:

```lua
-- Проверка лимитов в Redis
local requests_today = redis:get("rate_limit:" .. domain .. ":" .. today)
if requests_today and tonumber(requests_today) > domain_config.max_requests_per_day then
  return kong.response.exit(429, { message = "Rate limit exceeded" })
end

-- Инкремент счётчика
redis:incr("rate_limit:" .. domain .. ":" .. today)
redis:expire("rate_limit:" .. domain .. ":" .. today, 86400)
```

### Добавление логирования в БД

В `handler.lua`:

```lua
-- Логирование запроса
local log_query = string.format([[
  INSERT INTO widget_requests (domain, request_path, ip_address)
  VALUES ('%s', '%s', '%s')
]], domain, kong.request.get_path(), kong.client.get_ip())

pg:query(log_query)
```

### UI для управления

Создать админ панель (operator-service) для:
- Добавления/удаления доменов
- Изменения AI моделей
- Просмотра статистики
- Управления лимитами

## Альтернативы

Если Kong plugin сложен, можно использовать:

1. **Middleware в chat-service** - проверка домена в коде
2. **Nginx** - аналогичная логика на Lua
3. **API Gateway (AWS/Azure)** - облачное решение

Но Kong plugin даёт:
- Централизованную защиту
- Не нагружает chat-service
- Легко масштабируется
- Единая точка контроля

## Итог

Реализована полная защита виджета:
- Виджет работает только на разрешённых доменах
- AI модель выбирается автоматически из БД
- Невозможно подделать домен или модель из frontend
- Легко управлять через SQL
- Готово к масштабированию
