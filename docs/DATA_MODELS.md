# Модели данных и контракты

## 📋 Обзор

Данный документ описывает модели данных, используемые в мультиагентной системе технической поддержки, включая форматы сообщений, структуры хранения и API контракты.

---

## 🔄 Модель обращений (Message Model)

### User Message (Входящее сообщение)

**Формат RabbitMQ Queue: `ai_requests`**

```typescript
interface AIRequest {
  chatId: string;           // Уникальный ID чата
  message: string;          // Текст сообщения пользователя
  username?: string;        // Имя пользователя (опционально)
  messageHistory: MessageHistoryItem[];  // История чата
  metadata?: {
    timestamp?: string;     // ISO 8601
    source?: string;        // "widget" | "admin_console" | "api"
    userId?: string;        // ID пользователя из БД
  };
}
```

**Пример:**

```json
{
  "chatId": "chat_abc123xyz",
  "message": "Не работает Wi-Fi",
  "username": "Пользователь",
  "messageHistory": [
    {
      "username": "Пользователь",
      "message": "Привет"
    },
    {
      "answer": "Здравствуйте! Чем могу помочь?"
    }
  ],
  "metadata": {
    "timestamp": "2024-10-18T10:30:00Z",
    "source": "widget",
    "userId": "user_12345"
  }
}
```

### AI Response (Ответ AI)

**Формат RabbitMQ Queue: `ai_response`**

```typescript
interface AIResponse {
  chatId: string;           // ID чата (совпадает с запросом)
  answer: string;           // Сгенерированный ответ
  botUsername: string;      // Имя бота (обычно "AI-помощник")
  isManager: boolean;       // Флаг эскалации к оператору
  metadata?: {
    agent: string;          // Какой агент обработал
    confidence: number;     // Уверенность модели (0-1)
    context_similarity: number;  // Similarity с контекстом
    processing_time_ms: number;  // Время обработки
    timestamp: string;      // ISO 8601
  };
}
```

**Пример:**

```json
{
  "chatId": "chat_abc123xyz",
  "answer": "Проверьте подключение к роутеру и убедитесь, что Wi-Fi включен.",
  "botUsername": "AI-помощник",
  "isManager": false,
  "metadata": {
    "agent": "Сеть",
    "confidence": 0.89,
    "context_similarity": 0.76,
    "processing_time_ms": 1245,
    "timestamp": "2024-10-18T10:30:01Z"
  }
}
```

### Message History Item

```typescript
type MessageHistoryItem = UserHistoryItem | AIHistoryItem;

interface UserHistoryItem {
  username: string;
  message: string;
  timestamp?: string;       // ISO 8601
}

interface AIHistoryItem {
  answer: string;
  botUsername?: string;
  timestamp?: string;       // ISO 8601
}
```

---

## 💬 Модель чата (Chat Model)

### Chat Entity (PostgreSQL - Operator Service)

```typescript
interface Chat {
  id: string;               // UUID
  chatId: string;           // Уникальный ID чата (совпадает с RabbitMQ)
  status: ChatStatus;       // "active" | "waiting" | "resolved" | "closed"
  createdAt: Date;          // Дата создания
  updatedAt: Date;          // Последнее обновление
  assignedTo?: string;      // ID оператора (если назначен)
  category?: string;        // Категория проблемы
  priority?: Priority;      // "low" | "medium" | "high" | "critical"
  metadata: {
    source: string;         // Откуда пришёл запрос
    userAgent?: string;     // User agent браузера
    initialQuery: string;   // Первый запрос пользователя
  };
}

enum ChatStatus {
  ACTIVE = "active",        // Активный чат
  WAITING = "waiting",      // Ожидает оператора
  RESOLVED = "resolved",    // Проблема решена
  CLOSED = "closed"         // Чат закрыт
}

enum Priority {
  LOW = "low",
  MEDIUM = "medium",
  HIGH = "high",
  CRITICAL = "critical"
}
```

**SQL Schema:**

```sql
CREATE TABLE chats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chat_id VARCHAR(255) UNIQUE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    assigned_to UUID REFERENCES users(id),
    category VARCHAR(100),
    priority VARCHAR(50),
    metadata JSONB,

    INDEX idx_chat_id (chat_id),
    INDEX idx_status (status),
    INDEX idx_assigned_to (assigned_to)
);
```

---

## 📝 Модель сообщений в базе (Message Storage)

### Message Entity (PostgreSQL)

```typescript
interface Message {
  id: string;               // UUID
  chatId: string;           // Ссылка на чат
  content: string;          // Текст сообщения
  sender: MessageSender;    // "user" | "ai" | "operator"
  senderName?: string;      // Имя отправителя
  timestamp: Date;          // Время отправки
  metadata?: {
    agentName?: string;     // Для AI: какой агент ответил
    confidence?: number;    // Для AI: уверенность
    isEscalated?: boolean;  // Флаг эскалации
    processingTimeMs?: number;
  };
}

enum MessageSender {
  USER = "user",
  AI = "ai",
  OPERATOR = "operator"
}
```

**SQL Schema:**

```sql
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chat_id VARCHAR(255) NOT NULL REFERENCES chats(chat_id),
    content TEXT NOT NULL,
    sender VARCHAR(50) NOT NULL,
    sender_name VARCHAR(255),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB,

    INDEX idx_chat_id (chat_id),
    INDEX idx_timestamp (timestamp)
);
```

---

## 📊 Модель кэша (Redis)

### Chat History (Redis)

**Key format:** `chat:{chatId}:messages`

**Value:** List of JSON strings

```typescript
interface CachedMessage {
  username?: string;
  message?: string;
  answer?: string;
  botUsername?: string;
  timestamp: string;        // ISO 8601
}
```

**Redis Commands:**

```bash
# Сохранение сообщения
RPUSH chat:abc123:messages '{"username":"User","message":"Hello","timestamp":"2024-10-18T10:00:00Z"}'

# Обрезка до последних 50 сообщений
LTRIM chat:abc123:messages -50 -1

# Получение истории
LRANGE chat:abc123:messages 0 -1

# TTL: 24 часа
EXPIRE chat:abc123:messages 86400
```

---

## 🗄️ Модель базы знаний (Knowledge Base)

### Knowledge Base File

**Формат:** Текстовые файлы (.txt)

```
Сеть.txt
Приложение.txt
Оборудование.txt
Доступ и пароли.txt
Безопасность.txt
```

**Структура:**

```
Параграф 1 с информацией о настройке Wi-Fi.

Параграф 2 с информацией о решении проблем с роутером.

Параграф 3 с информацией о настройке VPN.
```

### Paragraph Embeddings (ChromaDB)

**Collection:** `paragraph_embeddings`

```typescript
interface ParagraphDocument {
  id: string;               // "{agent}_{index}" - например "Сеть_0"
  document: string;         // Текст параграфа
  embedding: number[];      // Вектор 384 измерений
  metadata: {
    agent: string;          // "Сеть" | "Приложение" | ...
    index: number;          // Индекс параграфа в файле
    file_path: string;      // Путь к файлу
  };
}
```

**Пример данных:**

```json
{
  "ids": ["Сеть_0", "Сеть_1", "Приложение_0"],
  "embeddings": [
    [0.23, -0.45, 0.67, ...],  // 384-мерный вектор
    [0.12, -0.33, 0.89, ...],
    [0.45, -0.21, 0.34, ...]
  ],
  "documents": [
    "Для настройки Wi-Fi откройте Настройки > Сеть > Wi-Fi.",
    "Если роутер не отвечает, проверьте подключение кабеля.",
    "Для установки Office перейдите на portal.office.com."
  ],
  "metadatas": [
    {"agent": "Сеть", "index": 0},
    {"agent": "Сеть", "index": 1},
    {"agent": "Приложение", "index": 0}
  ]
}
```

---

## 🤖 Модель агентов (Agent Model)

### Agent Configuration

```typescript
interface AgentConfig {
  name: string;             // "Сеть" | "Приложение" | ...
  model_path: string;       // Путь к LoRA адаптеру
  tokenizer_path: string;   // Путь к токенизатору
  knowledge_base_path: string;  // Путь к базе знаний
  similarity_threshold: number; // Порог для выбора агента (0.25)
  lora_config: {
    r: number;              // Rank (64)
    lora_alpha: number;     // Alpha (128)
    lora_dropout: number;   // Dropout (0.1)
    target_modules: string[]; // ["q_proj", "k_proj", ...]
  };
}
```

**Python Implementation:**

```python
agent_map = {
    "Сеть": {
        "model": PeftModel,          # LoRA модель
        "tokenizer": PreTrainedTokenizer,
        "file_path": "Сеть.txt",
        "paragraphs": List[str],     # Кэш параграфов
        "embeddings": NDArray         # Кэш embeddings
    },
    "Приложение": { ... },
    # ...
}
```

---

## 📡 WebSocket Events (Chat Service)

### Client → Server Events

#### `joinChat`

```typescript
interface JoinChatPayload {
  chatId: string;
  username: string;
}
```

**Example:**

```javascript
socket.emit('joinChat', {
  chatId: 'chat_abc123',
  username: 'Иван Иванов'
});
```

#### `sendMessage`

```typescript
interface SendMessagePayload {
  chatId: string;
  message: string;
  username: string;
}
```

**Example:**

```javascript
socket.emit('sendMessage', {
  chatId: 'chat_abc123',
  message: 'Не работает принтер',
  username: 'Иван Иванов'
});
```

#### `leaveChat`

```typescript
interface LeaveChatPayload {
  chatId: string;
}
```

### Server → Client Events

#### `message`

```typescript
interface MessagePayload {
  chatId: string;
  message: string;
  username: string;
  timestamp: string;        // ISO 8601
  isManager?: boolean;      // Если сообщение от оператора
}
```

**Example:**

```javascript
socket.on('message', (data) => {
  console.log(data);
  // {
  //   chatId: 'chat_abc123',
  //   message: 'Проверьте, включен ли принтер',
  //   username: 'AI-помощник',
  //   timestamp: '2024-10-18T10:30:00Z'
  // }
});
```

#### `messageHistory`

```typescript
interface MessageHistoryPayload {
  messages: Array<{
    username?: string;
    message?: string;
    answer?: string;
    timestamp: string;
  }>;
}
```

**Example:**

```javascript
socket.on('messageHistory', (data) => {
  data.messages.forEach(msg => {
    // Отображение истории
  });
});
```

#### `operatorJoined`

```typescript
interface OperatorJoinedPayload {
  chatId: string;
  operatorName: string;
  operatorId: string;
}
```

#### `chatClosed`

```typescript
interface ChatClosedPayload {
  chatId: string;
  reason: string;
}
```

---

## 🔐 Модель пользователей (User Model)

### User Entity (PostgreSQL - Operator Service)

```typescript
interface User {
  id: string;               // UUID
  email: string;            // Уникальный email
  passwordHash: string;     // Хэш пароля (bcrypt)
  role: UserRole;           // "operator" | "admin" | "manager"
  name: string;             // Полное имя
  createdAt: Date;
  updatedAt: Date;
  isActive: boolean;        // Активен ли аккаунт
  metadata?: {
    department?: string;    // Отдел
    phoneNumber?: string;
    avatar?: string;        // URL аватара
  };
}

enum UserRole {
  OPERATOR = "operator",    // Оператор поддержки
  ADMIN = "admin",          // Администратор
  MANAGER = "manager"       // Менеджер
}
```

**SQL Schema:**

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB,

    INDEX idx_email (email),
    INDEX idx_role (role)
);
```

---

## 📈 Модель метрик (Metrics Model)

### Prometheus Metrics

```typescript
interface AIServiceMetrics {
  // Counters
  ai_requests_total: number;          // Общее количество запросов
  ai_agent_selection_count: {         // Счётчик выбора агентов
    [agentName: string]: number;
  };
  ai_escalations_total: number;       // Количество эскалаций

  // Histograms
  ai_response_time_seconds: {         // Время обработки
    sum: number;
    count: number;
    buckets: { [le: string]: number };
  };

  // Gauges
  ai_active_requests: number;         // Активные запросы
  ai_cache_hit_rate: number;          // Hit rate кэша
}
```

### Custom Metrics (Application Level)

```typescript
interface ApplicationMetrics {
  totalRequests: number;
  successfulResponses: number;
  escalatedRequests: number;
  averageResponseTimeMs: number;
  agentUsageStats: {
    [agentName: string]: {
      count: number;
      avgConfidence: number;
      avgContextSimilarity: number;
    };
  };
  cacheStats: {
    hits: number;
    misses: number;
    hitRate: number;
  };
}
```

---

## 🔄 Модель действий (Action Model)

### User Action Log

```typescript
interface UserAction {
  id: string;               // UUID
  userId?: string;          // ID пользователя (если есть)
  chatId: string;           // ID чата
  action: ActionType;       // Тип действия
  timestamp: Date;
  metadata: {
    page?: string;          // Страница, где произошло действие
    userAgent?: string;
    ipAddress?: string;
  };
}

enum ActionType {
  CHAT_OPENED = "chat_opened",
  MESSAGE_SENT = "message_sent",
  FEEDBACK_GIVEN = "feedback_given",
  CHAT_CLOSED = "chat_closed",
  OPERATOR_REQUESTED = "operator_requested"
}
```

---

## 📦 Модель конфигурации (Configuration Model)

### System Configuration

```typescript
interface SystemConfig {
  ai: {
    model: {
      name: string;         // "t-tech/T-lite-it-1.0"
      quantization: string; // "4bit" | "8bit" | "fp16"
      device: string;       // "cuda" | "cpu"
      max_tokens: number;   // 8192
    };
    rag: {
      similarity_threshold: number;     // 0.25
      context_relevance_threshold: number; // 0.5
      max_context_tokens: number;       // 2000
    };
    agents: {
      [agentName: string]: {
        lora_path: string;
        knowledge_base: string;
        enabled: boolean;
      };
    };
  };

  rabbitmq: {
    host: string;
    queues: {
      ai_requests: string;
      ai_response: string;
      db_messages: string;
    };
  };

  redis: {
    host: string;
    port: number;
    max_messages_per_chat: number;    // 50
    ttl_hours: number;                // 24
  };

  chromadb: {
    host: string;
    port: number;
    collection_name: string;          // "paragraph_embeddings"
  };
}
```

---

## 🧪 Примеры использования

### Пример 1: Создание нового чата

```typescript
// 1. Создание записи в БД
const chat = await db.chats.create({
  chatId: generateChatId(),
  status: ChatStatus.ACTIVE,
  metadata: {
    source: "widget",
    initialQuery: "Привет"
  }
});

// 2. Инициализация в Redis
await redis.rpush(
  `chat:${chat.chatId}:messages`,
  JSON.stringify({
    username: "Пользователь",
    message: "Привет",
    timestamp: new Date().toISOString()
  })
);

// 3. Отправка в RabbitMQ
await rabbitmq.publish('ai_requests', {
  chatId: chat.chatId,
  message: "Привет",
  username: "Пользователь",
  messageHistory: []
});
```

### Пример 2: Обработка ответа AI

```typescript
// Получение из RabbitMQ
rabbitmq.consume('ai_response', async (msg) => {
  const response: AIResponse = JSON.parse(msg.content);

  // Сохранение в Redis
  await redis.rpush(
    `chat:${response.chatId}:messages`,
    JSON.stringify({
      answer: response.answer,
      botUsername: response.botUsername,
      timestamp: new Date().toISOString()
    })
  );

  // Обрезка до 50 последних сообщений
  await redis.ltrim(`chat:${response.chatId}:messages`, -50, -1);

  // Если эскалация - обновить статус чата
  if (response.isManager) {
    await db.chats.update(
      { chatId: response.chatId },
      { status: ChatStatus.WAITING }
    );
  }

  // Отправка через WebSocket
  io.to(response.chatId).emit('message', {
    chatId: response.chatId,
    message: response.answer,
    username: response.botUsername,
    timestamp: new Date().toISOString()
  });
});
```

---

## 📚 Валидация данных

### Zod Schemas (TypeScript)

```typescript
import { z } from 'zod';

export const AIRequestSchema = z.object({
  chatId: z.string().min(1),
  message: z.string().min(1).max(2000),
  username: z.string().optional(),
  messageHistory: z.array(z.union([
    z.object({
      username: z.string(),
      message: z.string()
    }),
    z.object({
      answer: z.string(),
      botUsername: z.string().optional()
    })
  ])),
  metadata: z.object({
    timestamp: z.string().optional(),
    source: z.string().optional(),
    userId: z.string().optional()
  }).optional()
});

export const AIResponseSchema = z.object({
  chatId: z.string(),
  answer: z.string(),
  botUsername: z.string(),
  isManager: z.boolean(),
  metadata: z.object({
    agent: z.string().optional(),
    confidence: z.number().min(0).max(1).optional(),
    context_similarity: z.number().min(0).max(1).optional(),
    processing_time_ms: z.number().optional(),
    timestamp: z.string().optional()
  }).optional()
});
```

### Pydantic Models (Python)

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Union
from datetime import datetime

class UserHistoryItem(BaseModel):
    username: str
    message: str
    timestamp: Optional[datetime] = None

class AIHistoryItem(BaseModel):
    answer: str
    botUsername: Optional[str] = "AI-помощник"
    timestamp: Optional[datetime] = None

class AIRequest(BaseModel):
    chatId: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1, max_length=2000)
    username: Optional[str] = "Пользователь"
    messageHistory: List[Union[UserHistoryItem, AIHistoryItem]] = []

class AIResponse(BaseModel):
    chatId: str
    answer: str
    botUsername: str = "AI-помощник"
    isManager: bool = False
```

---

**Последнее обновление:** 2024-10-18
**Версия:** 1.0
