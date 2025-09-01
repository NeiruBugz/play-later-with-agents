# Repository Guidelines

## Project Structure & Modules
- `web/`: React + Vite + TypeScript app. Routes in `src/routes`, components in `src/components`, utilities in `src/lib`. API client is generated into `src/api/`.
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
  - Run locally: `cd api && poetry run uvicorn main:app --reload --port 8000`
  - Format Python: `cd api && poetry run ruff format`
- Git hooks: `pnpm postinstall` installs Lefthook. Pre-commit runs web lint, API format, and `terraform fmt` for `infra/`.

## Coding Style & Naming
- TypeScript/React: 2-space indent; components in PascalCase (e.g., `Header.tsx`). File-based routing under `src/routes` (e.g., `__root.tsx`, `index.tsx`).
- ESLint config: see `web/eslint.config.js` (React + hooks rules). TS is strict (`web/tsconfig.json`).
- Python: PEP 8 via Ruff formatter; keep functions/modules in `snake_case`.

## Testing Guidelines
- Web: Vitest + Testing Library (`.test.ts`/`.test.tsx` colocated with code). Run with `pnpm -F web test`.
- API: No tests defined yet — prefer pytest under `api/` when introduced.

## Commits & Pull Requests
- Conventional Commits enforced by commitlint. Examples:
  - `feat(web): add homepage header`
  - `fix(api): handle missing route`
- PRs: include a clear description, link issues, add screenshots for UI changes, and ensure hooks pass locally.

## Contract & Infra Tips
- After editing `contract/openapi.json`, regenerate the client: `pnpm -F web gen:api`.
- Format Terraform: `terraform fmt -recursive infra`. Run plans inside `infra/`: `terraform init && terraform plan`.

