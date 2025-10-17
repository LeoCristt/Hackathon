# Инструкция по развертыванию AI Service

## Структура репозиториев

- **GitHub**: Весь код проекта (кроме больших файлов моделей)
- **Hugging Face**: Все AI модели в одном репозитории

## 1. Загрузка моделей на Hugging Face

### Шаг 1: Создайте аккаунт и токен на Hugging Face

1. Зарегистрируйтесь на https://huggingface.co
2. Перейдите в https://huggingface.co/settings/tokens
3. Создайте новый токен с правами записи (write)
4. Сохраните токен в безопасном месте

### Шаг 2: Создайте репозиторий для моделей

1. Перейдите на https://huggingface.co/new
2. Создайте новый репозиторий, например: `your-username/ai-service-models`
3. Выберите тип: Model

### Шаг 3: Установите Hugging Face CLI

```bash
pip install huggingface-hub
```

### Шаг 4: Войдите в систему

```bash
huggingface-cli login
```

Введите ваш токен доступа.

### Шаг 5: Загрузите модели

Из директории `backend/ai-service` выполните:

```bash
# Загрузка всех моделей в репозиторий
huggingface-cli upload your-username/ai-service-models ./quantized_model quantized_model
huggingface-cli upload your-username/ai-service-models ./frida_embedding_model frida_embedding_model
huggingface-cli upload your-username/ai-service-models "./Сеть/best_model" "Сеть/best_model"
huggingface-cli upload your-username/ai-service-models "./Приложение/best_model" "Приложение/best_model"
huggingface-cli upload your-username/ai-service-models "./Оборудование/best_model" "Оборудование/best_model"
huggingface-cli upload your-username/ai-service-models "./Доступ и пароли/best_model" "Доступ и пароли/best_model"
huggingface-cli upload your-username/ai-service-models "./Безопастность/best_model" "Безопастность/best_model"
```

**Примечание**: Загрузка ~8.5GB может занять продолжительное время в зависимости от скорости интернета.

## 2. Настройка проекта

### Шаг 1: Создайте файл .env

Скопируйте `.env.example` в `.env`:

```bash
cd backend/ai-service
cp .env.example .env
```

### Шаг 2: Заполните переменные окружения

Откройте `.env` и укажите:

```env
HF_TOKEN=your_actual_token_here
HF_MODELS_REPO=your-username/ai-service-models
RABBITMQ_HOST=localhost
QUEUE_IN=ai_requests
QUEUE_OUT=ai_responses
```

### Шаг 3: Установите зависимости

```bash
pip install -r requirements.txt
```

## 3. Запуск сервиса

При первом запуске модели автоматически загрузятся с Hugging Face:

```bash
python model.py
```

Модели будут сохранены локально в соответствующие папки и при следующих запусках загружаться не будут.

## 4. Git коммиты

Большие файлы моделей исключены из Git через `.gitignore`. Теперь можно безопасно делать коммиты:

```bash
git add .
git commit -m "Update AI service configuration"
git push
```

## 5. Развертывание на сервере

На сервере выполните:

```bash
# Клонируйте репозиторий
git clone https://github.com/your-username/Hakaton.git
cd Hakaton/backend/ai-service

# Создайте .env файл с вашими настройками
nano .env

# Установите зависимости
pip install -r requirements.txt

# Запустите сервис
python model.py
```

При первом запуске модели автоматически загрузятся с Hugging Face.

## Структура репозитория на Hugging Face

После загрузки ваш репозиторий на HF будет иметь структуру:

```
your-username/ai-service-models/
├── quantized_model/
│   ├── config.json
│   ├── model-00001-of-00002.safetensors
│   ├── model-00002-of-00002.safetensors
│   └── ...
├── frida_embedding_model/
│   ├── config.json
│   ├── model.safetensors
│   └── ...
├── Сеть/
│   └── best_model/
│       ├── adapter_config.json
│       ├── adapter_model.safetensors
│       └── ...
├── Приложение/best_model/...
├── Оборудование/best_model/...
├── Доступ и пароли/best_model/...
└── Безопастность/best_model/...
```

## Troubleshooting

### Ошибка "401 Unauthorized"
- Проверьте правильность токена HF_TOKEN
- Убедитесь, что токен имеет права на чтение (read) репозитория

### Модели не загружаются
- Проверьте название репозитория HF_MODELS_REPO
- Убедитесь в наличии интернет-соединения
- Проверьте, что репозиторий публичный или токен имеет доступ

### Нехватка места на диске
- Модели занимают ~8.5GB при локальной загрузке
- Убедитесь в наличии достаточного свободного места
