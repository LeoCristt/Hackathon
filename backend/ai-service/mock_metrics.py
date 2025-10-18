"""
Mock-сервис для генерации тестовых метрик AI-сервиса
Этот скрипт генерирует реалистичные метрики для демонстрации в Grafana
"""

from prometheus_client import Counter, Histogram, Gauge, start_http_server
import random
import time
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Метрики для запросов
ai_requests_total = Counter(
    'ai_requests_total',
    'Общее количество обработанных запросов',
    ['agent', 'status']
)

ai_request_duration_seconds = Histogram(
    'ai_request_duration_seconds',
    'Время обработки запроса в секундах',
    ['agent'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0)
)

# Метрики для токенов
ai_tokens_used = Histogram(
    'ai_tokens_used',
    'Количество использованных токенов',
    ['token_type'],
    buckets=(10, 50, 100, 200, 500, 1000, 2000, 4000, 8000)
)

# Метрики для агентов
ai_agent_selection_similarity = Histogram(
    'ai_agent_selection_similarity',
    'Схожесть запроса с выбранным агентом',
    ['agent'],
    buckets=(0.25, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 1.0)
)

ai_context_similarity = Histogram(
    'ai_context_similarity',
    'Схожесть ответа с контекстом',
    buckets=(0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)
)

# Метрики для специальных случаев
ai_special_cases_total = Counter(
    'ai_special_cases_total',
    'Количество специальных случаев',
    ['case_type']
)

# Метрики для активных чатов
ai_active_chats = Gauge(
    'ai_active_chats',
    'Количество активных чатов'
)

# Метрики для истории
ai_history_truncation_total = Counter(
    'ai_history_truncation_total',
    'Количество случаев обрезки истории'
)

# Конфигурация для генерации данных
AGENTS = ['Сеть', 'Приложение', 'Оборудование', 'Доступ и пароли', 'Безопасность']
STATUSES = ['success', 'error', 'escalated']
TOKEN_TYPES = ['prompt', 'context', 'history', 'total']
CASE_TYPES = ['greeting', 'profanity', 'escalation', 'no_context', 'low_similarity']

# Вес для статусов (больше успешных запросов)
STATUS_WEIGHTS = [0.85, 0.05, 0.10]  # success, error, escalated

# Вес для агентов (разное распределение популярности)
AGENT_WEIGHTS = [0.30, 0.25, 0.20, 0.15, 0.10]

def generate_realistic_metrics():
    """Генерирует реалистичные метрики для одного запроса"""

    # Выбираем агента с весами
    agent = random.choices(AGENTS, weights=AGENT_WEIGHTS, k=1)[0]
    status = random.choices(STATUSES, weights=STATUS_WEIGHTS, k=1)[0]

    # Увеличиваем счетчик запросов
    ai_requests_total.labels(agent=agent, status=status).inc()

    # Генерируем реалистичное время обработки
    # Успешные запросы обычно быстрее
    if status == 'success':
        duration = random.gauss(2.5, 1.0)  # среднее 2.5 сек, std 1.0
        duration = max(0.5, min(10.0, duration))  # ограничиваем диапазон
    elif status == 'error':
        duration = random.gauss(1.0, 0.5)  # ошибки быстрее
        duration = max(0.1, min(3.0, duration))
    else:  # escalated
        duration = random.gauss(0.8, 0.3)
        duration = max(0.3, min(2.0, duration))

    ai_request_duration_seconds.labels(agent=agent).observe(duration)

    # Генерируем метрики токенов (только для успешных запросов)
    if status == 'success':
        prompt_tokens = int(random.gauss(150, 50))
        prompt_tokens = max(50, min(500, prompt_tokens))

        context_tokens = int(random.gauss(300, 100))
        context_tokens = max(100, min(800, context_tokens))

        history_tokens = int(random.gauss(200, 80))
        history_tokens = max(50, min(600, history_tokens))

        total_tokens = prompt_tokens + context_tokens + history_tokens

        ai_tokens_used.labels(token_type='prompt').observe(prompt_tokens)
        ai_tokens_used.labels(token_type='context').observe(context_tokens)
        ai_tokens_used.labels(token_type='history').observe(history_tokens)
        ai_tokens_used.labels(token_type='total').observe(total_tokens)

    # Генерируем схожесть с агентом (обычно высокая)
    agent_similarity = random.gauss(0.75, 0.15)
    agent_similarity = max(0.3, min(1.0, agent_similarity))
    ai_agent_selection_similarity.labels(agent=agent).observe(agent_similarity)

    # Генерируем схожесть контекста (для успешных запросов выше)
    if status == 'success':
        context_sim = random.gauss(0.75, 0.10)
        context_sim = max(0.5, min(1.0, context_sim))
    else:
        context_sim = random.gauss(0.45, 0.15)
        context_sim = max(0.3, min(0.65, context_sim))

    ai_context_similarity.observe(context_sim)

    # Иногда генерируем специальные случаи
    if random.random() < 0.15:  # 15% шанс специального случая
        case_type = random.choice(CASE_TYPES)
        ai_special_cases_total.labels(case_type=case_type).inc()

    # Иногда обрезаем историю
    if random.random() < 0.08:  # 8% шанс обрезки
        ai_history_truncation_total.inc()

def update_active_chats():
    """Обновляет количество активных чатов"""
    # Генерируем реалистичное число активных чатов (меняется со временем)
    hour = datetime.now().hour

    # Больше чатов в рабочее время (9-18)
    if 9 <= hour <= 18:
        base_chats = random.randint(45, 75)
    else:
        base_chats = random.randint(10, 30)

    ai_active_chats.set(base_chats)

def run_mock_service(port=1234, requests_per_minute=30):
    """
    Запускает mock-сервис для генерации метрик

    Args:
        port: порт для HTTP сервера метрик
        requests_per_minute: количество симулируемых запросов в минуту
    """
    # Запускаем HTTP сервер для экспорта метрик
    start_http_server(port)
    logger.info(f"Mock metrics server started on port {port}")
    logger.info(f"Generating ~{requests_per_minute} requests per minute")
    logger.info("Metrics available at http://localhost:{}/metrics".format(port))

    delay_between_requests = 60.0 / requests_per_minute

    iteration = 0
    try:
        while True:
            # Генерируем метрики для одного запроса
            generate_realistic_metrics()

            # Обновляем активные чаты каждые 10 запросов
            if iteration % 10 == 0:
                update_active_chats()
                logger.info(f"Generated {iteration} mock requests so far...")

            iteration += 1

            # Добавляем небольшую случайность в задержке
            actual_delay = delay_between_requests * random.uniform(0.5, 1.5)
            time.sleep(actual_delay)

    except KeyboardInterrupt:
        logger.info("Stopping mock metrics service...")

if __name__ == "__main__":
    # По умолчанию генерируем 30 запросов в минуту
    # Это даст хороший поток данных для графиков в Grafana
    run_mock_service(port=1234, requests_per_minute=30)
