# Play Later API Documentation

## Overview

The Play Later API is a FastAPI-based backend service for managing gaming backlogs, collections, and playthroughs. It provides a robust foundation for tracking games across multiple platforms with support for multiple playthroughs per game.

## Architecture

This API is built with:
- **FastAPI** - Modern Python web framework with automatic OpenAPI generation
- **SQLAlchemy** - Database ORM with PostgreSQL support
- **Pydantic** - Data validation and serialization
- **AWS Cognito** - Authentication and user management
- **Alembic** - Database migrations

## Core Concepts

### Game
Central entity representing game metadata from IGDB with local caching to minimize external API calls.

### Collection
Represents games owned by a user on specific platforms. Separates ownership from playthroughs.

### Playthrough  
Individual play sessions/attempts by a user. Supports multiple playthroughs per game with different statuses and platforms.

## Key Features

- **Multi-platform Support** - Track games across Steam, PlayStation, Xbox, Switch, etc.
- **Multiple Playthroughs** - Replay games with separate tracking for each attempt
- **Advanced Filtering** - Complex queries by platform, status, rating, completion date, etc.
- **Authentication** - Secure user isolation via AWS Cognito JWT tokens
- **Performance Optimized** - Indexed queries for fast filtering and pagination

## API Structure

```
/api/v1/
├── games/           # Game metadata and search
├── collection/      # User game ownership
├── playthroughs/    # Individual play sessions
├── auth/           # Authentication utilities
└── health/         # System health checks
```

## Documentation Structure

- [`architecture/`](./architecture/) - Core entity design and system architecture
- [`api-spec/`](./api-spec/) - Detailed API endpoint specifications
- [`database/`](./database/) - Database schema and migration documentation

## Development

### Prerequisites
- Python 3.9+
- Poetry for dependency management
- PostgreSQL database
- AWS Cognito user pool

### Getting Started

1. **Install dependencies**:
   ```bash
   poetry install
   ```

2. **Setup environment**:
   ```bash
   cp .env.example .env
   # Configure database and AWS Cognito settings
   ```

3. **Run migrations**:
   ```bash
   poetry run alembic upgrade head
   ```

4. **Start development server**:
   ```bash
   poetry run uvicorn main:app --reload
   ```

5. **Access API docs**:
   - OpenAPI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## Schema Generation

This API automatically generates OpenAPI schemas for frontend TypeScript client generation:

```bash
# Generate schema
poetry run generate-schema

# Frontend will automatically consume from contract/openapi.json
```

## Authentication

All user-specific endpoints require AWS Cognito JWT tokens:

```bash
Authorization: Bearer <cognito-jwt-token>
```

User identification is handled via the `sub` claim from Cognito tokens.