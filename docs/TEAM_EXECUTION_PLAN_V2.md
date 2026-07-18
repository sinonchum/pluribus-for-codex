# Pluribus Memory Registry — Four-Person Pivot Plan

## Stop instruction

Stop development on the old mission-orchestration feature branches. Do not merge `feat/demo-ui-redesign` into the pivot. All four new branches must start from the exact Pivot SHA announced after this document is committed.

## New product loop

```text
Publish → Discover → Install → Codex Uses → Verify
```

The shared contract is frozen in `docs/MEMORY_REGISTRY_SCOPE.md`. No developer may change response shapes independently. Contract changes require a team decision and a dedicated contract commit on the Pivot branch.

## Conflict-control rules

1. Each person owns the directories listed below.
2. Only Person 1 may modify `backend/app/main.py`, `backend/app/db/database.py`, and API router registration.
3. Only Person 4 may modify `frontend/`.
4. Only Person 3 may modify `demo/memory-fixture/` and `demo/memory-evidence/`.
5. Nobody changes the old orchestration modules unless their owned module imports a stable adapter from them.
6. Every behavior change follows RED → GREEN → REFACTOR.
7. Every PR includes exact commands and real output.
8. No raw Codex transcript, token, secret, home-directory path, or OAuth file may enter Git.

---

## Person 1 — Memory Registry API and persistence

**Branch:** `feat/memory-registry-api`

**Owns:**

```text
backend/app/registry/**
backend/app/api/memories.py
backend/app/schemas/memories.py
backend/app/db/database.py
backend/app/main.py
backend/tests/registry/**
backend/tests/api/test_memories.py
```

**Goal:** Build the server-side source of truth for published memories, stars, installs, and demo snapshots.

### Tasks

1. Write failing schema tests for the frozen Memory Capsule JSON.
2. Implement typed models for author, verification, memory, install record, receipt summary, and demo snapshot.
3. Add SQLite tables for `memories`, `memory_stars`, and `memory_installs` without breaking existing tables.
4. Seed the fixed `fix-pytest-module-collisions` verified memory idempotently.
5. Implement search by title, summary, trigger, and tag.
6. Implement exact and filtered list endpoints.
7. Implement detail, star, and install-record endpoints.
8. Implement `GET /api/installed` and `GET /api/demo/snapshot`.
9. Register the router in `app/main.py`.
10. Preserve localhost-only CORS and existing health endpoints.

### API acceptance

```text
GET /api/memories?query=pytest              → seeded memory
GET /api/memories?tag=debugging             → seeded memory
GET /api/memories/fix-pytest-module-collisions → full capsule
POST /api/memories/{slug}/star              → stars increment once per fixed demo user
POST /api/memories/{slug}/install           → install count + install record
GET /api/demo/snapshot                      → frozen aggregate shape
```

### Required verification

```bash
cd backend
uv sync --dev
uv run pytest tests/registry tests/api/test_memories.py -q
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
```

### Must not do

- Do not build the local filesystem installer.
- Do not run Codex.
- Do not edit the frontend.
- Do not add authentication.

---

## Person 2 — Codex memory capture, redaction, installation, and context injection

**Branch:** `feat/codex-memory-runtime`

**Owns:**

```text
backend/app/memory_runtime/**
backend/app/adapters/codex/memory_context.py
backend/tests/memory_runtime/**
tools/pluribus_memory.py
```

**Goal:** Turn a sanitized Memory Capsule into a deterministic local package and inject relevant installed memories into a bounded Codex prompt.

### Tasks

1. Write failing tests for secret redaction using fake credentials only.
2. Implement redaction for bearer tokens, common API-key assignments, and user-home absolute paths.
3. Write failing tests for deterministic Memory Markdown rendering.
4. Render `MEMORY.md` with title, problem, triggers, steps, compatibility, author, version, and evidence.
5. Write failing tests for install manifest generation and SHA-256 integrity.
6. Install to a caller-supplied root: `<root>/.pluribus/installed/<slug>/`.
7. Implement list and uninstall operations for the local root.
8. Implement trigger matching against a task/error string.
9. Build a bounded context packet from the top matching installed memories.
10. Add a Codex adapter helper that appends the explicit memory packet to a prompt.
11. Provide CLI commands:

```text
python tools/pluribus_memory.py install --capsule <json> --root <repo>
python tools/pluribus_memory.py list --root <repo>
python tools/pluribus_memory.py match --text "..." --root <repo>
```

### Runtime acceptance

- Installation creates `MEMORY.md` and `manifest.json`.
- Reinstalling the same version is idempotent.
- Manifest hash matches the Markdown bytes.
- A pytest import-mismatch error selects the seeded memory.
- Context output explicitly identifies the memory id/version.
- Fake secrets used in tests never appear in rendered content.

### Required verification

```bash
cd backend
uv run pytest tests/memory_runtime -q
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
```

### Must not do

- Do not write registry database tables or API routes.
- Do not edit `app/main.py`.
- Do not edit the frontend.
- Do not claim native hidden Codex memory mutation.

---

## Person 3 — Usage receipts, verification, and fixed demo fixture

**Branch:** `feat/memory-usage-verification`

**Owns:**

```text
backend/app/usage/**
backend/tests/usage/**
demo/memory-fixture/**
demo/memory-evidence/**
demo/run-memory-demo.py
```

**Goal:** Prove that an installed memory was matched, injected into Codex, associated with a concrete file change, and followed by coordinator-run verification.

### Tasks

1. Create a tiny Python fixture with duplicate test module basenames that reproduces pytest import-file-mismatch without importlib mode.
2. Commit the failing baseline and record the exact expected failure signature.
3. Write failing tests for Usage Receipt validation.
4. Implement receipt construction from memory match, Codex handoff, changed files, and verification output.
5. Reject receipts that lack a matched trigger, injected memory id, changed file, or coordinator verification.
6. Reuse the existing safe subprocess verification runner; do not use `shell=True`.
7. Add a demo runner that accepts an installed memory root and a Codex adapter protocol.
8. Record deterministic replay evidence separately from live execution.
9. Produce `demo_snapshot.json`, sanitized verification output, and one receipt fixture for the UI.
10. Verify protected paths and keep all changes inside the fixture.

### Demo acceptance

```text
Baseline command                         → reproducible failure
Memory selected                          → mem_pytest_importlib_v1
Codex prompt contains installed memory   → true
Changed file                             → pyproject.toml
Coordinator command                      → pytest -q
Coordinator exit code                    → 0
Usage receipt                            → valid
```

### Required verification

```bash
cd backend
uv run pytest tests/usage -q
uv run pytest -q
uv run ruff check .
cd ../demo/memory-fixture
uv run pytest -q
```

The fixture's final checked-in state may be passing, but `demo/memory-evidence/` must preserve the sanitized failing baseline receipt used by Replay.

### Must not do

- Do not add registry routes.
- Do not edit `app/main.py` or `database.py`.
- Do not edit the frontend.
- Do not fabricate live Codex output; replay must be labeled.

---

## Person 4 — Memory Marketplace UI and demo story

**Branch:** `feat/memory-marketplace-ui`

**Owns:**

```text
frontend/**
demo/start-memory-demo.mjs
demo/README_MEMORY_DEMO.md
```

**Goal:** Make the product instantly understandable as “GitHub for useful Codex memories.”

### Required screens

1. **Explore** — search, tags, verified badge, author, stars, installs, and featured memories.
2. **Memory Detail** — problem, triggers, steps, compatibility, evidence, version, fork lineage, and Install button.
3. **My Codex** — installed memory list and local installation state.
4. **Usage Receipt** — publisher → memory → consumer → changed file → verification passed.
5. **Publish** — fixed, validated form for one Memory Capsule; no transcript upload.

### Demo navigation

```text
Explore → Open memory → Install to Codex → Run/Replay use → Show receipt
```

### Tasks

1. Freeze TypeScript types from `MEMORY_REGISTRY_SCOPE.md` before components.
2. Write failing tests for search, detail, install transition, and receipt rendering.
3. Build a GitHub/package-registry-like Explore page, not a multi-agent mission dashboard.
4. Build detail and install interaction against the frozen API.
5. Build My Codex installation state.
6. Build the receipt proof page with large verification evidence.
7. Add explicit `LIVE` and `REPLAY — RECORDED EVIDENCE` states.
8. Add deterministic replay data matching the shared contract.
9. Verify at the projector viewport with browser console at zero errors.

### Required verification

```bash
cd frontend
npm ci
npm test -- --run
npm run typecheck
npm run build
npm audit
```

### Must not do

- Do not show Scout/Builder/Tester/Reviewer as the primary product.
- Do not reuse the Mission Control narrative.
- Do not modify backend files.
- Do not silently invent API fields.

---

## Integration order

```text
1. feat/memory-registry-api
2. feat/codex-memory-runtime
3. feat/memory-usage-verification
4. feat/memory-marketplace-ui
```

Person 1 merges first because the API contract and persistence are foundational. Person 2 and Person 3 may code in parallel against Protocols and fixtures, but merge in the order above. Person 4 consumes only the frozen contract and merges last.

## Final integration gate

```bash
cd backend
uv sync --dev
uv run pytest -q
uv run ruff check .
uv run ruff format --check .

cd ../frontend
npm ci
npm test -- --run
npm run typecheck
npm run build
npm audit

cd ..
python demo/run-memory-demo.py --mode replay
```

Before presentation freeze, verify:

- Search and detail use real API data.
- Install writes a real local package.
- Trigger matching selects the installed memory.
- Codex preflight succeeds on the demo machine.
- The live/replay boundary is explicit.
- Usage Receipt includes a real changed file and coordinator test output.
- No secret or personal home path appears in Git, logs, or screenshots.
