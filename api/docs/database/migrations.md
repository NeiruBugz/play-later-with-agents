# Database Migrations Strategy

## Overview

This document outlines the migration strategy for the Play Later database, starting fresh with a clean PostgreSQL schema. We'll use Alembic for database migrations with a focus on performance, maintainability, and incremental development.

## Migration Framework

### Alembic Configuration
Using Alembic for database migrations with PostgreSQL.

```python
# alembic.ini configuration
[alembic]
script_location = alembic
sqlalchemy.url = postgresql://postgres:postgres@0.0.0.0:6432/play-later-db
file_template = %%(year)d%%(month).2d%%(day).2d_%%(hour).2d%%(minute).2d_%%(rev)s_%%(slug)s
timezone = UTC

[loggers]
keys = root,sqlalchemy,alembic

[handlers] 
keys = console

[formatters]
keys = generic
```

### Environment Setup
```python
# alembic/env.py
import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
from app.database.models import Base  # All model imports

config = context.config
target_metadata = Base.metadata

def run_migrations_online():
    """Run migrations in 'online' mode with async support."""
    
    def do_run_migrations(connection: Connection):
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True
        )
        
        with context.begin_transaction():
            context.run_migrations()
    
    async def async_run_migrations():
        connectable = async_engine_from_config(
            config.get_section(config.config_ini_section),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )
        
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)
        
        await connectable.dispose()
    
    asyncio.run(async_run_migrations())
```

## Fresh Database Setup

### Phase 1: Core Schema Setup
Create foundational tables with proper constraints and indexes.

```python
# Migration: 001_initial_schema.py
"""Initial schema setup

Revision ID: 001_initial_schema
Revises: 
Create Date: 2024-03-15 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Games table - central repository for game metadata
    op.create_table('games',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('igdb_id', sa.Integer(), unique=True, nullable=True),
        sa.Column('hltb_id', sa.Integer(), nullable=True),
        sa.Column('steam_app_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('cover_image_id', sa.String(50), nullable=True, comment='IGDB image ID like co2lbd'),
        sa.Column('release_date', sa.Date(), nullable=True),
        sa.Column('main_story', sa.Integer(), nullable=True, comment='HLTB main story hours'),
        sa.Column('main_extra', sa.Integer(), nullable=True, comment='HLTB main + extras hours'),
        sa.Column('completionist', sa.Integer(), nullable=True, comment='HLTB completionist hours'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.current_timestamp()),
    )
    
    # User Game Collection - ownership/access tracking
    op.create_table('user_game_collection',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.String(255), nullable=False, comment='AWS Cognito sub'),
        sa.Column('game_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('acquisition_type', sa.String(20), nullable=False),
        sa.Column('acquired_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True, comment='Soft delete flag'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.current_timestamp()),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'game_id', 'platform', name='uq_user_game_platform'),
        sa.CheckConstraint("acquisition_type IN ('PHYSICAL', 'DIGITAL', 'SUBSCRIPTION', 'BORROWED', 'RENTAL')", name='ck_acquisition_type'),
        sa.CheckConstraint('priority >= 1 AND priority <= 5', name='ck_priority_range'),
        sa.CheckConstraint('acquired_at <= CURRENT_TIMESTAMP', name='ck_acquired_not_future')
    )
    
    # Game Playthrough - individual play sessions
    op.create_table('game_playthrough',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.String(255), nullable=False, comment='AWS Cognito sub'),
        sa.Column('game_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('collection_id', postgresql.UUID(as_uuid=True), nullable=True, comment='Optional link to collection'),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('started_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('completed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('play_time_hours', sa.NUMERIC(8,2), nullable=True),
        sa.Column('playthrough_type', sa.String(100), nullable=True, comment='First Run, NG+, Speedrun, etc.'),
        sa.Column('difficulty', sa.String(50), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.current_timestamp()),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['collection_id'], ['user_game_collection.id'], ondelete='SET NULL'),
        sa.CheckConstraint("status IN ('PLANNING', 'PLAYING', 'COMPLETED', 'DROPPED', 'ON_HOLD', 'MASTERED')", name='ck_playthrough_status'),
        sa.CheckConstraint('rating IS NULL OR (rating >= 1 AND rating <= 10)', name='ck_rating_range'),
        sa.CheckConstraint('play_time_hours IS NULL OR play_time_hours >= 0', name='ck_positive_play_time'),
        sa.CheckConstraint('completed_at IS NULL OR started_at IS NULL OR completed_at > started_at', name='ck_completion_date_logic')
    )

def downgrade():
    op.drop_table('game_playthrough')
    op.drop_table('user_game_collection')
    op.drop_table('games')
```

### Phase 2: Performance Indexes
Add all performance-critical indexes.

```python
# Migration: 002_add_performance_indexes.py
"""Add performance indexes for filtering and searching

Revision ID: 002_add_performance_indexes
Revises: 001_initial_schema
Create Date: 2024-03-15 11:00:00.000000

"""

def upgrade():
    # Games indexes - for search and lookup
    op.create_index('idx_games_igdb_id', 'games', ['igdb_id'], unique=True, postgresql_where=sa.text('igdb_id IS NOT NULL'))
    op.create_index('idx_games_title_search', 'games', [sa.text("to_tsvector('english', title)")], postgresql_using='gin')
    op.create_index('idx_games_release_date', 'games', ['release_date'])
    op.create_index('idx_games_created_at', 'games', ['created_at'])
    
    # Full-text search across title and description
    op.create_index('idx_games_fulltext_search', 'games', 
        [sa.text("to_tsvector('english', coalesce(title, '') || ' ' || coalesce(description, ''))")], 
        postgresql_using='gin')
    
    # Collection indexes - critical for user filtering
    op.create_index('idx_collection_user_id', 'user_game_collection', ['user_id'])
    op.create_index('idx_collection_user_platform', 'user_game_collection', ['user_id', 'platform'])
    op.create_index('idx_collection_user_priority', 'user_game_collection', ['user_id', 'priority'], 
        postgresql_where=sa.text('priority IS NOT NULL'))
    op.create_index('idx_collection_user_acquired', 'user_game_collection', ['user_id', 'acquired_at'])
    op.create_index('idx_collection_active', 'user_game_collection', ['user_id', 'is_active'])
    
    # Composite indexes for common filter combinations
    op.create_index('idx_collection_platform_priority', 'user_game_collection', 
        ['user_id', 'platform', 'priority'])
    op.create_index('idx_collection_platform_acquired', 'user_game_collection', 
        ['user_id', 'platform', 'acquired_at'])
    op.create_index('idx_collection_active_platform', 'user_game_collection', 
        ['user_id', 'is_active', 'platform'], 
        postgresql_where=sa.text('is_active = true'))
    
    # Playthrough indexes - for status tracking and analytics
    op.create_index('idx_playthrough_user_id', 'game_playthrough', ['user_id'])
    op.create_index('idx_playthrough_user_status', 'game_playthrough', ['user_id', 'status'])
    op.create_index('idx_playthrough_user_platform', 'game_playthrough', ['user_id', 'platform'])
    op.create_index('idx_playthrough_user_rating', 'game_playthrough', ['user_id', 'rating'], 
        postgresql_where=sa.text('rating IS NOT NULL'))
    op.create_index('idx_playthrough_user_completed', 'game_playthrough', ['user_id', 'completed_at'], 
        postgresql_where=sa.text('completed_at IS NOT NULL'))
    op.create_index('idx_playthrough_user_updated', 'game_playthrough', ['user_id', 'updated_at'])
    op.create_index('idx_playthrough_game_user', 'game_playthrough', ['game_id', 'user_id'])
    
    # Composite indexes for advanced filtering
    op.create_index('idx_playthrough_status_platform', 'game_playthrough', 
        ['user_id', 'status', 'platform'])
    op.create_index('idx_playthrough_status_rating', 'game_playthrough', 
        ['user_id', 'status', 'rating'])
    op.create_index('idx_playthrough_completed_rating', 'game_playthrough', 
        ['user_id', 'completed_at', 'rating'], 
        postgresql_where=sa.text('completed_at IS NOT NULL'))

def downgrade():
    # Drop indexes in reverse order
    indexes_to_drop = [
        'idx_playthrough_completed_rating',
        'idx_playthrough_status_rating', 
        'idx_playthrough_status_platform',
        'idx_playthrough_game_user',
        'idx_playthrough_user_updated',
        'idx_playthrough_user_completed',
        'idx_playthrough_user_rating',
        'idx_playthrough_user_platform',
        'idx_playthrough_user_status',
        'idx_playthrough_user_id',
        'idx_collection_active_platform',
        'idx_collection_platform_acquired',
        'idx_collection_platform_priority',
        'idx_collection_active',
        'idx_collection_user_acquired',
        'idx_collection_user_priority',
        'idx_collection_user_platform',
        'idx_collection_user_id',
        'idx_games_fulltext_search',
        'idx_games_created_at',
        'idx_games_release_date',
        'idx_games_title_search',
        'idx_games_igdb_id'
    ]
    
    for index_name in indexes_to_drop:
        op.drop_index(index_name)
```

### Phase 3: Database Functions and Triggers
Add automated functionality and triggers.

```python
# Migration: 003_add_functions_triggers.py
"""Add database functions and triggers

Revision ID: 003_add_functions_triggers  
Revises: 002_add_performance_indexes
Create Date: 2024-03-15 11:30:00.000000

"""

def upgrade():
    # Automatic timestamp update function
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    
    # Apply timestamp triggers to all tables
    op.execute("""
        CREATE TRIGGER update_games_updated_at 
        BEFORE UPDATE ON games 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)
    
    op.execute("""
        CREATE TRIGGER update_collection_updated_at 
        BEFORE UPDATE ON user_game_collection 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)
    
    op.execute("""
        CREATE TRIGGER update_playthrough_updated_at 
        BEFORE UPDATE ON game_playthrough 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)
    
    # Game search function with ranking
    op.execute("""
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
    """)

def downgrade():
    op.execute("DROP FUNCTION IF EXISTS search_games(TEXT, VARCHAR(255), INTEGER);")
    op.execute("DROP TRIGGER IF EXISTS update_playthrough_updated_at ON game_playthrough;")
    op.execute("DROP TRIGGER IF EXISTS update_collection_updated_at ON user_game_collection;")
    op.execute("DROP TRIGGER IF EXISTS update_games_updated_at ON games;")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column();")
```

### Phase 4: Session Management
Add session storage for authentication.

```python
# Migration: 004_add_session_management.py
"""Add session management for authentication

Revision ID: 004_add_session_management
Revises: 003_add_functions_triggers
Create Date: 2024-03-15 12:00:00.000000

"""

def upgrade():
    # User sessions table for secure authentication
    op.create_table('user_sessions',
        sa.Column('session_id', sa.String(64), primary_key=True),
        sa.Column('user_id', sa.String(255), nullable=False, comment='AWS Cognito sub'),
        sa.Column('access_token', sa.Text(), nullable=False),
        sa.Column('refresh_token', sa.Text(), nullable=False),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.current_timestamp())
    )
    
    # Session indexes for performance
    op.create_index('idx_sessions_user_id', 'user_sessions', ['user_id'])
    op.create_index('idx_sessions_expires_at', 'user_sessions', ['expires_at'])
    op.create_index('idx_sessions_cleanup', 'user_sessions', ['expires_at'], 
        postgresql_where=sa.text('expires_at < CURRENT_TIMESTAMP'))
    
    # Session cleanup function
    op.execute("""
        CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
        RETURNS INTEGER AS $$
        DECLARE
            deleted_count INTEGER;
        BEGIN
            DELETE FROM user_sessions WHERE expires_at < CURRENT_TIMESTAMP;
            GET DIAGNOSTICS deleted_count = ROW_COUNT;
            RETURN deleted_count;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Add session update trigger
    op.execute("""
        CREATE TRIGGER update_sessions_updated_at 
        BEFORE UPDATE ON user_sessions 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)

def downgrade():
    op.execute("DROP TRIGGER IF EXISTS update_sessions_updated_at ON user_sessions;")
    op.execute("DROP FUNCTION IF EXISTS cleanup_expired_sessions();")
    op.drop_table('user_sessions')
```

### Phase 5: Database Views for Common Queries
Add materialized views for performance.

```python
# Migration: 005_add_database_views.py
"""Add database views for common query patterns

Revision ID: 005_add_database_views
Revises: 004_add_session_management
Create Date: 2024-03-15 12:30:00.000000

"""

def upgrade():
    # Active collection view with game details
    op.execute("""
        CREATE VIEW active_collection AS
        SELECT 
            c.id,
            c.user_id,
            c.game_id,
            g.title,
            g.cover_image_id,
            g.release_date,
            g.main_story,
            g.main_extra,
            g.completionist,
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
    """)
    
    # Playthrough summary with calculated fields
    op.execute("""
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
                WHEN p.play_time_hours IS NOT NULL AND g.main_story IS NOT NULL AND g.main_story > 0
                THEN ROUND((p.play_time_hours / g.main_story) * 100, 1)
                ELSE NULL
            END AS completion_percentage
        FROM game_playthrough p
        JOIN games g ON p.game_id = g.id;
    """)
    
    # User statistics aggregated view (materialized for performance)
    op.execute("""
        CREATE MATERIALIZED VIEW user_game_stats AS
        SELECT 
            COALESCE(c.user_id, p.user_id) as user_id,
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
            END as completion_rate_percent,
            
            -- Last activity
            MAX(p.updated_at) as last_activity
        FROM user_game_collection c
        FULL OUTER JOIN game_playthrough p ON c.user_id = p.user_id
        WHERE c.user_id IS NOT NULL OR p.user_id IS NOT NULL
        GROUP BY COALESCE(c.user_id, p.user_id);
    """)
    
    # Create index on materialized view
    op.create_index('idx_user_stats_user_id', 'user_game_stats', ['user_id'], unique=True)
    
    # Function to refresh user stats
    op.execute("""
        CREATE OR REPLACE FUNCTION refresh_user_stats(target_user_id VARCHAR(255) DEFAULT NULL)
        RETURNS VOID AS $$
        BEGIN
            IF target_user_id IS NOT NULL THEN
                -- Refresh stats for specific user (not supported in standard PostgreSQL)
                REFRESH MATERIALIZED VIEW CONCURRENTLY user_game_stats;
            ELSE
                -- Refresh all stats
                REFRESH MATERIALIZED VIEW CONCURRENTLY user_game_stats;
            END IF;
        END;
        $$ LANGUAGE plpgsql;
    """)

def downgrade():
    op.execute("DROP FUNCTION IF EXISTS refresh_user_stats(VARCHAR(255));")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS user_game_stats;")
    op.execute("DROP VIEW IF EXISTS playthrough_summary;")
    op.execute("DROP VIEW IF EXISTS active_collection;")
```

## Development Workflow

### Creating New Migrations
```bash
# Generate migration from model changes
alembic revision --autogenerate -m "Add feature description"

# Create empty migration
alembic revision -m "Manual schema change"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Check current version
alembic current

# Show migration history
alembic history --verbose
```

### Testing Migrations
```python
# tests/test_migrations.py
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

@pytest.fixture
def alembic_config():
    return Config("alembic.ini")

@pytest.fixture  
def test_engine():
    engine = create_engine("postgresql://postgres:postgres@0.0.0.0:6432/test_play_later_db")
    yield engine
    engine.dispose()

def test_migrations_up_and_down(alembic_config, test_engine):
    """Test complete migration cycle."""
    
    # Apply all migrations
    command.upgrade(alembic_config, "head")
    
    # Verify core tables exist
    with test_engine.connect() as conn:
        result = conn.execute(text("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """))
        tables = [row[0] for row in result]
        
        expected_tables = [
            'games', 
            'user_game_collection', 
            'game_playthrough', 
            'user_sessions'
        ]
        
        for table in expected_tables:
            assert table in tables, f"Table {table} not found"
    
    # Test rollback to base
    command.downgrade(alembic_config, "base")
    
    # Verify tables are removed
    with test_engine.connect() as conn:
        result = conn.execute(text("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public'
        """))
        tables = [row[0] for row in result]
        
        for table in expected_tables:
            assert table not in tables, f"Table {table} still exists after downgrade"

def test_database_constraints(test_engine):
    """Test that database constraints work correctly."""
    
    # Apply migrations
    command.upgrade(alembic_config, "head")
    
    with test_engine.connect() as conn:
        # Insert valid game
        game_result = conn.execute(text("""
            INSERT INTO games (title, igdb_id) 
            VALUES ('Test Game', 12345) 
            RETURNING id
        """))
        game_id = game_result.fetchone()[0]
        
        # Insert valid collection entry
        conn.execute(text("""
            INSERT INTO user_game_collection 
            (user_id, game_id, platform, acquisition_type, acquired_at)
            VALUES ('test_user_123', :game_id, 'PS5', 'DIGITAL', NOW())
        """), {'game_id': game_id})
        
        # Test constraint violations
        with pytest.raises(Exception):  # Invalid acquisition type
            conn.execute(text("""
                INSERT INTO user_game_collection 
                (user_id, game_id, platform, acquisition_type, acquired_at)
                VALUES ('test_user_456', :game_id, 'PS5', 'INVALID', NOW())
            """), {'game_id': game_id})
        
        with pytest.raises(Exception):  # Invalid priority
            conn.execute(text("""
                INSERT INTO user_game_collection 
                (user_id, game_id, platform, acquisition_type, acquired_at, priority)
                VALUES ('test_user_789', :game_id, 'Steam', 'DIGITAL', NOW(), 10)
            """), {'game_id': game_id})
        
        conn.rollback()
```

## Production Deployment

### Deployment Strategy
```bash
#!/bin/bash
# scripts/deploy_migration.sh

set -e

echo "Starting migration deployment..."

# 1. Backup current database
echo "Creating backup..."
pg_dump $DATABASE_URL > "backup_$(date +%Y%m%d_%H%M%S).sql"

# 2. Run migrations
echo "Running migrations..."
alembic upgrade head

# 3. Refresh materialized views
echo "Refreshing materialized views..."
psql $DATABASE_URL -c "SELECT refresh_user_stats();"

# 4. Verify deployment
echo "Running verification..."
python scripts/verify_migration.py

echo "Migration deployment completed successfully!"
```

### Health Checks
```python
# scripts/verify_migration.py
"""Verify migration deployment health."""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def verify_migration():
    engine = create_async_engine(DATABASE_URL)
    
    async with engine.connect() as conn:
        # Check tables exist
        result = await conn.execute(text("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public'
        """))
        tables = [row[0] for row in result]
        
        required_tables = ['games', 'user_game_collection', 'game_playthrough', 'user_sessions']
        for table in required_tables:
            assert table in tables, f"Required table {table} missing"
        
        # Check indexes exist
        result = await conn.execute(text("""
            SELECT indexname FROM pg_indexes 
            WHERE schemaname = 'public' AND indexname LIKE 'idx_%'
        """))
        indexes = [row[0] for row in result]
        
        # Check critical indexes exist
        critical_indexes = [
            'idx_collection_user_id',
            'idx_playthrough_user_status',
            'idx_games_title_search'
        ]
        for index in critical_indexes:
            assert index in indexes, f"Critical index {index} missing"
        
        # Test basic functionality
        await conn.execute(text("INSERT INTO games (title) VALUES ('Migration Test Game')"))
        result = await conn.execute(text("SELECT COUNT(*) FROM games WHERE title = 'Migration Test Game'"))
        count = result.scalar()
        assert count == 1, "Basic insert/select not working"
        
        await conn.rollback()  # Cleanup test data
    
    await engine.dispose()
    print("✅ Migration verification passed!")

if __name__ == "__main__":
    asyncio.run(verify_migration())
```

This fresh migration approach provides a clean, maintainable database schema that can evolve incrementally as the application grows, without the complexity of migrating from existing data structures.