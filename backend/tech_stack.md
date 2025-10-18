# ТЕХНОЛОГИЧЕСКИЙ СТЕК
## AI-виджет с мультиагентной системой

---

## 1️⃣ БЭКЕНД

### Chat Service
- **NestJS** 11 + **TypeScript** 5.7
- **Socket.IO** 4.8 - реал-тайм WebSocket
- **Express** - HTTP сервер
- **ioredis** - Redis клиент

### Operator Service
- **Go** 1.24.3
- **Gin** 1.11 - HTTP фреймворк
- **GORM** - ORM для PostgreSQL
- **JWT** + **bcrypt** - аутентификация

### AI Service
- **Python** 3.x + **PyTorch** 2.0+
- **Transformers** - LLM модели
- **PEFT** - LoRA адаптеры (5 агентов)
- **LangChain** - RAG оркестрация
- **Sentence Transformers** - embeddings
- **Razdel** - русскоязычная NLP

### Базы данных
- **PostgreSQL** 13 - основная БД
- **Redis** 6.2 - кэш и состояние
- **ChromaDB** 0.5 - векторная БД для RAG

---

## 2️⃣ ФРОНТЕНД

### Widget (Встраиваемый виджет)
- **Vanilla JavaScript** ES6+
- **HTML5** + **CSS3**
- **Socket.IO Client** - WebSocket
- **Express** 5.1 - файловый сервер

### Admin Console
- **React** 19 + **TypeScript** 5.9
- **Vite** 7.1 - сборщик
- **Tailwind CSS** 4.1 - стилизация
- **React Router** 7.9 - роутинг
- **Socket.IO Client** 4.5 - WebSocket

---

## 3️⃣ АНАЛИТИКА И МОНИТОРИНГ

### Метрики
- **Prometheus** 2.42 - сбор метрик
- **Grafana** 8.5 - визуализация дашбордов

### Логирование
- **Loki** 2.5 - хранилище логов
- **Promtail** 2.5 - агент сбора логов

---

## 4️⃣ ИНФРАСТРУКТУРА

### Message Broker
- **RabbitMQ** 3.12 - очереди сообщений
  - ai_requests
  - ai_response
  - db_messages

### API Gateway
- **Kong** 3.6 - маршрутизация, безопасность, CORS
- Кастомный плагин: widget-domain-check

### Контейнеризация
- **Docker** + **Docker Compose**
- **NVIDIA GPU** support (опционально)

---

## 📊 КРАТКАЯ СТАТИСТИКА

**Языки:** TypeScript, Go, Python, JavaScript
**Микросервисы:** 3 (Chat, Operator, AI)
**Базы данных:** 3 (PostgreSQL, Redis, ChromaDB)
**AI модели:** 1 LLM + 5 LoRA адаптеров + 1 embedding
**Контейнеры:** 9 production сервисов
