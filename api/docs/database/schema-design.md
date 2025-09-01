# Database Schema Design

## Overview

The Play Later database is designed for PostgreSQL with a focus on performance, data integrity, and scalability. The schema separates concerns between game metadata, user ownership, and playthrough tracking while maintaining referential integrity and optimizing for common query patterns.

## Connection Configuration

```bash
# Available test database
DATABASE_URL=postgresql://postgres:postgres@0.0.0.0:6432/play-later-db

# Production environment variables
DATABASE_URL=postgresql://user:password@host:port/database_name
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
DATABASE_POOL_TIMEOUT=30
```

## Core Tables

### Games Table
Central repository for game metadata cached from IGDB.

```sql
CREATE TABLE games (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    igdb_id INTEGER UNIQUE,
    hltb_id INTEGER,
    steam_app_id INTEGER,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    cover_image_id VARCHAR(50), -- IGDB image identifier like 'co2lbd'
    release_date DATE,
    main_story INTEGER, -- HLTB hours
    main_extra INTEGER, -- HLTB hours  
    completionist INTEGER, -- HLTB hours
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for game lookups
CREATE UNIQUE INDEX idx_games_igdb_id ON games(igdb_id) WHERE igdb_id IS NOT NULL;
CREATE INDEX idx_games_title_search ON games USING gin(to_tsvector('english', title));
CREATE INDEX idx_games_release_date ON games(release_date);
CREATE INDEX idx_games_created_at ON games(created_at);

-- Full-text search index
CREATE INDEX idx_games_search ON games USING gin(
    to_tsvector('english', coalesce(title, '') || ' ' || coalesce(description, ''))
);
```

### User Game Collection Table
Tracks user ownership/access to games on specific platforms.

```sql
CREATE TABLE user_game_collection (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL, -- AWS Cognito sub
    game_id UUID NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    acquisition_type VARCHAR(20) NOT NULL CHECK (acquisition_type IN ('PHYSICAL', 'DIGITAL', 'SUBSCRIPTION', 'BORROWED', 'RENTAL')),
    acquired_at TIMESTAMP WITH TIME ZONE NOT NULL,
    priority INTEGER CHECK (priority >= 1 AND priority <= 5),
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Unique constraint: user can own same game on different platforms
    UNIQUE(user_id, game_id, platform)
);

-- Performance indexes for collection filtering
CREATE INDEX idx_collection_user_id ON user_game_collection(user_id);
CREATE INDEX idx_collection_user_platform ON user_game_collection(user_id, platform);
CREATE INDEX idx_collection_user_priority ON user_game_collection(user_id, priority) WHERE priority IS NOT NULL;
CREATE INDEX idx_collection_user_acquired ON user_game_collection(user_id, acquired_at);
CREATE INDEX idx_collection_active ON user_game_collection(user_id, is_active);

-- Composite indexes for common filter combinations
CREATE INDEX idx_collection_platform_priority ON user_game_collection(user_id, platform, priority);
CREATE INDEX idx_collection_platform_acquired ON user_game_collection(user_id, platform, acquired_at);
```

### Game Playthrough Table  
Individual play sessions with comprehensive tracking.

```sql
CREATE TABLE game_playthrough (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL, -- AWS Cognito sub
    game_id UUID NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    collection_id UUID REFERENCES user_game_collection(id) ON DELETE SET NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('PLANNING', 'PLAYING', 'COMPLETED', 'DROPPED', 'ON_HOLD', 'MASTERED')),
    platform VARCHAR(50) NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    play_time_hours DECIMAL(8,2) CHECK (play_time_hours >= 0),
    playthrough_type VARCHAR(100), -- 'First Run', 'NG+', 'Speedrun', etc.
    difficulty VARCHAR(50),
    rating INTEGER CHECK (rating >= 1 AND rating <= 10),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Business rules
    CONSTRAINT check_completion_date CHECK (
        (completed_at IS NULL) OR 
        (started_at IS NULL) OR 
        (completed_at > started_at)
    ),
    CONSTRAINT check_completion_status CHECK (
        (status NOT IN ('COMPLETED', 'MASTERED')) OR 
        (completed_at IS NOT NULL)
    )
);

-- Performance indexes for playthrough filtering
CREATE INDEX idx_playthrough_user_id ON game_playthrough(user_id);
CREATE INDEX idx_playthrough_user_status ON game_playthrough(user_id, status);
CREATE INDEX idx_playthrough_user_platform ON game_playthrough(user_id, platform);
CREATE INDEX idx_playthrough_user_rating ON game_playthrough(user_id, rating) WHERE rating IS NOT NULL;
CREATE INDEX idx_playthrough_user_completed ON game_playthrough(user_id, completed_at) WHERE completed_at IS NOT NULL;
CREATE INDEX idx_playthrough_user_updated ON game_playthrough(user_id, updated_at);
CREATE INDEX idx_playthrough_game_user ON game_playthrough(game_id, user_id);

-- Composite indexes for advanced filtering
CREATE INDEX idx_playthrough_status_platform ON game_playthrough(user_id, status, platform);
CREATE INDEX idx_playthrough_status_rating ON game_playthrough(user_id, status, rating);
CREATE INDEX idx_playthrough_completed_rating ON game_playthrough(user_id, completed_at, rating) WHERE completed_at IS NOT NULL;
```

## Session Management Tables

### User Sessions Table
Secure session storage for authentication.

```sql  
CREATE TABLE user_sessions (
    session_id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for session management
CREATE INDEX idx_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_sessions_expires_at ON user_sessions(expires_at);

-- Cleanup expired sessions automatically
CREATE INDEX idx_sessions_cleanup ON user_sessions(expires_at) WHERE expires_at < CURRENT_TIMESTAMP;
```

## Audit and Metadata Tables

### Game Update Log
Track changes to game metadata for cache invalidation.

```sql
CREATE TABLE game_update_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id UUID NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    field_name VARCHAR(100) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    updated_by VARCHAR(50) DEFAULT 'system',
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_game_updates_game_id ON game_update_log(game_id, updated_at);
CREATE INDEX idx_game_updates_date ON game_update_log(updated_at);
```

## Database Views

### Active Collection View
Simplified view of active collection items with game details.

```sql
CREATE VIEW active_collection AS
SELECT 
    c.id,
    c.user_id,
    c.game_id,
    g.title,
    g.cover_image_id,
    g.release_date,
    c.platform,
    c.acquisition_type,
    c.acquired_at,
    c.priority,
    c.notes,
    c.created_at,
    c.updated_at
FROM user_game_collection c
JOIN games g ON c.game_id = g.id
WHERE c.is_active = TRUE;
```

### Playthrough Summary View
Rich view combining playthrough and game data.

```sql
CREATE VIEW playthrough_summary AS
SELECT 
    p.id,
    p.user_id,
    p.game_id,
    g.title,
    g.cover_image_id,
    g.main_story,
    g.main_extra,
    g.completionist,
    p.status,
    p.platform,
    p.started_at,
    p.completed_at,
    p.play_time_hours,
    p.playthrough_type,
    p.difficulty,
    p.rating,
    p.notes,
    p.created_at,
    p.updated_at,
    -- Calculated fields
    CASE 
        WHEN p.completed_at IS NOT NULL AND p.started_at IS NOT NULL 
        THEN p.completed_at - p.started_at 
        ELSE NULL 
    END AS duration,
    CASE
        WHEN p.play_time_hours IS NOT NULL AND g.main_story IS NOT NULL
        THEN ROUND((p.play_time_hours / g.main_story) * 100, 1)
        ELSE NULL
    END AS completion_percentage
FROM game_playthrough p
JOIN games g ON p.game_id = g.id;
```

### User Statistics View
Aggregated statistics per user.

```sql
CREATE VIEW user_game_stats AS
SELECT 
    user_id,
    -- Collection stats
    COUNT(DISTINCT c.id) FILTER (WHERE c.is_active = TRUE) as total_games,
    COUNT(DISTINCT c.id) FILTER (WHERE c.platform = 'PS5' AND c.is_active = TRUE) as ps5_games,
    COUNT(DISTINCT c.id) FILTER (WHERE c.platform = 'Steam' AND c.is_active = TRUE) as steam_games,
    COUNT(DISTINCT c.id) FILTER (WHERE c.platform = 'Xbox' AND c.is_active = TRUE) as xbox_games,
    COUNT(DISTINCT c.id) FILTER (WHERE c.platform = 'Switch' AND c.is_active = TRUE) as switch_games,
    
    -- Playthrough stats
    COUNT(DISTINCT p.id) as total_playthroughs,
    COUNT(DISTINCT p.id) FILTER (WHERE p.status = 'COMPLETED') as completed_games,
    COUNT(DISTINCT p.id) FILTER (WHERE p.status = 'PLAYING') as currently_playing,
    COUNT(DISTINCT p.id) FILTER (WHERE p.status = 'PLANNING') as backlog_size,
    
    -- Time and rating stats
    COALESCE(SUM(p.play_time_hours) FILTER (WHERE p.status = 'COMPLETED'), 0) as total_hours,
    ROUND(AVG(p.rating) FILTER (WHERE p.rating IS NOT NULL), 1) as average_rating,
    ROUND(AVG(p.play_time_hours) FILTER (WHERE p.status = 'COMPLETED' AND p.play_time_hours IS NOT NULL), 1) as avg_completion_time,
    
    -- Completion rate
    CASE 
        WHEN COUNT(DISTINCT p.id) > 0 
        THEN ROUND((COUNT(DISTINCT p.id) FILTER (WHERE p.status = 'COMPLETED')::DECIMAL / COUNT(DISTINCT p.id)) * 100, 1)
        ELSE 0 
    END as completion_rate_percent
FROM user_game_collection c
FULL OUTER JOIN game_playthrough p ON c.user_id = p.user_id
WHERE c.user_id IS NOT NULL OR p.user_id IS NOT NULL
GROUP BY user_id;
```

## Database Functions

### Update Timestamp Function
Automatically update updated_at timestamps.

```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply to all tables with updated_at
CREATE TRIGGER update_games_updated_at BEFORE UPDATE ON games 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_collection_updated_at BEFORE UPDATE ON user_game_collection 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_playthrough_updated_at BEFORE UPDATE ON game_playthrough 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sessions_updated_at BEFORE UPDATE ON user_sessions 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

### Session Cleanup Function
Remove expired sessions automatically.

```sql
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM user_sessions 
    WHERE expires_at < CURRENT_TIMESTAMP;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Schedule cleanup (requires pg_cron extension)
-- SELECT cron.schedule('cleanup-sessions', '0 * * * *', 'SELECT cleanup_expired_sessions();');
```

### Game Search Function
Advanced game search with ranking.

```sql
CREATE OR REPLACE FUNCTION search_games(
    search_query TEXT,
    user_id_param VARCHAR(255) DEFAULT NULL,
    limit_param INTEGER DEFAULT 20
)
RETURNS TABLE(
    id UUID,
    title VARCHAR(255),
    cover_image_id VARCHAR(50),
    release_date DATE,
    owned BOOLEAN,
    search_rank REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        g.id,
        g.title,
        g.cover_image_id,
        g.release_date,
        (c.id IS NOT NULL) as owned,
        ts_rank(
            to_tsvector('english', coalesce(g.title, '') || ' ' || coalesce(g.description, '')),
            plainto_tsquery('english', search_query)
        ) as search_rank
    FROM games g
    LEFT JOIN user_game_collection c ON g.id = c.game_id 
        AND c.user_id = user_id_param 
        AND c.is_active = TRUE
    WHERE to_tsvector('english', coalesce(g.title, '') || ' ' || coalesce(g.description, ''))
        @@ plainto_tsquery('english', search_query)
    ORDER BY search_rank DESC, g.title
    LIMIT limit_param;
END;
$$ LANGUAGE plpgsql;
```

## Performance Optimization

### Query Performance Guidelines

#### Collection Queries
```sql
-- GOOD: Uses user_id index first
SELECT * FROM user_game_collection 
WHERE user_id = $1 AND platform = $2 AND is_active = TRUE;

-- GOOD: Uses composite index
SELECT * FROM user_game_collection 
WHERE user_id = $1 AND platform = $2 AND priority IN (1, 2);

-- BAD: Missing user_id filter (security + performance issue)
SELECT * FROM user_game_collection WHERE platform = $1;
```

#### Playthrough Queries  
```sql
-- GOOD: User-scoped query with status filter
SELECT * FROM game_playthrough 
WHERE user_id = $1 AND status = $2 
ORDER BY updated_at DESC LIMIT 20;

-- GOOD: Complex filtering with proper indexes
SELECT p.*, g.title FROM game_playthrough p
JOIN games g ON p.game_id = g.id
WHERE p.user_id = $1 
  AND p.status IN ('PLAYING', 'COMPLETED')
  AND p.rating >= $2
ORDER BY p.completed_at DESC;
```

### Index Maintenance
```sql
-- Monitor index usage
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;

-- Identify unused indexes
SELECT 
    schemaname,
    tablename,
    indexname
FROM pg_stat_user_indexes
WHERE idx_scan = 0 AND schemaname = 'public';
```

## Data Integrity Constraints

### Business Logic Constraints
```sql
-- Ensure completion dates are logical
ALTER TABLE game_playthrough 
ADD CONSTRAINT check_completion_logic 
CHECK (
    (status NOT IN ('COMPLETED', 'MASTERED')) OR 
    (completed_at IS NOT NULL AND (started_at IS NULL OR completed_at >= started_at))
);

-- Ensure ratings are valid
ALTER TABLE game_playthrough 
ADD CONSTRAINT check_valid_rating 
CHECK (rating IS NULL OR (rating >= 1 AND rating <= 10));

-- Ensure play time is non-negative
ALTER TABLE game_playthrough 
ADD CONSTRAINT check_positive_play_time 
CHECK (play_time_hours IS NULL OR play_time_hours >= 0);

-- Ensure priority is in valid range
ALTER TABLE user_game_collection 
ADD CONSTRAINT check_valid_priority 
CHECK (priority IS NULL OR (priority >= 1 AND priority <= 5));

-- Ensure acquisition date is not in future
ALTER TABLE user_game_collection 
ADD CONSTRAINT check_acquisition_date 
CHECK (acquired_at <= CURRENT_TIMESTAMP);
```

### Referential Integrity
```sql
-- Foreign key constraints with proper cascade behavior
ALTER TABLE user_game_collection 
ADD CONSTRAINT fk_collection_game 
FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE;

ALTER TABLE game_playthrough 
ADD CONSTRAINT fk_playthrough_game 
FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE;

ALTER TABLE game_playthrough 
ADD CONSTRAINT fk_playthrough_collection 
FOREIGN KEY (collection_id) REFERENCES user_game_collection(id) ON DELETE SET NULL;
```

## Security Considerations

### Row Level Security (RLS)
```sql
-- Enable RLS on user tables
ALTER TABLE user_game_collection ENABLE ROW LEVEL SECURITY;
ALTER TABLE game_playthrough ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY;

-- Collection access policy
CREATE POLICY collection_user_access ON user_game_collection
    FOR ALL TO application_role
    USING (user_id = current_setting('app.current_user_id'));

-- Playthrough access policy  
CREATE POLICY playthrough_user_access ON game_playthrough
    FOR ALL TO application_role
    USING (user_id = current_setting('app.current_user_id'));

-- Session access policy
CREATE POLICY session_user_access ON user_sessions
    FOR ALL TO application_role
    USING (user_id = current_setting('app.current_user_id'));
```

### Database Roles
```sql
-- Application connection role
CREATE ROLE application_role;
GRANT CONNECT ON DATABASE play_later_db TO application_role;
GRANT USAGE ON SCHEMA public TO application_role;

-- Table permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON games TO application_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON user_game_collection TO application_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON game_playthrough TO application_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON user_sessions TO application_role;

-- Sequence permissions for UUID generation
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO application_role;
```

## Backup and Maintenance

### Backup Strategy
```sql
-- Full backup
pg_dump -h 0.0.0.0 -p 6432 -U postgres -d play-later-db > backup.sql

-- Schema only backup
pg_dump -h 0.0.0.0 -p 6432 -U postgres -d play-later-db --schema-only > schema.sql

-- Data only backup
pg_dump -h 0.0.0.0 -p 6432 -U postgres -d play-later-db --data-only > data.sql
```

### Maintenance Tasks
```sql
-- Regular maintenance queries
ANALYZE; -- Update table statistics
VACUUM ANALYZE; -- Reclaim space and update stats
REINDEX DATABASE play_later_db; -- Rebuild indexes

-- Monitor database size
SELECT 
    pg_size_pretty(pg_database_size('play-later-db')) as database_size,
    pg_size_pretty(pg_total_relation_size('user_game_collection')) as collection_size,
    pg_size_pretty(pg_total_relation_size('game_playthrough')) as playthrough_size;
```

## Migration Strategy

### From Current Prisma Schema
```sql
-- Migration mapping from existing schema
-- BacklogItem -> user_game_collection + game_playthrough split
-- User fields -> handled by Cognito (no users table needed)
-- Game fields -> mostly direct mapping with cover_image_id change

-- Example migration script structure:
-- 1. Create new tables
-- 2. Migrate games (update cover_image URL to ID)
-- 3. Split BacklogItem into collection + playthrough
-- 4. Migrate user references to Cognito sub
-- 5. Update indexes and constraints
-- 6. Verify data integrity
```

This schema design provides a robust foundation for the Play Later application with excellent performance characteristics, data integrity, and scalability for future growth.