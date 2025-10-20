INSERT INTO roles (name) VALUES
('admin'),
('operator'),
('admin-operator'),
('user')
ON CONFLICT (name) DO NOTHING;

INSERT INTO users (first_name, last_name, middle_name, password, email, role_id) 
VALUES (
    'admin',
    'admin',
    'admin',
    '$2a$12$c7bZQ1.B8zvTkCpn8RdJg.EzPAiDPPBqgFOMHZHX3W/GFU8cnyl7u', --admin123
    'admin@admin.com',
    (SELECT id FROM roles WHERE name = 'admin')
)
ON CONFLICT (email) DO NOTHING;

INSERT INTO users (first_name, last_name, middle_name, password, email, role_id) 
VALUES (
    'test',
    'test',
    'test',
    '$2a$12$p/P6QsZV9AXkAZaG87/RbevSDadoCXM/XuKUn7j33CwPg/JwlHaHW', --test123
    'test@test.com',
    (SELECT id FROM roles WHERE name = 'user')
)
ON CONFLICT (email) DO NOTHING;

INSERT INTO widget_domains (domain, ai_model, is_active, max_requests_per_day, allowed_origins) VALUES
    ('localhost', 'gpt-9', true, 10000, ARRAY['http://localhost:3300', 'http://localhost:8080', 'http://127.0.0.1:3000']),
    ('example.com', 'claude-3', true, 5000, ARRAY['https://example.com', 'https://www.example.com']),
    ('demo.com', 'gpt-4-turbo', true, 2000, ARRAY['https://demo.com']),
    ('test.local', 'gpt-3.5-turbo', true, 1000, ARRAY['http://test.local']);