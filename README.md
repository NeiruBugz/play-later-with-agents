# Play Later - Build with Agents

A full-stack application for managing content to consume later, built with modern web technologies and AI agents.

## 🏗️ Architecture

This is a monorepo using pnpm workspaces with 4 main packages:

- **`web/`** - TanStack React frontend with Vite, TypeScript, Tailwind CSS, and Shadcn UI
- **`api/`** - FastAPI Python backend with PostgreSQL database
- **`contract/`** - OpenAPI schema definitions for API contracts
- **`infra/`** - Terraform infrastructure as code

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ and pnpm
- Python 3.9+ and Poetry
- PostgreSQL database running on port 6432

### Development Setup

```bash
# Install all workspace dependencies
pnpm install

# Set up API
cd api/
poetry install
source .venv/bin/activate
echo "DATABASE_URL=postgresql://postgres:postgres@0.0.0.0:6432/play-later-db" > .env

# Run database migrations
PYTHONPATH=. python -m alembic upgrade head

# Start development servers
pnpm --filter web dev     # Frontend on http://localhost:3000
poetry run uvicorn app.main:app --reload  # API on http://localhost:8000
```

## 📦 Package Scripts

### Frontend (web/)
```bash
pnpm --filter web dev      # Start dev server
pnpm --filter web build    # Production build
pnpm --filter web test     # Run tests
pnpm --filter web lint     # ESLint check
pnpm --filter web gen:api  # Generate API client
```

### Backend (api/)
```bash
cd api/
poetry run uvicorn app.main:app --reload  # Start dev server
poetry run pytest                         # Run tests
poetry run ruff format                     # Format code
poetry run generate-schema                 # Generate OpenAPI schema
```

## 🧪 Testing

Both frontend and backend follow Test-Driven Development (TDD) practices:

```bash
# Frontend tests
pnpm --filter web test

# Backend tests
cd api/ && source .venv/bin/activate && pytest
```

## 🚢 Deployment

Infrastructure is managed with Terraform in the `infra/` directory:

```bash
terraform fmt -recursive infra  # Format Terraform files
```

## 📚 Documentation

For detailed development guidelines, see:
- [CLAUDE.md](./CLAUDE.md) - Development guidelines for Claude Code
- [web/README.md](./web/README.md) - Frontend-specific documentation
- [api/README.md](./api/README.md) - Backend-specific documentation
- [infra/README.md](./infra/README.md) - Infrastructure documentation

## 🔧 Code Quality

This project uses:
- **Lefthook** for git hooks
- **Commitlint** for conventional commits
- **ESLint** for frontend linting
- **Ruff** for Python formatting
- **TypeScript** strict mode

## 🤖 AI Agents

This project is designed to work with AI development assistants. See [AGENTS.md](./AGENTS.md) and [GEMINI.md](./GEMINI.md) for agent-specific guidelines.

## 📄 License

ISC License