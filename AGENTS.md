# Repository Guidelines

## Project Structure & Modules
- `web/`: React + Vite + TypeScript app. Routes in `src/routes`, components in `src/components`, utilities in `src/lib`. API client is generated into `src/shared/api/generated/`. Styling: Tailwind CSS v4 + Shadcn UI.
- `api/`: FastAPI service (`main.py`) managed by Poetry; Python formatting via Ruff.
- `contract/`: OpenAPI contract (`openapi.json`) — single source of truth for the web client.
- `infra/`: Terraform configuration (`*.tf`).

## Build, Test, and Development
- Install workspace tools: `pnpm install`. Backend deps: `cd api && poetry install`.
- Web
  - Dev: `pnpm -F web dev` (http://localhost:3000)
  - Build: `pnpm -F web build`
  - Test: `pnpm -F web test`
  - Lint: `pnpm -F web lint`
  - Generate API client from contract: `pnpm -F web run gen:api`
- API
  - Run locally: `cd api && poetry run uvicorn app.main:app --reload --port 8000`
  - Format Python: `cd api && poetry run ruff format`
  - Tests: `cd api && pytest`
- OpenAPI schema
  - Generate from API: `cd api && poetry run generate-schema` (writes to `contract/openapi.json`)
- Git hooks: `pnpm postinstall` installs Lefthook. Pre-commit runs web lint, API format, and `terraform fmt` for `infra/`.
  - Additionally, on Python changes, pre-commit regenerates the OpenAPI schema and web API client (`api/scripts/generate_schema.py` then `pnpm -F web gen:api`).

## Database & Migrations
- Default DB: SQLite file at `api/test.db` if `DATABASE_URL` is not set.
- PostgreSQL: set `DATABASE_URL` in `api/.env` (e.g., `postgresql://user:pass@host:port/db`).
- Alembic migrations (from `api/` with venv active):
  - Upgrade: `PYTHONPATH=. python -m alembic upgrade head`
  - Current: `PYTHONPATH=. python -m alembic current`
  - History: `PYTHONPATH=. python -m alembic history`
  - New revision: `PYTHONPATH=. python -m alembic revision --autogenerate -m "desc"`

## Coding Style & Naming
- TypeScript/React: 2-space indent; components in PascalCase (e.g., `Header.tsx`). File-based routing under `src/routes` (e.g., `__root.tsx`, `index.tsx`).
- ESLint config: see `web/eslint.config.js` (React + hooks rules). TS is strict (`web/tsconfig.json`).
- Python: PEP 8 via Ruff formatter; keep functions/modules in `snake_case`.
- UI: Prefer Shadcn UI components. Add components with `pnpx shadcn@latest add <component>`.

## Testing Guidelines
- Web: Vitest + Testing Library (`.test.ts`/`.test.tsx` colocated with code). Run with `pnpm -F web test`.
- API: Pytest tests live under `api/tests`. Run with `cd api && pytest`.

## Commits & Pull Requests
- Conventional Commits enforced by commitlint. Examples:
  - `feat(web): add homepage header`
  - `fix(api): handle missing route`
- PRs: include a clear description, link issues, add screenshots for UI changes, and ensure hooks pass locally.

## Contract & Infra Tips
- After editing `contract/openapi.json`, regenerate the client: `pnpm -F web gen:api`.
- Format Terraform: `terraform fmt -recursive infra`. Run plans inside `infra/`: `terraform init && terraform plan`.

## Gotchas
- Regenerate the API client after backend schema changes (pre-commit does this automatically on Python changes).
- Activate the Python venv for backend CLI tools: `source api/.venv/bin/activate`.
- Ensure database is reachable and migrations are applied when running against PostgreSQL.
