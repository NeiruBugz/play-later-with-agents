# API - FastAPI Backend

FastAPI backend service for the Play Later application with PostgreSQL database integration.

## 🏗️ Architecture

- **Framework**: FastAPI with Python 3.9+
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Migrations**: Alembic for database schema management
- **Testing**: pytest with TestClient
- **Code Quality**: Ruff for formatting and linting
- **Package Management**: Poetry

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Poetry
- PostgreSQL database running on port 6432

### Setup

```bash
# Install dependencies
poetry install

# Activate virtual environment
source .venv/bin/activate

# Create environment file
echo "DATABASE_URL=postgresql://postgres:postgres@0.0.0.0:6432/play-later-db" > .env

# Run database migrations
PYTHONPATH=. python -m alembic upgrade head
```

### Development Server

```bash
# Start development server with auto-reload
poetry run uvicorn app.main:app --reload

# Server will be available at http://localhost:8000
# API documentation at http://localhost:8000/docs
```

## 🧪 Testing

Follow Test-Driven Development (TDD) practices:

```bash
# Run all tests
poetry run pytest

# Run tests with verbose output
poetry run pytest -v

# Run tests with coverage
poetry run pytest --cov

# Run specific test file
poetry run pytest tests/test_example.py
```

### Testing Guidelines

- Write tests first before implementing functionality
- Use FastAPI's TestClient for API endpoint testing
- Create database fixtures for consistent test state
- Test both success and error scenarios
- Mock external dependencies appropriately

## 🗄️ Database Management

### Migrations

```bash
# Check current migration version
source .venv/bin/activate && PYTHONPATH=. python -m alembic current

# View migration history
source .venv/bin/activate && PYTHONPATH=. python -m alembic history

# Create new migration
source .venv/bin/activate && PYTHONPATH=. python -m alembic revision --autogenerate -m "description"

# Run migrations
source .venv/bin/activate && PYTHONPATH=. python -m alembic upgrade head
```

### Database Configuration

Database connection is configured via environment variables:

```bash
DATABASE_URL=postgresql://postgres:postgres@0.0.0.0:6432/play-later-db
```

## 📋 API Documentation

### OpenAPI Schema Generation

```bash
# Generate OpenAPI schema to contract/openapi.json
poetry run generate-schema
```

The API documentation is automatically available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## 🔧 Code Quality

### Formatting

```bash
# Format code with Ruff
poetry run ruff format

# Check formatting
poetry run ruff format --check
```

### Code Style Guidelines

- Follow PEP 8 style guide (enforced by Ruff)
- Use type hints for all function parameters and returns
- Implement proper error handling with HTTP status codes
- Use SQLAlchemy models for database operations
- Follow FastAPI dependency injection patterns
- Use Pydantic models for request/response validation

## 📁 Project Structure

```
api/
├── alembic/                # Database migrations
├── app/                    # Application code
│   ├── core/              # Core functionality
│   ├── models/            # SQLAlchemy models
│   ├── schemas/           # Pydantic schemas
│   ├── services/          # Business logic
│   ├── routers/           # API route handlers
│   └── main.py           # FastAPI application entry point
├── scripts/               # Utility scripts
├── tests/                # Test files
├── docs/                 # Additional documentation
├── pyproject.toml        # Poetry configuration
├── alembic.ini          # Alembic configuration
├── logging.yaml         # Logging configuration
└── main.py              # Development server entry point
```

## 🚀 Deployment

The API is containerized and ready for deployment. Configuration is managed through environment variables.

### Environment Variables

- `DATABASE_URL`: PostgreSQL connection string
- `DEBUG`: Enable debug mode (default: False)
- `LOG_LEVEL`: Logging level (default: INFO)

## 📚 Dependencies

### Production Dependencies

- **FastAPI**: Modern web framework for APIs
- **uvicorn**: ASGI server
- **SQLAlchemy**: SQL toolkit and ORM
- **psycopg2-binary**: PostgreSQL adapter
- **pydantic-settings**: Settings management
- **PyYAML**: YAML parsing

### Development Dependencies

- **pytest**: Testing framework
- **httpx**: HTTP client for testing
- **ruff**: Fast Python linter and formatter
- **alembic**: Database migration tool

## 🐛 Troubleshooting

### Common Issues

1. **Database connection errors**: Ensure PostgreSQL is running on port 6432
2. **Import errors**: Make sure virtual environment is activated
3. **Migration failures**: Check database permissions and connectivity
4. **Test failures**: Ensure database is in clean state with migrations applied

### Debug Mode

Enable detailed error messages and auto-reload:

```bash
# Set environment variable
export DEBUG=true

# Or use in development
poetry run uvicorn app.main:app --reload --log-level debug
```