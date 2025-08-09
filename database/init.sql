-- 🗄️ MEFAPEX PostgreSQL Database Initialization Script
-- =======================================================
-- This script initializes the PostgreSQL database with optimized settings for production

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search optimization
CREATE EXTENSION IF NOT EXISTS "btree_gin";  -- For advanced indexing

-- Create optimized users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    user_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    failed_login_attempts INTEGER DEFAULT 0,
    created_ip INET,
    last_login_ip INET
);

-- Create optimized chat_sessions table
CREATE TABLE IF NOT EXISTS chat_sessions (
    id SERIAL PRIMARY KEY,
    session_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    message_count INTEGER DEFAULT 0,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create optimized chat_messages table with partitioning support
CREATE TABLE IF NOT EXISTS chat_messages (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL,
    user_id UUID NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    user_message TEXT,
    bot_response TEXT,
    source VARCHAR(100),
    message_hash VARCHAR(64),  -- For deduplication
    response_time_ms INTEGER,   -- Performance tracking
    confidence_score FLOAT     -- AI confidence tracking
);

-- Create performance indexes
CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active) WHERE is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_session_id ON chat_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON chat_sessions(created_at);
CREATE INDEX IF NOT EXISTS idx_sessions_active ON chat_sessions(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_sessions_last_activity ON chat_sessions(last_activity);

CREATE INDEX IF NOT EXISTS idx_messages_user_id ON chat_messages(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_session_id ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON chat_messages(timestamp);
CREATE INDEX IF NOT EXISTS idx_messages_source ON chat_messages(source);
CREATE INDEX IF NOT EXISTS idx_messages_recent ON chat_messages(timestamp) WHERE timestamp > (CURRENT_TIMESTAMP - INTERVAL '7 days');

-- Text search indexes for message content
CREATE INDEX IF NOT EXISTS idx_messages_user_text_search ON chat_messages USING gin(to_tsvector('turkish', user_message));
CREATE INDEX IF NOT EXISTS idx_messages_bot_text_search ON chat_messages USING gin(to_tsvector('turkish', bot_response));

-- Composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_messages_user_timestamp ON chat_messages(user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_messages_session_timestamp ON chat_messages(session_id, timestamp ASC);

-- Foreign key constraints
ALTER TABLE chat_sessions ADD CONSTRAINT IF NOT EXISTS fk_sessions_user_id 
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE;

ALTER TABLE chat_messages ADD CONSTRAINT IF NOT EXISTS fk_messages_user_id 
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE;

ALTER TABLE chat_messages ADD CONSTRAINT IF NOT EXISTS fk_messages_session_id 
    FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE;

-- Create function to update timestamp automatically
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for automatic timestamp updates
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_sessions_updated_at ON chat_sessions;
CREATE TRIGGER update_sessions_updated_at 
    BEFORE UPDATE ON chat_sessions 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create function for automatic session activity update
CREATE OR REPLACE FUNCTION update_session_activity()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE chat_sessions 
    SET last_activity = CURRENT_TIMESTAMP,
        message_count = message_count + 1
    WHERE session_id = NEW.session_id;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to update session activity when messages are added
DROP TRIGGER IF EXISTS update_session_activity_trigger ON chat_messages;
CREATE TRIGGER update_session_activity_trigger
    AFTER INSERT ON chat_messages
    FOR EACH ROW EXECUTE FUNCTION update_session_activity();

-- Create view for recent chat activity
CREATE OR REPLACE VIEW recent_chat_activity AS
SELECT 
    u.username,
    u.user_id,
    s.session_id,
    s.created_at as session_started,
    s.last_activity,
    s.message_count,
    m.latest_message
FROM users u
JOIN chat_sessions s ON u.user_id = s.user_id
LEFT JOIN (
    SELECT 
        session_id,
        MAX(timestamp) as latest_message
    FROM chat_messages
    GROUP BY session_id
) m ON s.session_id = m.session_id
WHERE s.is_active = TRUE
ORDER BY s.last_activity DESC;

-- Create view for user statistics
CREATE OR REPLACE VIEW user_statistics AS
SELECT 
    u.user_id,
    u.username,
    u.created_at as user_created,
    COUNT(DISTINCT s.session_id) as total_sessions,
    COUNT(m.id) as total_messages,
    MAX(m.timestamp) as last_message_time,
    AVG(m.response_time_ms) as avg_response_time,
    COALESCE(SUM(CASE WHEN m.timestamp > CURRENT_TIMESTAMP - INTERVAL '24 hours' THEN 1 ELSE 0 END), 0) as messages_last_24h
FROM users u
LEFT JOIN chat_sessions s ON u.user_id = s.user_id
LEFT JOIN chat_messages m ON s.session_id = m.session_id
GROUP BY u.user_id, u.username, u.created_at
ORDER BY total_messages DESC;

-- Performance optimization: Analyze tables
ANALYZE users;
ANALYZE chat_sessions;
ANALYZE chat_messages;

-- Create role for application with minimal privileges
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'mefapex_app') THEN
        CREATE ROLE mefapex_app;
    END IF;
END
$$;

-- Grant minimal required permissions
GRANT CONNECT ON DATABASE mefapex_chatbot TO mefapex_app;
GRANT USAGE ON SCHEMA public TO mefapex_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON users, chat_sessions, chat_messages TO mefapex_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO mefapex_app;
GRANT SELECT ON recent_chat_activity, user_statistics TO mefapex_app;

-- Log completion
INSERT INTO chat_messages (session_id, user_id, user_message, bot_response, source)
SELECT 
    uuid_generate_v4(),
    (SELECT user_id FROM users WHERE username = 'system' LIMIT 1),
    'Database initialization completed',
    'PostgreSQL database has been successfully initialized with production optimizations',
    'system'
WHERE EXISTS (SELECT 1 FROM users WHERE username = 'system')
ON CONFLICT DO NOTHING;

-- Performance settings recommendations (to be applied via docker-compose)
/*
Recommended PostgreSQL configuration for production:

max_connections = 200
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 4MB
min_wal_size = 1GB
max_wal_size = 4GB
*/
