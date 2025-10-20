CREATE TABLE IF NOT EXISTS roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(30) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    first_name VARCHAR(30) NOT NULL,
    last_name VARCHAR(30) NOT NULL,
    middle_name VARCHAR(30),
    password VARCHAR(200) NOT NULL,
    email VARCHAR(50) NOT NULL UNIQUE,
    role_id INTEGER NOT NULL,
    CONSTRAINT users_role_id_fkey FOREIGN KEY (role_id) REFERENCES roles(id)
);

CREATE TABLE IF NOT EXISTS chats (
    id VARCHAR(50) PRIMARY KEY,
    is_manager BOOLEAN NOT NULL DEFAULT false,    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    username VARCHAR(30) NOT NULL,
    message TEXT NOT NULL,
    message_sequence INTEGER NOT NULL,
    chat_id VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_chat FOREIGN KEY(chat_id) REFERENCES chats(id)
);

CREATE TABLE IF NOT EXISTS widget_domains (
    id SERIAL PRIMARY KEY,
    domain VARCHAR(255) UNIQUE NOT NULL,
    ai_model VARCHAR(100) NOT NULL DEFAULT 'gpt-4',
    is_active BOOLEAN DEFAULT true,
    max_requests_per_day INTEGER DEFAULT 1000,
    allowed_origins TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS requests (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    user_id INTEGER REFERENCES users(id),
    domain_id INTEGER REFERENCES widget_domains(id)
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role_id ON users(role_id);

CREATE INDEX IF NOT EXISTS idx_roles_name ON roles(name);

CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id);

DROP INDEX IF EXISTS idx_chat_sequence;
CREATE UNIQUE INDEX idx_chat_sequence ON messages(chat_id, message_sequence);

CREATE INDEX idx_widget_domains_domain ON widget_domains(domain);
CREATE INDEX idx_widget_domains_active ON widget_domains(is_active);