# AI Support System - Мультиагентная система технической поддержки

**Интеллектуальная система технической поддержки на базе RAG (Retrieval-Augmented Generation) и мультиагентной архитектуры**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-required-blue.svg)](https://www.docker.com/)

---

## 📋 Содержание

- [Быстрый старт](#-быстрый-старт-за-5-минут)
- [Архитектура системы](#-архитектура-системы)
- [Компоненты](#-компоненты)
- [API и интерфейсы](#-api-и-интерфейсы)
- [Типовые запросы](#-типовые-запросы)
- [Документация](#-документация)
- [Разработка](#-разработка)

---

## 🚀 Быстрый старт за 5 минут

### Предварительные требования

- Docker и Docker Compose установлены
- NVIDIA GPU с CUDA 11.0+ (для AI-сервиса)
- Минимум 16GB RAM
- 50GB свободного места на диске

### Шаг 1: Клонирование репозитория

```bash
git clone <repository-url>
cd Hakaton
```

### Шаг 2: Подготовка AI-модели

```bash
# Убедитесь, что модель Qwen2-7B уже квантизирована и находится в:
# backend/ai-service/quantized_model/
# backend/ai-service/frida_embedding_model/

# Проверьте наличие обученных LoRA адаптеров для каждого агента:
ls backend/ai-service/Сеть/best_model/
ls backend/ai-service/Приложение/best_model/
ls backend/ai-service/Оборудование/best_model/
ls backend/ai-service/Доступ\ и\ пароли/best_model/
ls backend/ai-service/Безопасность/best_model/
```

### Шаг 3: Запуск всех сервисов

```bash
cd backend
docker-compose up -d
```

### Шаг 4: Проверка запуска

```bash
# Проверка статуса всех сервисов
docker-compose ps

# Проверка логов AI-сервиса
docker-compose logs -f ai-service

# Ожидаемый вывод:
# "Коллекция paragraph_embeddings найдена в ChromaDB."
# "Ожидание сообщений из RabbitMQ. Для выхода нажмите CTRL+C"
```

### Шаг 5: Доступ к интерфейсам

| Сервис | URL | Описание |
|--------|-----|----------|
| **Виджет чата** | http://localhost:8000/widget | Пользовательский интерфейс чата |
| **Admin Console** | http://localhost:5173 | Консоль оператора |
| **API Gateway (Kong)** | http://localhost:8000 | Точка входа для всех API |
| **RabbitMQ Management** | http://localhost:15672 | Мониторинг очередей (guest/guest) |
| **Grafana** | http://localhost:3000 | Метрики и дашборды (admin/admin) |
| **Prometheus** | http://localhost:9090 | Сбор метрик |
| **ChromaDB** | http://localhost:8002 | Векторная база данных |

### Шаг 6: Тестирование

```bash
# Откройте браузер и перейдите на:
http://localhost:8000/widget

# Отправьте тестовый запрос:
"Привет! Помоги настроить Wi-Fi"

# Ожидаемый ответ от агента "Сеть":
"Для настройки Wi-Fi выполните следующие действия: [инструкция из базы знаний]"
```

---

## 🏗️ Архитектура системы

### Общая схема

```mermaid
graph TB
    subgraph "Внешний слой"
        USER[👤 Пользователь]
        OPERATOR[👨‍💼 Оператор]
        WIDGET[🖥️ Chat Widget]
        ADMIN[🛠️ Admin Console]
    end

    subgraph "API Gateway Layer"
        KONG[Kong API Gateway<br/>:8000]
        CORS[CORS Plugin]
        AUTH[JWT Auth Plugin]
    end

    subgraph "Application Layer"
        CHAT[Chat Service<br/>NestJS + Socket.IO<br/>:3001]
        OPERATOR_SVC[Operator Service<br/>Go + PostgreSQL<br/>:8080]
    end

    subgraph "Message Queue Layer"
        RMQ[RabbitMQ<br/>:5672]
        Q1[Queue: ai_requests]
        Q2[Queue: ai_response]
        Q3[Queue: db_messages]
    end

    subgraph "AI Processing Layer"
        AI_SVC[AI Service<br/>Python + PyTorch]
        ORCHESTRATOR[Orchestrator<br/>process_query]
        AGENT_SELECTOR[Agent Selector<br/>Embedding-based]
    end

    subgraph "Multi-Agent System"
        AGENT1[🌐 Агент: Сеть<br/>LoRA Adapter]
        AGENT2[💻 Агент: Приложение<br/>LoRA Adapter]
        AGENT3[🔧 Агент: Оборудование<br/>LoRA Adapter]
        AGENT4[🔑 Агент: Доступ<br/>LoRA Adapter]
        AGENT5[🛡️ Агент: Безопасность<br/>LoRA Adapter]
    end

    subgraph "Knowledge Base"
        CHROMA[ChromaDB<br/>Vector Database<br/>:8002]
        KB1[Сеть.txt<br/>Embeddings]
        KB2[Приложение.txt<br/>Embeddings]
        KB3[Оборудование.txt<br/>Embeddings]
        KB4[Доступ.txt<br/>Embeddings]
        KB5[Безопасность.txt<br/>Embeddings]
    end

    subgraph "Foundation Models"
        LLM[Qwen2-7B<br/>4-bit quantized<br/>~4GB VRAM]
        EMB[Sentence-BERT<br/>Embedding Model<br/>frida]
    end

    subgraph "Infrastructure"
        REDIS[(Redis<br/>Cache + Sessions)]
        POSTGRES[(PostgreSQL<br/>User Data)]
        PROMETHEUS[Prometheus<br/>Metrics]
        GRAFANA[Grafana<br/>Dashboards]
        LOKI[Loki + Promtail<br/>Logs]
    end

    USER --> WIDGET
    OPERATOR --> ADMIN
    WIDGET --> KONG
    ADMIN --> KONG

    KONG --> CHAT
    KONG --> OPERATOR_SVC

    CHAT --> RMQ
    CHAT --> REDIS

    RMQ --> Q1
    RMQ --> Q2
    RMQ --> Q3

    Q1 --> AI_SVC
    AI_SVC --> Q2
    Q3 --> OPERATOR_SVC

    AI_SVC --> ORCHESTRATOR
    ORCHESTRATOR --> AGENT_SELECTOR

    AGENT_SELECTOR --> AGENT1
    AGENT_SELECTOR --> AGENT2
    AGENT_SELECTOR --> AGENT3
    AGENT_SELECTOR --> AGENT4
    AGENT_SELECTOR --> AGENT5

    AGENT1 --> CHROMA
    AGENT2 --> CHROMA
    AGENT3 --> CHROMA
    AGENT4 --> CHROMA
    AGENT5 --> CHROMA

    CHROMA --> KB1
    CHROMA --> KB2
    CHROMA --> KB3
    CHROMA --> KB4
    CHROMA --> KB5

    AGENT1 --> LLM
    AGENT2 --> LLM
    AGENT3 --> LLM
    AGENT4 --> LLM
    AGENT5 --> LLM

    AGENT_SELECTOR --> EMB

    OPERATOR_SVC --> POSTGRES
    AI_SVC --> PROMETHEUS
    CHAT --> PROMETHEUS
    PROMETHEUS --> GRAFANA
    AI_SVC --> LOKI

    style AI_SVC fill:#4CAF50,color:#fff
    style ORCHESTRATOR fill:#2196F3,color:#fff
    style CHROMA fill:#FF9800,color:#fff
    style LLM fill:#9C27B0,color:#fff
    style KONG fill:#00ACC1,color:#fff
```

### Потоки данных

#### 1️⃣ Обработка пользовательского запроса

```mermaid
sequenceDiagram
    participant User as 👤 Пользователь
    participant Widget as Chat Widget
    participant Kong as API Gateway
    participant Chat as Chat Service
    participant RMQ as RabbitMQ
    participant AI as AI Service
    participant Chroma as ChromaDB
    participant LLM as Qwen2-7B

    User->>Widget: Отправка сообщения
    Widget->>Kong: WebSocket (Socket.IO)
    Kong->>Chat: Передача через proxy
    Chat->>RMQ: Публикация в ai_requests

    RMQ->>AI: Получение из очереди
    AI->>AI: Выбор агента (embedding similarity)
    AI->>Chroma: Поиск релевантного контекста
    Chroma-->>AI: Возврат параграфов (top-1)
    AI->>LLM: Генерация с LoRA адаптером
    LLM-->>AI: Сгенерированный ответ
    AI->>AI: Валидация (similarity check)
    AI->>RMQ: Публикация в ai_response

    RMQ->>Chat: Получение ответа
    Chat->>Widget: WebSocket emit
    Widget->>User: Отображение ответа
```

#### 2️⃣ Эскалация к оператору

```mermaid
sequenceDiagram
    participant User as 👤 Пользователь
    participant AI as AI Service
    participant Chat as Chat Service
    participant Operator as 👨‍💼 Оператор

    User->>AI: Запрос (низкая релевантность)
    AI->>AI: similarity < 0.5
    AI->>Chat: isManager = true
    Chat->>Operator: Уведомление о новом чате
    Operator->>Chat: Принятие чата
    Chat->>User: "Запрос передан специалисту"
```

---

## 🧩 Компоненты

### 1. AI Service (Python)

**Локация:** `backend/ai-service/`

**Назначение:** Ядро мультиагентной системы с RAG

**Основные файлы:**
- `model.py` - Оркестратор и RAG pipeline
- `lora.py` - Дообучение LoRA адаптеров
- `ARCHITECTURE.md` - Детальная архитектура

**Технологии:**
- PyTorch + Transformers
- PEFT (LoRA)
- Sentence-Transformers
- ChromaDB
- RabbitMQ (pika)

**Потребление ресурсов:**
- GPU: ~4-5GB VRAM (4-bit quantization)
- RAM: ~8GB
- CPU: 4 cores

### 2. Chat Service (NestJS)

**Локация:** `backend/chat-service/`

**Назначение:** WebSocket сервер для real-time общения

**Основные файлы:**
- `src/chat.gateway.ts` - Socket.IO gateway
- `src/rabbitmq.service.ts` - Интеграция с RabbitMQ
- `src/redis.service.ts` - Кэширование истории

**Технологии:**
- NestJS
- Socket.IO
- RabbitMQ
- Redis

### 3. Operator Service (Go)

**Локация:** `backend/operator-service/`

**Назначение:** Управление операторами и чатами

**Технологии:**
- Go (Fiber framework)
- PostgreSQL
- JWT Authentication

### 4. ChromaDB

**Назначение:** Векторное хранилище для embeddings параграфов

**Данные:**
- 5 коллекций (по одной на агента)
- ~1000-1500 параграфов
- Персистентное хранилище в Docker volume

### 5. Kong API Gateway

**Назначение:** Единая точка входа, маршрутизация, CORS

**Конфигурация:**
- Routes для `/widget`, `/api/chat`, `/socket.io`
- CORS plugin для cross-origin запросов
- JWT plugin для защищённых endpoints

---

## 📡 API и интерфейсы

### WebSocket API (Chat Service)

**Подключение:**
```javascript
const socket = io('http://localhost:8000', {
  path: '/socket.io',
  transports: ['websocket', 'polling']
});
```

**События:**

#### `joinChat` - Присоединение к чату
```javascript
socket.emit('joinChat', {
  chatId: 'unique-chat-id',
  username: 'Пользователь'
});
```

#### `sendMessage` - Отправка сообщения
```javascript
socket.emit('sendMessage', {
  chatId: 'unique-chat-id',
  message: 'Как настроить Wi-Fi?',
  username: 'Пользователь'
});
```

#### `message` - Получение сообщения
```javascript
socket.on('message', (data) => {
  console.log(data);
  // {
  //   chatId: 'unique-chat-id',
  //   message: 'Для настройки Wi-Fi...',
  //   username: 'AI-помощник',
  //   timestamp: '2024-10-18T10:30:00Z'
  // }
});
```

#### `messageHistory` - История сообщений
```javascript
socket.on('messageHistory', (messages) => {
  console.log(messages);
  // Array of messages
});
```

### RabbitMQ Message Format

#### Очередь: `ai_requests`
```json
{
  "chatId": "unique-chat-id",
  "message": "Как сбросить пароль?",
  "username": "Пользователь",
  "messageHistory": [
    {
      "username": "Пользователь",
      "message": "Привет"
    },
    {
      "answer": "Здравствуйте! Чем могу помочь?"
    }
  ]
}
```

#### Очередь: `ai_response`
```json
{
  "chatId": "unique-chat-id",
  "answer": "Для сброса пароля обратитесь к администратору.",
  "botUsername": "AI-помощник",
  "isManager": false
}
```

### REST API (Operator Service)

**Base URL:** `http://localhost:8000/api`

#### Authentication
```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "operator@example.com",
  "password": "password123"
}

Response:
{
  "token": "jwt-token-here",
  "user": {
    "id": "user-id",
    "email": "operator@example.com",
    "role": "operator"
  }
}
```

#### Get Active Chats
```http
GET /api/chats
Authorization: Bearer {jwt-token}

Response:
{
  "chats": [
    {
      "chatId": "unique-chat-id",
      "status": "active",
      "lastMessage": "Как настроить принтер?",
      "timestamp": "2024-10-18T10:30:00Z"
    }
  ]
}
```

---

## 💬 Типовые запросы

### 1. Сетевые проблемы (Агент: Сеть)

```
Пользователь: "Не работает интернет, что делать?"

AI-помощник: "Проверьте подключение кабеля Ethernet к компьютеру и роутеру,
убедитесь, что индикаторы на роутере горят зелёным цветом."
```

```
Пользователь: "Как настроить Wi-Fi на ноутбуке?"

AI-помощник: "Откройте настройки сети, выберите доступную сеть Wi-Fi,
введите пароль и нажмите 'Подключить'."
```

### 2. Проблемы с приложениями (Агент: Приложение)

```
Пользователь: "Не могу открыть документ в Word"

AI-помощник: "Убедитесь, что Microsoft Office установлен и активирован.
Попробуйте открыть файл от имени администратора."
```

```
Пользователь: "Outlook не отправляет письма"

AI-помощник: "Проверьте настройки исходящего сервера SMTP и убедитесь,
что указан правильный порт (обычно 587 или 465)."
```

### 3. Проблемы с оборудованием (Агент: Оборудование)

```
Пользователь: "Принтер не печатает"

AI-помощник: "Проверьте, что принтер включен, подключен к сети,
и в нём есть бумага и достаточно тонера."
```

### 4. Доступ и пароли (Агент: Доступ и пароли)

```
Пользователь: "Забыл пароль от рабочего компьютера"

AI-помощник: "Для сброса пароля обратитесь к системному администратору
или в службу поддержки IT-отдела."
```

### 5. Безопасность (Агент: Безопасность)

```
Пользователь: "Получил подозрительное письмо с вложением"

AI-помощник: "Не открывайте вложения от неизвестных отправителей.
Переместите письмо в спам и сообщите в отдел безопасности."
```

### 6. Общение (Базовая модель без агента)

```
Пользователь: "Привет!"

AI-помощник: "Здравствуйте! Я AI-помощник технической поддержки.
Чем могу помочь?"
```

```
Пользователь: "Спасибо за помощь!"

AI-помощник: "Рад был помочь! Обращайтесь, если возникнут ещё вопросы."
```

### 7. Эскалация к оператору

```
Пользователь: "Мой компьютер издаёт странные звуки и греется"

AI-помощник: "Запрос передан специалисту. Пожалуйста, подождите."
[isManager = true → чат передаётся оператору]
```

---

## 📚 Документация

Подробная документация находится в директории `docs/`:

1. **[COMPONENT_DIAGRAM.md](docs/COMPONENT_DIAGRAM.md)** - Детальная диаграмма компонентов
2. **[MODEL_SELECTION.md](docs/MODEL_SELECTION.md)** - Обоснование выбора модели
3. **[MCP_TOOLS_SPEC.md](docs/MCP_TOOLS_SPEC.md)** - Спецификация MCP-инструментов
4. **[DATA_MODELS.md](docs/DATA_MODELS.md)** - Модели данных и контракты
5. **[API_REFERENCE.md](docs/API_REFERENCE.md)** - Полная справка по API
6. **[DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Инструкции по развертыванию

---

## 🛠️ Разработка

### Структура проекта

```
Hakaton/
├── backend/
│   ├── ai-service/              # AI мультиагентная система
│   │   ├── model.py            # Оркестратор и RAG
│   │   ├── lora.py             # Обучение LoRA
│   │   ├── quantized_model/    # Базовая модель Qwen2-7B
│   │   ├── frida_embedding_model/  # Embedding модель
│   │   ├── Сеть/               # LoRA адаптер "Сеть"
│   │   ├── Приложение/         # LoRA адаптер "Приложение"
│   │   ├── Оборудование/       # LoRA адаптер "Оборудование"
│   │   ├── Доступ и пароли/    # LoRA адаптер "Доступ"
│   │   ├── Безопасность/       # LoRA адаптер "Безопасность"
│   │   ├── Сеть.txt           # База знаний: Сеть
│   │   ├── Приложение.txt     # База знаний: Приложения
│   │   ├── Оборудование.txt   # База знаний: Оборудование
│   │   ├── Доступ и пароли.txt # База знаний: Доступ
│   │   ├── Безопасность.txt   # База знаний: Безопасность
│   │   ├── ARCHITECTURE.md     # Архитектура AI-сервиса
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── chat-service/           # NestJS WebSocket сервис
│   │   ├── src/
│   │   │   ├── chat.gateway.ts
│   │   │   ├── rabbitmq.service.ts
│   │   │   └── redis.service.ts
│   │   └── package.json
│   ├── operator-service/       # Go сервис операторов
│   │   ├── main.go
│   │   └── migrations/
│   └── docker-compose.yml      # Оркестрация всех сервисов
├── frontend/
│   ├── hakaton-frontend/       # Chat Widget (React)
│   └── ac-frontend/            # Admin Console (React)
├── docs/                       # Документация
└── README.md                   # Этот файл
```

### Локальная разработка AI-сервиса

```bash
# Создание виртуального окружения
cd backend/ai-service
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Установка зависимостей
pip install -r requirements.txt

# Запуск локально (требует RabbitMQ и ChromaDB)
export RABBITMQ_HOST=localhost
export QUEUE_IN=ai_requests
export QUEUE_OUT=ai_response
export CHROMADB_HOST=localhost
export CHROMADB_PORT=8002

python model.py
```

### Дообучение нового агента

```bash
# 1. Создайте файл базы знаний: НовыйАгент.txt
# 2. Обновите agent_map в model.py
# 3. Запустите обучение LoRA:

python lora.py  # Измените file_path на НовыйАгент.txt
```

### Мониторинг и отладка

```bash
# Логи всех сервисов
docker-compose logs -f

# Логи конкретного сервиса
docker-compose logs -f ai-service

# Метрики в Prometheus
open http://localhost:9090

# Дашборды в Grafana
open http://localhost:3000

# RabbitMQ Management
open http://localhost:15672
```

---

## 🔧 Конфигурация

### Переменные окружения

#### AI Service
```env
RABBITMQ_HOST=rabbitmq
QUEUE_IN=ai_requests
QUEUE_OUT=ai_response
CHROMADB_HOST=chromadb
CHROMADB_PORT=8000
```

#### Chat Service
```env
PORT=3001
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672
REDIS_URL=redis://redis:6379
REDIS_MAX_MESSAGES=50
```

#### Operator Service
```env
POSTGRES_HOST=operator-db
POSTGRES_USER=operator_service
POSTGRES_PASSWORD=operator_password
POSTGRES_DB=operator_db
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672
RABBITMQ_QUEUE=db_messages
```

---

## 📊 Метрики и мониторинг

### Доступные метрики (Prometheus)

- `ai_requests_total` - Общее количество запросов
- `ai_response_time_seconds` - Время обработки запросов
- `ai_agent_selection_count` - Счётчик выбора агентов
- `ai_escalations_total` - Количество эскалаций к оператору
- `chat_active_connections` - Активные WebSocket соединения
- `rabbitmq_messages_in_queue` - Сообщения в очередях

### Grafana Dashboards

1. **AI Service Overview** - Общие метрики AI-сервиса
2. **RabbitMQ Monitoring** - Состояние очередей
3. **Chat Service** - WebSocket соединения и throughput
4. **System Resources** - CPU, RAM, GPU utilization

---

## 🐛 Известные проблемы и решения

### Проблема: AI-сервис не запускается (CUDA out of memory)

**Решение:**
```bash
# Уменьшите batch size или используйте CPU fallback
# В model.py измените:
device = "cpu"  # Вместо "cuda"
```

### Проблема: ChromaDB connection refused

**Решение:**
```bash
# Убедитесь, что ChromaDB запущен и доступен
docker-compose up -d chromadb
docker-compose logs chromadb

# Проверьте healthcheck
curl http://localhost:8002/api/v2/heartbeat
```

### Проблема: RabbitMQ очереди не создаются

**Решение:**
```bash
# Пересоздайте очереди вручную
docker-compose up rabbitmq-setup --force-recreate
```

---

## 📝 Лицензия

MIT License - см. [LICENSE](LICENSE)

---

## 👥 Команда

Разработано для хакатона 2024

---

## 🙏 Благодарности

- [Qwen2](https://github.com/QwenLM/Qwen2) - Базовая языковая модель
- [ChromaDB](https://www.trychroma.com/) - Векторная база данных
- [LangChain](https://www.langchain.com/) - RAG framework
- [Hugging Face](https://huggingface.co/) - Transformers и PEFT

---

**Последнее обновление:** 2024-10-18
