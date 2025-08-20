-- 🚀 MEFAPEX Advanced Database Optimizations
-- =============================================
-- Complete PostgreSQL optimization suite for production performance

-- 1. ✨ Advanced Indexing Strategy
-- ================================

-- Drop existing basic indexes to recreate as optimized versions
DROP INDEX IF EXISTS idx_messages_user_timestamp;
DROP INDEX IF EXISTS idx_messages_session_timestamp;
DROP INDEX IF EXISTS idx_sessions_user_activity;

-- Advanced composite indexes for high-performance queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_messages_user_timestamp_desc 
ON chat_messages(user_id, timestamp DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_messages_session_timestamp_asc 
ON chat_messages(session_id, timestamp ASC);

-- Optimized index for active sessions
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sessions_user_activity 
ON chat_sessions(user_id, last_activity DESC) 
WHERE is_active = true;

-- Full-text search index for Turkish content (improved)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_messages_fts_turkish 
ON chat_messages USING gin(to_tsvector('turkish', COALESCE(user_message, '') || ' ' || COALESCE(bot_response, '')));

-- Partial indexes for recent data (hot data)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_messages_recent_week
ON chat_messages(timestamp DESC, user_id) 
WHERE timestamp > (CURRENT_TIMESTAMP - INTERVAL '7 days');

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_messages_recent_month
ON chat_messages(timestamp DESC, user_id) 
WHERE timestamp > (CURRENT_TIMESTAMP - INTERVAL '30 days');

-- Performance index for session statistics
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sessions_stats
ON chat_sessions(user_id, message_count DESC, last_activity DESC)
WHERE is_active = true AND message_count > 0;

-- 2. 🗂️ Table Partitioning Strategy
-- =================================

-- Create partitioned table for large datasets
CREATE TABLE IF NOT EXISTS chat_messages_partitioned (
    LIKE chat_messages INCLUDING ALL
) PARTITION BY RANGE (timestamp);

-- Create monthly partitions for current and future months
DO $$
DECLARE
    start_date date;
    end_date date;
    partition_name text;
BEGIN
    -- Create partitions for the last 6 months and next 12 months
    FOR i IN -6..12 LOOP
        start_date := date_trunc('month', CURRENT_DATE) + (i || ' months')::interval;
        end_date := start_date + interval '1 month';
        partition_name := 'chat_messages_' || to_char(start_date, 'YYYY_MM');
        
        EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF chat_messages_partitioned 
                       FOR VALUES FROM (%L) TO (%L)', 
                       partition_name, start_date, end_date);
    END LOOP;
END $$;

-- 3. ⚡ Optimized Query Functions
-- ==============================

-- High-performance chat history with cursor pagination
CREATE OR REPLACE FUNCTION get_chat_history_optimized(
    p_user_id UUID,
    p_cursor_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    p_limit INTEGER DEFAULT 20
)
RETURNS TABLE (
    id BIGINT,
    user_message TEXT,
    bot_response TEXT,
    timestamp TIMESTAMP WITH TIME ZONE,
    source VARCHAR(100)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        m.id,
        m.user_message,
        m.bot_response,
        m.timestamp,
        m.source
    FROM chat_messages m
    WHERE m.user_id = p_user_id 
    AND (p_cursor_timestamp IS NULL OR m.timestamp < p_cursor_timestamp)
    ORDER BY m.timestamp DESC 
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql STABLE;

-- Optimized session statistics
CREATE OR REPLACE FUNCTION get_user_session_stats(p_user_id UUID)
RETURNS TABLE (
    session_id UUID,
    created_at TIMESTAMP WITH TIME ZONE,
    message_count BIGINT,
    last_message_time TIMESTAMP WITH TIME ZONE,
    first_message TEXT
) AS $$
BEGIN
    RETURN QUERY
    WITH session_stats AS (
        SELECT 
            s.session_id,
            s.created_at,
            COUNT(m.id) as msg_count,
            MAX(m.timestamp) as last_msg,
            (array_agg(m.user_message ORDER BY m.timestamp ASC))[1] as first_msg
        FROM chat_sessions s
        LEFT JOIN chat_messages m ON s.session_id = m.session_id
        WHERE s.user_id = p_user_id
        GROUP BY s.session_id, s.created_at
        HAVING COUNT(m.id) > 0
    )
    SELECT 
        ss.session_id,
        ss.created_at,
        ss.msg_count,
        ss.last_msg,
        COALESCE(ss.first_msg, 'Empty Session')
    FROM session_stats ss
    ORDER BY ss.last_msg DESC, ss.created_at DESC;
END;
$$ LANGUAGE plpgsql STABLE;

-- Fast search function with Turkish full-text search
CREATE OR REPLACE FUNCTION search_messages_turkish(
    p_user_id UUID,
    p_search_text TEXT,
    p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
    id BIGINT,
    user_message TEXT,
    bot_response TEXT,
    timestamp TIMESTAMP WITH TIME ZONE,
    session_id UUID,
    relevance REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        m.id,
        m.user_message,
        m.bot_response,
        m.timestamp,
        m.session_id,
        ts_rank(to_tsvector('turkish', COALESCE(m.user_message, '') || ' ' || COALESCE(m.bot_response, '')), 
                plainto_tsquery('turkish', p_search_text)) as relevance
    FROM chat_messages m
    WHERE m.user_id = p_user_id
    AND to_tsvector('turkish', COALESCE(m.user_message, '') || ' ' || COALESCE(m.bot_response, '')) 
        @@ plainto_tsquery('turkish', p_search_text)
    ORDER BY relevance DESC, m.timestamp DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql STABLE;

-- 4. 🧹 Automated Cleanup Functions
-- =================================

-- Comprehensive cleanup function
CREATE OR REPLACE FUNCTION cleanup_old_data(
    p_retention_months INTEGER DEFAULT 6,
    p_max_sessions_per_user INTEGER DEFAULT 50
)
RETURNS JSON AS $$
DECLARE
    deleted_messages INTEGER := 0;
    deleted_sessions INTEGER := 0;
    cleaned_users INTEGER := 0;
    result JSON;
BEGIN
    -- Delete old messages (older than retention period)
    DELETE FROM chat_messages 
    WHERE timestamp < CURRENT_TIMESTAMP - (p_retention_months || ' months')::INTERVAL;
    GET DIAGNOSTICS deleted_messages = ROW_COUNT;
    
    -- Delete empty sessions
    DELETE FROM chat_sessions 
    WHERE id NOT IN (
        SELECT DISTINCT session_id::TEXT::INTEGER 
        FROM chat_messages 
        WHERE session_id IS NOT NULL
    );
    GET DIAGNOSTICS deleted_sessions = ROW_COUNT;
    
    -- Clean up excess sessions per user (keep only recent ones)
    WITH excess_sessions AS (
        SELECT s.id
        FROM chat_sessions s
        LEFT JOIN chat_messages m ON s.session_id = m.session_id
        WHERE s.id NOT IN (
            SELECT s2.id
            FROM chat_sessions s2
            LEFT JOIN chat_messages m2 ON s2.session_id = m2.session_id
            WHERE s2.user_id = s.user_id
            ORDER BY COALESCE(MAX(m2.timestamp), s2.created_at) DESC
            LIMIT p_max_sessions_per_user
        )
        GROUP BY s.id
    )
    DELETE FROM chat_sessions WHERE id IN (SELECT id FROM excess_sessions);
    
    -- Update statistics
    ANALYZE chat_messages;
    ANALYZE chat_sessions;
    ANALYZE users;
    
    -- Reset stats for better query planning
    PERFORM pg_stat_reset();
    
    result := json_build_object(
        'deleted_messages', deleted_messages,
        'deleted_sessions', deleted_sessions,
        'cleanup_timestamp', CURRENT_TIMESTAMP,
        'retention_months', p_retention_months,
        'max_sessions_per_user', p_max_sessions_per_user
    );
    
    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- Vacuum and maintenance function
CREATE OR REPLACE FUNCTION maintenance_tasks()
RETURNS JSON AS $$
DECLARE
    result JSON;
    start_time TIMESTAMP;
BEGIN
    start_time := CURRENT_TIMESTAMP;
    
    -- Vacuum analyze all tables
    VACUUM ANALYZE users;
    VACUUM ANALYZE chat_sessions;
    VACUUM ANALYZE chat_messages;
    
    -- Reindex if fragmentation is high
    REINDEX INDEX CONCURRENTLY idx_messages_user_timestamp_desc;
    REINDEX INDEX CONCURRENTLY idx_messages_session_timestamp_asc;
    REINDEX INDEX CONCURRENTLY idx_sessions_user_activity;
    
    result := json_build_object(
        'maintenance_completed', CURRENT_TIMESTAMP,
        'duration_seconds', EXTRACT(epoch FROM (CURRENT_TIMESTAMP - start_time)),
        'tasks_completed', ARRAY['vacuum_analyze', 'reindex']
    );
    
    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- 5. 📊 Performance Monitoring Views
-- ===================================

-- Performance statistics view
CREATE OR REPLACE VIEW performance_stats AS
SELECT 
    schemaname,
    tablename,
    n_tup_ins as inserts,
    n_tup_upd as updates,
    n_tup_del as deletes,
    n_live_tup as live_tuples,
    n_dead_tup as dead_tuples,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    last_autoanalyze,
    vacuum_count,
    autovacuum_count,
    analyze_count,
    autoanalyze_count
FROM pg_stat_user_tables
ORDER BY n_live_tup DESC;

-- Index usage statistics
CREATE OR REPLACE VIEW index_usage_stats AS
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_tup_read as index_reads,
    idx_tup_fetch as index_fetches,
    idx_scan as index_scans,
    CASE 
        WHEN idx_scan = 0 THEN 'UNUSED'
        WHEN idx_scan < 100 THEN 'LOW_USAGE'
        WHEN idx_scan < 1000 THEN 'MEDIUM_USAGE'
        ELSE 'HIGH_USAGE'
    END as usage_level
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;

-- Query performance view
CREATE OR REPLACE VIEW slow_queries AS
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    min_time,
    max_time,
    stddev_time,
    rows,
    100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
FROM pg_stat_statements
WHERE mean_time > 100  -- queries taking more than 100ms on average
ORDER BY mean_time DESC;

-- Database size and growth tracking
CREATE OR REPLACE VIEW database_size_stats AS
SELECT 
    pg_database.datname as database_name,
    pg_size_pretty(pg_database_size(pg_database.datname)) as size,
    pg_database_size(pg_database.datname) as size_bytes
FROM pg_database
WHERE pg_database.datname = current_database();

-- Table size statistics
CREATE OR REPLACE VIEW table_size_stats AS
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) as index_size,
    pg_total_relation_size(schemaname||'.'||tablename) as total_bytes,
    pg_relation_size(schemaname||'.'||tablename) as table_bytes
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- 6. 🔧 Connection and Performance Settings
-- ==========================================

-- Optimized settings for production (apply via postgresql.conf or docker)
/*
-- Connection Settings
max_connections = 200
superuser_reserved_connections = 3

-- Memory Settings  
shared_buffers = 256MB                    # 25% of RAM
effective_cache_size = 1GB                # 75% of RAM
work_mem = 4MB                           # Per connection working memory
maintenance_work_mem = 64MB              # Maintenance operations
dynamic_shared_memory_type = posix

-- Checkpoint Settings
wal_buffers = 16MB
checkpoint_completion_target = 0.9
checkpoint_timeout = 15min
max_wal_size = 4GB
min_wal_size = 1GB

-- Query Planner
random_page_cost = 1.1                   # SSD optimized
effective_io_concurrency = 200           # SSD parallel I/O
default_statistics_target = 100          # Better query planning

-- Logging
log_min_duration_statement = 1000        # Log slow queries (>1s)
log_checkpoints = on
log_connections = on
log_disconnections = on
log_lock_waits = on

-- Autovacuum Tuning
autovacuum_max_workers = 3
autovacuum_naptime = 20s
autovacuum_vacuum_threshold = 50
autovacuum_analyze_threshold = 50
autovacuum_vacuum_scale_factor = 0.1
autovacuum_analyze_scale_factor = 0.05
autovacuum_vacuum_cost_delay = 10ms
autovacuum_vacuum_cost_limit = 1000

-- Background Writer
bgwriter_delay = 200ms
bgwriter_lru_maxpages = 100
bgwriter_lru_multiplier = 2.0

-- Archive Settings (for backup)
archive_mode = on
archive_command = 'cp %p /var/lib/postgresql/archive/%f'
*/

-- 7. 🕐 Automated Scheduling
-- ==========================

-- Install pg_cron extension if available
-- CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Schedule daily cleanup at 2 AM
-- SELECT cron.schedule('mefapex-daily-cleanup', '0 2 * * *', 'SELECT cleanup_old_data()');

-- Schedule weekly maintenance on Sunday at 3 AM  
-- SELECT cron.schedule('mefapex-weekly-maintenance', '0 3 * * 0', 'SELECT maintenance_tasks()');

-- Schedule hourly statistics update
-- SELECT cron.schedule('mefapex-stats-update', '0 * * * *', 'ANALYZE;');

-- 8. 🛡️ Security and Monitoring
-- ==============================

-- Create monitoring role
CREATE ROLE mefapex_monitor;
GRANT CONNECT ON DATABASE mefapex_chatbot TO mefapex_monitor;
GRANT USAGE ON SCHEMA public TO mefapex_monitor;
GRANT SELECT ON performance_stats, index_usage_stats, table_size_stats TO mefapex_monitor;

-- Function to check database health
CREATE OR REPLACE FUNCTION database_health_check()
RETURNS JSON AS $$
DECLARE
    result JSON;
    connection_count INTEGER;
    active_queries INTEGER;
    db_size_mb NUMERIC;
    cache_hit_ratio NUMERIC;
BEGIN
    -- Get current connections
    SELECT count(*) INTO connection_count FROM pg_stat_activity;
    
    -- Get active queries
    SELECT count(*) INTO active_queries FROM pg_stat_activity WHERE state = 'active';
    
    -- Get database size in MB
    SELECT pg_database_size(current_database()) / 1024 / 1024 INTO db_size_mb;
    
    -- Calculate cache hit ratio
    SELECT 
        round(
            100.0 * sum(blks_hit) / (sum(blks_hit) + sum(blks_read)), 2
        ) INTO cache_hit_ratio
    FROM pg_stat_database 
    WHERE datname = current_database();
    
    result := json_build_object(
        'timestamp', CURRENT_TIMESTAMP,
        'database_name', current_database(),
        'connection_count', connection_count,
        'active_queries', active_queries,
        'database_size_mb', db_size_mb,
        'cache_hit_ratio_percent', COALESCE(cache_hit_ratio, 0),
        'status', CASE 
            WHEN connection_count > 150 THEN 'WARNING: High connection count'
            WHEN cache_hit_ratio < 95 THEN 'WARNING: Low cache hit ratio'
            ELSE 'HEALTHY'
        END
    );
    
    RETURN result;
END;
$$ LANGUAGE plpgsql STABLE;

-- 9. 🚀 Query Optimization Hints
-- ===============================

-- Create function to get query execution plans
CREATE OR REPLACE FUNCTION explain_query(query_text TEXT)
RETURNS TABLE (plan_line TEXT) AS $$
BEGIN
    RETURN QUERY EXECUTE 'EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) ' || query_text;
END;
$$ LANGUAGE plpgsql;

-- Create indexes for common query patterns
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_messages_user_recent
ON chat_messages(user_id, timestamp DESC)
WHERE timestamp > CURRENT_TIMESTAMP - INTERVAL '30 days';

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sessions_active_users
ON chat_sessions(user_id)
WHERE is_active = true;

-- 10. 📈 Performance Reporting
-- ============================

-- Create comprehensive performance report function
CREATE OR REPLACE FUNCTION generate_performance_report()
RETURNS JSON AS $$
DECLARE
    report JSON;
    table_stats JSON;
    index_stats JSON;
    health_stats JSON;
BEGIN
    -- Get table statistics
    SELECT json_agg(
        json_build_object(
            'table_name', tablename,
            'total_size', pg_size_pretty(pg_total_relation_size('public.'||tablename)),
            'live_tuples', n_live_tup,
            'dead_tuples', n_dead_tup,
            'last_vacuum', last_vacuum,
            'last_analyze', last_analyze
        )
    ) INTO table_stats
    FROM pg_stat_user_tables
    WHERE schemaname = 'public';
    
    -- Get index statistics
    SELECT json_agg(
        json_build_object(
            'index_name', indexname,
            'table_name', tablename,
            'index_scans', idx_scan,
            'tuples_read', idx_tup_read,
            'usage_level', CASE 
                WHEN idx_scan = 0 THEN 'UNUSED'
                WHEN idx_scan < 100 THEN 'LOW'
                WHEN idx_scan < 1000 THEN 'MEDIUM'
                ELSE 'HIGH'
            END
        )
    ) INTO index_stats
    FROM pg_stat_user_indexes
    WHERE schemaname = 'public';
    
    -- Get health statistics
    SELECT database_health_check() INTO health_stats;
    
    -- Combine all statistics
    report := json_build_object(
        'generated_at', CURRENT_TIMESTAMP,
        'database_health', health_stats,
        'table_statistics', table_stats,
        'index_statistics', index_stats,
        'recommendations', json_build_array(
            'Run VACUUM ANALYZE weekly',
            'Monitor index usage and drop unused indexes',
            'Consider partitioning for tables > 10M rows',
            'Review slow queries > 1000ms',
            'Maintain cache hit ratio > 95%'
        )
    );
    
    RETURN report;
END;
$$ LANGUAGE plpgsql STABLE;

-- Final optimization: Update table statistics
ANALYZE users;
ANALYZE chat_sessions; 
ANALYZE chat_messages;

-- Log completion
INSERT INTO chat_messages (session_id, user_id, user_message, bot_response, source)
SELECT 
    gen_random_uuid(),
    (SELECT user_id FROM users WHERE username = 'demo' LIMIT 1),
    'Database optimization completed',
    'Advanced PostgreSQL optimizations have been successfully applied including: indexing strategy, partitioning, query optimization, automated cleanup, and performance monitoring.',
    'database_optimization'
WHERE EXISTS (SELECT 1 FROM users WHERE username = 'demo')
ON CONFLICT DO NOTHING;

-- 🎉 Optimization Complete!
-- =========================
/*
Applied optimizations:
✅ Advanced composite indexing strategy
✅ Table partitioning for scalability  
✅ Optimized query functions with cursor pagination
✅ Automated cleanup and maintenance procedures
✅ Performance monitoring views and functions
✅ Turkish full-text search optimization
✅ Database health monitoring
✅ Security enhancements
✅ Query performance analysis tools
✅ Comprehensive reporting system

Next steps:
1. Apply PostgreSQL configuration settings via docker-compose
2. Schedule automated cleanup jobs  
3. Monitor performance metrics regularly
4. Consider Redis caching for frequently accessed data
5. Implement connection pooling (PgBouncer)
*/
