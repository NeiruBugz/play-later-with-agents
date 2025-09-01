# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Architecture

This is a monorepo using pnpm workspaces with 4 main packages:
- `web/` - TanStack React frontend with Vite, TypeScript, Tailwind CSS, and Shadcn UI
- `api/` - FastAPI Python backend using Poetry for dependency management
- `contract/` - OpenAPI schema definitions (currently empty JSON file)
- `infra/` - Terraform infrastructure as code

## Essential Commands

### Development Setup
```bash
pnpm install                    # Install all workspace dependencies
```

### Web Frontend (TanStack React)
```bash
# From root or cd web/
pnpm --filter web dev           # Start dev server on port 3000
pnpm --filter web start         # Alias for dev
pnpm --filter web build         # Production build with TypeScript check
pnpm --filter web test          # Run Vitest tests
pnpm --filter web lint          # ESLint check
pnpm --filter web gen:api       # Generate API client from OpenAPI schema
```

### Python API (FastAPI)
```bash
cd api/
poetry install                  # Install Python dependencies
poetry run uvicorn main:app --reload  # Start development server
poetry run ruff format          # Format Python code
```

### Infrastructure
```bash
terraform fmt -recursive infra  # Format Terraform files
```

## Code Quality & Pre-commit

This project uses Lefthook for git hooks with the following checks:
- Frontend linting before commits
- Python formatting with Ruff before commits
- Terraform formatting before commits
- Conventional commit message linting

Conventional commits are enforced using commitlint. Follow the format: `type(scope): description`

## Key Technologies & Conventions

### Frontend (web/)
- **Framework**: TanStack React with file-based routing in `src/routes/`
- **Styling**: Tailwind CSS v4 with Shadcn UI components
- **Testing**: Vitest with React Testing Library
- **API Client**: Generated from OpenAPI using @hey-api/openapi-ts
- **Dev Tools**: TanStack Router Devtools enabled

### Backend (api/)
- **Framework**: FastAPI with Python 3.9+
- **Package Manager**: Poetry
- **Code Formatting**: Ruff

### Shadcn UI Components
Add new components using: `pnpx shadcn@latest add [component-name]`

## API Client Generation

The frontend generates TypeScript API clients from the OpenAPI schema:
```bash
pnpm --filter web gen:api
```
This reads from `contract/openapi.json` and outputs to `web/src/api/`