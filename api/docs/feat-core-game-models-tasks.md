# Feature Plan: Core Game/Collection/Playthrough API

## Scope
- Implement backend v1 API per `api/docs/api-spec/*` (collections, playthroughs, stats, bulk ops) with auth, filtering, and validations.
- Keep OpenAPI contract in sync via `poetry run generate-schema` and regenerate the web client via `pnpm -F web gen:api`.
- Each task is atomic, validated by automated tests, and committed using Conventional Commits.

## Testing Strategy
- Service-level tests using pytest hit FastAPI app with TestClient, covering success and error paths for each endpoint.
- Prefer test-first for each task; remove reliance on manual cURL checks.
- Lightweight factories/fixtures for users, games, collection items, and playthroughs.

## Per-Task Checklist
- Write or update service-level tests (pytest) for the unit/endpoint you are changing.
- Implement the minimal code to make tests pass.
- Run: `cd api && poetry run ruff format` and `pytest`.
- Update contract: `poetry run generate-schema` then `pnpm -F web gen:api`.
- Commit with the specified Conventional Commit message.

## Tasks

### [x] Task 0 – Test environment bootstrap
- Add pytest to dev deps, `conftest.py` with FastAPI TestClient, basic factories, and helpers.
- Seed minimal in-memory DB/test DB setup (depending on ORM wiring in Task 3/7).
- Validate: `pytest` runs and a sample health test passes.
- Commit: `test(api): bootstrap pytest, fixtures, and sample health test`

### [x] Task 1 – Add API versioning
- Introduce `/api/v1` router prefix and tags; wire `health` under v1.
- Validate: `GET /api/v1/health` returns HealthResponse in tests; schema shows v1 paths.
- Commit: `feat(api): introduce /api/v1 base router`

### [x] Task 2 – Base error model
- Add standard error response schema and exception handlers to match docs (422/404/401 shape with `request_id`).
- Validate: tests assert error body structure and status codes.
- Commit: `feat(api): add standard error responses`

### [x] Task 3 – Settings + DB wiring
- Add SQLAlchemy engine/session factory and config (env). No endpoints yet.
- Validate: app boots; session dependency works in tests.
- Commit: `chore(api): configure database engine and session`

### [x] Task 4 – Auth dependency stub
- Implement dependency that extracts user ID (Cognito later, stub now) and enforce auth on protected routes.
- Validate: protected test route returns 401 without session, 200 with stub.
- Commit: `feat(api): add auth dependency and protect v1 routes`

### [x] Task 5 – Session model (optional now)
- Add minimal session storage schema per docs.
- Validate: session create/read tested via utility functions.
- Commit: `feat(api): add session storage schema`

### [x] Task 6 – Pydantic schemas
- Define DTOs for Game, CollectionItem, Playthrough, enums, pagination/results, stats as per docs.
- Validate: openapi includes schemas; tests import and validate dataclasses.
- Commit: `feat(api): add DTOs for games, collection, playthroughs`

### [x] Task 7 – ORM models + migration
- Progress: ORM models implemented and validated via tests; Alembic migration pending.
- SQLAlchemy models and initial Alembic migration for games, collection, playthroughs.
- Validate: migration runs in test setup; tables exist; simple CRUD tested.
- Commit: `feat(api): add ORM models and initial migration`

### [x] Task 8 – GET /collection
- Implement list with filtering, sorting, pagination; auth enforced.
- Validate: tests cover filters, pagination, unauthorized.
- Commit: `feat(api): list user collection with filters`

### [x] Task 9 – POST /collection
- Create item with validation (unique user+game+platform).
- Validate: 201 on create; 409 on duplicate; invalid data 422.
- Commit: `feat(api): add collection create endpoint`

### [x] Task 10 – GET /collection/{id}
- Fetch by ID with embedded game and playthrough summary.
- Validate: 200/404 cases.
- Commit: `feat(api): add collection get by id`

### [x] Task 11 – PUT /collection/{id}
- Update mutable fields only; enforce rules.
- Validate: 200; 422 on invalid priority; immutable fields rejected.
- Commit: `feat(api): update collection item`

### [x] Task 12 – DELETE /collection/{id}
- Soft delete by default; optional hard delete flag with safeguards.
- Validate: 200; is_active=false on soft; 404 not owned.
- Commit: `feat(api): delete collection item (soft/hard)`

### Task 13 – POST /collection/bulk
- Implement supported actions with partial success (207) semantics.
- Validate: mixed IDs return 207; all good returns 200.
- Commit: `feat(api): bulk collection operations`

### Task 14 – GET /collection/stats
- Return counts by platform, acquisition, priority, value estimate.
- Validate: deterministic aggregates in tests.
- Commit: `feat(api): collection statistics endpoint`

### Task 15 – GET /playthroughs
- List with advanced filters (status, platform, rating, time, dates, search) and sorting.
- Validate: key filter combinations and pagination.
- Commit: `feat(api): list playthroughs with filters`

### Task 16 – POST /playthroughs
- Create with validation (exists, ownership, enums).
- Validate: 201; 404 on invalid refs; 422 invalid payload.
- Commit: `feat(api): create playthrough`

### Task 17 – GET /playthroughs/{id}
- Full detail with embedded game/collection and milestones.
- Validate: 200/404.
- Commit: `feat(api): get playthrough by id`

### Task 18 – PUT /playthroughs/{id}
- Update with business rules and valid status transitions.
- Validate: 422 on invalid transitions; 200 on valid; timestamps logic.
- Commit: `feat(api): update playthrough with rules`

### Task 19 – POST /playthroughs/{id}/complete
- Finalize with completion details and types.
- Validate: 200; 409 if already completed; data persisted.
- Commit: `feat(api): complete playthrough`

### Task 20 – DELETE /playthroughs/{id}
- Delete record.
- Validate: 200/404.
- Commit: `feat(api): delete playthrough`

### Task 21 – POST /playthroughs/bulk
- Implement bulk actions (status, platform, add_time, delete).
- Validate: 200/207 and per-item outcomes.
- Commit: `feat(api): bulk playthrough operations`

### Task 22 – GET /playthroughs/backlog
- Planning status and collection priority filters.
- Validate: 200; shape matches docs.
- Commit: `feat(api): backlog endpoint`

### Task 23 – GET /playthroughs/playing
- Active sessions by platform.
- Validate: 200 with expected fields.
- Commit: `feat(api): currently playing endpoint`

### Task 24 – GET /playthroughs/completed
- Completed list with year/rating/platform filters.
- Validate: 200; aggregates match fixtures.
- Commit: `feat(api): completed playthroughs endpoint`

### Task 25 – GET /playthroughs/stats
- Aggregate stats and top genres.
- Validate: numbers/averages computed correctly.
- Commit: `feat(api): playthrough statistics endpoint`

### Task 26 – Rate limiting
- Apply per-route limits per docs (stats/bulk stricter).
- Validate: exceeding thresholds returns 429 in tests.
- Commit: `feat(api): add per-route rate limits`

### Task 27 – Caching
- TTL cache for lists/items/stats; invalidate on mutations.
- Validate: cached responses and invalidation covered by tests.
- Commit: `feat(api): add response caching with invalidation`

### Task 28 – Logging and request IDs
- Structured logs and `request_id` in error body.
- Validate: tests assert `request_id` in errors; logs include IDs (smoke).
- Commit: `chore(api): add structured logging and request ids`

### Task 29 – Generate OpenAPI
- Run `poetry run generate-schema` after API changes.
- Validate: `contract/openapi.json` includes new paths/schemas.
- Commit: `chore(contract): update openapi schema`

### Task 30 – Regenerate web client
- Run `pnpm -F web gen:api`.
- Validate: generated SDK includes new endpoints.
- Commit: `chore(web): regenerate API client from contract`

### Task 31 – Docs alignment
- Ensure `api/docs` examples match responses.
- Validate: spot-check major sections.
- Commit: `docs(api): sync examples with implementation`

### Task 32 – Update AGENTS.md
- Document the test-first workflow, per-task checklist, and generation steps.
- Validate: content reflects the final process.
- Commit: `docs: update AGENTS.md with testing and contract flow`
