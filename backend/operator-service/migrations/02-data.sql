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