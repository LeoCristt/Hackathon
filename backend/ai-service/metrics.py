"""
Метрики Prometheus для отслеживания эффективности AI-сервиса
"""

from prometheus_client import Counter, Histogram, Gauge, start_http_server
import logging

logger = logging.getLogger(__name__)

# Метрики для запросов
ai_requests_total = Counter(
    'ai_requests_total',
    'Общее количество обработанных запросов',
    ['agent', 'status']  # agent - выбранный агент, status - success/error/escalated
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
    ['token_type'],  # prompt, context, history, total
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
    ['case_type']  # greeting, profanity, escalation, no_context
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

def start_metrics_server(port=8000):
    """Запускает HTTP сервер для экспорта метрик"""
    try:
        start_http_server(port)
        logger.info(f"Metrics server started on port {port}")
    except Exception as e:
        logger.error(f"Failed to start metrics server: {e}")
