# DB → Domain Mapping Layer Plan

This document proposes a focused mapping layer to convert SQLAlchemy ORM models (DB) into Pydantic schemas (Domain) used by the API responses. It fits between the services and the I/O layer, without adding a full repository pattern.

**Why Mappers**
- **Decoupling:** Keep persistence details (SQLAlchemy types, lazy relationships) isolated from response shapes.
- **Reuse:** Centralize repeated projections (e.g., `Game -> GameSummary/Detail`, `Playthrough -> ListItem/Response`).
- **Consistency:** One source of truth for how fields are derived/serialized (enums, optional fields, derived data).
- **Testability:** Pure, small functions that are easy to unit test without the DB/session.
- **Easier refactors:** Change response shapes or DB fields in one place.

**Scope**
- **Inputs:** Loaded ORM instances from `app.db_models` (`Game`, `CollectionItem`, `Playthrough`).
- **Outputs:** Pydantic models from `app.schemas` (`GameSummary`, `GameDetail`, `PlaythroughListItem`, `PlaythroughResponse`, `CollectionItemExpanded`, etc.).
- **Non-goals:** No DB access, no validation/business rules, no side effects. Keep mappers pure and synchronous.

**Design**
- **Location:** `app/mappers/` with per-aggregate modules.
  - `app/mappers/game_mapper.py`
  - `app/mappers/playthrough_mapper.py`
  - `app/mappers/collection_mapper.py`
  - `app/mappers/__init__.py`
- **API shape:** Small, composable functions.
  - `to_game_summary(game: Game) -> GameSummary`
  - `to_game_detail(game: Game) -> GameDetail`
  - `to_playthrough_response(pt: Playthrough) -> PlaythroughResponse`
  - `to_playthrough_list_item(pt: Playthrough, game: Game, collection: CollectionItem | None) -> PlaythroughListItem`
  - `to_collection_item_expanded(item: CollectionItem, game: Game, playthroughs: list[Playthrough]) -> CollectionItemExpanded`
- **Purity:** No `Session` usage. Accept inputs that the service already queried. Do not trigger lazy loads unintentionally.
- **Datetime handling:** Return `datetime`/`date` objects; FastAPI’s custom JSON encoder already formats them globally.
- **Enums:** Convert to appropriate enum types defined in `app.schemas` where required.

**Usage Example**
- Before (service-level projection):
  - Services build `GameSummary`, `GameDetail`, and dicts for playthroughs inline, duplicating logic across methods.
- After (via mappers):
  - Service composes: `summary = to_game_summary(game)`; `item = to_playthrough_list_item(pt, game, collection)`; `expanded = to_collection_item_expanded(ci, game, pts)`.
  - Reduces duplicate code and keeps service methods focused on querying, validation, and orchestration.

**Pros**
- **Separation of concerns:** Services query and apply business rules; mappers only translate models.
- **Consistency:** Uniform enum conversions and field defaults across endpoints.
- **Reusability:** Shared projections for list/detail views and specialized DTOs.
- **Testability:** Fast unit tests with synthetic ORM instances (no DB).

**Cons**
- **Indirection:** Another layer to look through when navigating code.
- **Overhead:** Adds files/APIs; small projects may not need it.
- **Drift risk:** If services bypass mappers, responses can become inconsistent. Enforce usage via code review.

**Performance Considerations**
- **No lazy loads in mappers:** Pass fully loaded objects (or selected columns) from services. Use `select` + joins or `joinedload` in services to avoid N+1.
- **Keep mapping O(1):** Loops only over already-fetched collections (e.g., list results). Avoid DB calls in mappers.

**Directory & Naming**
- **Folder:** `app/mappers`
- **Functions:** Prefix with `to_` (e.g., `to_game_detail`). Keep names aligned with target schema names.
- **Files:** One mapper module per aggregate (`game_mapper.py`, `playthrough_mapper.py`, `collection_mapper.py`).

**Initial Mapper Surface**
- **Game:** `to_game_summary`, `to_game_detail`.
- **Playthrough:** `to_playthrough_response`, `to_playthrough_list_item`, `to_playthrough_detail` (accepts `Game` and optional `CollectionItem`).
- **Collection:** `to_collection_item_expanded` (accepts `Game` and list of `Playthrough`), plus small helper to build the lightweight playthrough dicts used in the collection response.

**Testing**
- **Unit tests:** Under `api/tests`, e.g., `tests/test_mappers_game.py`, instantiate ORM models directly and assert mapped Pydantic outputs.
- **Edge cases:** Missing optional fields, enum conversions, None datetimes, empty playthrough lists.

**Migration Plan**
- **Step 1:** Create `app/mappers/` and add Game mappers; add unit tests.
- **Step 2:** Refactor `PlaythroughsService` to use playthrough mappers in list/detail/create/update paths.
- **Step 3:** Refactor `CollectionService` to use collection mappers; centralize the playthrough dicts.
- **Step 4:** Remove duplicated projection code from services; keep services focused on DB queries and validation.
- **Step 5:** Add CI tests for mappers; ensure existing tests pass.

**When Not To Use**
- Very small endpoints where mapping is trivial and not reused.
- One-off admin utilities or internal scripts where consistency is less critical.

**Open Questions**
- **Aggregation ownership:** Keep aggregates/stats logic (counts/averages) in services to preserve mapper purity.
- **Partial DTOs:** We currently return small dicts for playthrough snippets in collection responses. Option: introduce dedicated Pydantic models to replace loose dicts for stronger typing.

This plan aims to reduce duplication and improve maintainability without overengineering. We can introduce it incrementally with minimal disruption to existing services.
