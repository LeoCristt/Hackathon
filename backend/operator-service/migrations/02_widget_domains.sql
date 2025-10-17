-- Таблица для хранения разрешённых доменов и их настроек
CREATE TABLE IF NOT EXISTS widget_domains (
    id SERIAL PRIMARY KEY,
    domain VARCHAR(255) UNIQUE NOT NULL,
    ai_model VARCHAR(100) NOT NULL DEFAULT 'gpt-4',
    is_active BOOLEAN DEFAULT true,
    max_requests_per_day INTEGER DEFAULT 1000,
    allowed_origins TEXT[], -- массив разрешённых origin (для CORS)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для быстрого поиска
CREATE INDEX idx_widget_domains_domain ON widget_domains(domain);
CREATE INDEX idx_widget_domains_active ON widget_domains(is_active);

-- Вставка тестовых данных
INSERT INTO widget_domains (domain, ai_model, is_active, max_requests_per_day, allowed_origins) VALUES
    ('localhost', 'gpt-9', true, 10000, ARRAY['http://localhost:3300', 'http://localhost:8080', 'http://127.0.0.1:3000']),
    ('example.com', 'claude-3', true, 5000, ARRAY['https://example.com', 'https://www.example.com']),
    ('demo.com', 'gpt-4-turbo', true, 2000, ARRAY['https://demo.com']),
    ('test.local', 'gpt-3.5-turbo', true, 1000, ARRAY['http://test.local']);

-- Комментарии к полям
COMMENT ON TABLE widget_domains IS 'Разрешённые домены для виджета с настройками AI моделей';
COMMENT ON COLUMN widget_domains.domain IS 'Доменное имя (без протокола и порта)';
COMMENT ON COLUMN widget_domains.ai_model IS 'AI модель для использования (gpt-4, claude-3, и т.д.)';
COMMENT ON COLUMN widget_domains.is_active IS 'Активен ли домен';
COMMENT ON COLUMN widget_domains.max_requests_per_day IS 'Лимит запросов в день';
COMMENT ON COLUMN widget_domains.allowed_origins IS 'Массив разрешённых Origin для CORS';
