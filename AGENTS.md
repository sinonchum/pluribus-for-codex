# AGENTS.md — Pluribus Memory Registry Pivot

## Mandatory context reset

The repository contains code and documents from an earlier product direction. Your stored Codex memories, previous chat context, and some existing files may describe Pluribus as a multi-agent Mission Control system with Scout, Builder, Tester, Reviewer, Hive Blackboard, Git worktrees, and one shared software mission.

**That direction is obsolete for the current build. Do not continue it.**

For all current work, use this definition:

> **Pluribus for Codex is GitHub for useful Codex memories: an open registry where developers publish, discover, install, reuse, fork, and verify Codex debugging methods and coding best practices.**

The current golden path is:

```text
Publish → Discover → Install → Codex Uses → Verify
```

A developer publishes a verified debugging memory. Another developer finds and installs it. Pluribus injects the matching installed memory into a bounded Codex task. Codex applies the method. Coordinator-run verification passes. A Usage Receipt links the publisher, memory, consumer, changed file, and test output.

## Authoritative documents

Read these before changing code:

1. `docs/MEMORY_REGISTRY_SCOPE.md` — product scope, JSON contracts, endpoints, demo criteria.
2. `docs/TEAM_EXECUTION_PLAN_V2.md` — branch ownership, tasks, merge order, verification.
3. This `AGENTS.md` — context reset and branch-specific instructions.

Treat the following as historical and non-authoritative for the current pivot:

- `docs/PRD.md`
- `docs/TEAM_EXECUTION_PLAN.md`
- old Mission Control UI and Replay narrative
- old Scout/Builder/Tester/Reviewer workflow

Do not delete historical code merely because it is obsolete. Avoid touching it unless your assigned module needs a stable reusable adapter.

## Fixed demo story

The only required demo memory is:

```text
Title: Fix duplicate pytest module collisions
Slug: fix-pytest-module-collisions
ID: mem_pytest_importlib_v1
Trigger: pytest import file mismatch caused by duplicate test module basenames
Method: configure pytest with --import-mode=importlib
Expected changed file: pyproject.toml
Final verification: pytest -q exits 0
```

Do not replace this with a different demo scenario without a team decision.

## Honest product boundary

Pluribus does not mutate hidden Codex model state and must not claim to do so. It creates explicit local memory packages under a caller-supplied project root and injects matching memory content into Codex task context through the existing adapter.

Do not commit:

- OAuth tokens
- API keys
- raw private Codex transcripts
- `~/.codex/auth.json`
- absolute personal home-directory paths
- unredacted environment variables

## Shared frozen data contracts

All branches must use the exact contract in `docs/MEMORY_REGISTRY_SCOPE.md`.

Core objects:

```text
Memory Capsule
Install Manifest
Usage Receipt
Demo Snapshot
```

Frozen API surface:

```text
GET    /api/memories?query=&tag=&sort=
POST   /api/memories
GET    /api/memories/{slug}
POST   /api/memories/{slug}/star
POST   /api/memories/{slug}/install
GET    /api/installed
POST   /api/usage-receipts
GET    /api/usage-receipts/{id}
GET    /api/demo/snapshot
```

Do not invent or rename contract fields locally. If a contract is impossible to implement, stop and report the exact issue rather than silently changing it.

## First command: identify your branch

Before doing anything else, run:

```bash
git branch --show-current
git rev-parse HEAD
git status --short
```

Then follow only the section matching your branch.

---

## Branch: `feat/memory-registry-api`

### Your role

You are **Person 1: Memory Registry API and persistence owner**.

### You own

```text
backend/app/registry/**
backend/app/api/memories.py
backend/app/schemas/memories.py
backend/app/db/database.py
backend/app/main.py
backend/tests/registry/**
backend/tests/api/test_memories.py
```

Only this branch may register new routers in `backend/app/main.py` or change registry tables in `backend/app/db/database.py`.

### Build

1. Write failing tests for the frozen Memory Capsule schema.
2. Add typed models for memories, authors, verification evidence, install records, and demo snapshot.
3. Add idempotent SQLite tables for memories, stars, and installs.
4. Seed `fix-pytest-module-collisions` exactly once.
5. Implement query and tag search.
6. Implement create, detail, star, install-record, installed-list, and demo-snapshot endpoints.
7. Preserve existing `/health`, localhost-only CORS, and existing database tables.

### Required observable result

```text
GET /api/memories?query=pytest
```

returns the seeded verified memory, and:

```text
GET /api/demo/snapshot
```

returns the aggregate shape frozen in the scope document.

### Do not

- Do not build filesystem installation.
- Do not run Codex.
- Do not edit `frontend/`.
- Do not add authentication, billing, or social following.

### Verify

```bash
cd backend
uv sync --dev
uv run pytest tests/registry tests/api/test_memories.py -q
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
```

---

## Branch: `feat/codex-memory-runtime`

### Your role

You are **Person 2: local Memory Runtime and Codex context owner**.

### You own

```text
backend/app/memory_runtime/**
backend/app/adapters/codex/memory_context.py
backend/tests/memory_runtime/**
tools/pluribus_memory.py
```

### Build

1. Write failing tests for redacting fake tokens, API-key assignments, and personal absolute paths.
2. Render a deterministic `MEMORY.md` from the frozen Memory Capsule.
3. Generate `manifest.json` with memory id, slug, version, install path, SHA-256, and timestamp.
4. Install under `<root>/.pluribus/installed/<slug>/`.
5. Make reinstalling the same version idempotent.
6. Implement local list and uninstall operations.
7. Match installed memories against task/error text using frozen triggers and tags.
8. Produce a bounded context packet containing memory id, version, trigger, and steps.
9. Add a helper that injects this packet into the existing Codex adapter prompt.
10. Provide CLI commands for `install`, `list`, and `match`.

### Required observable result

```bash
python tools/pluribus_memory.py match \
  --text "pytest import file mismatch in duplicate test_runner.py" \
  --root /tmp/pluribus-demo
```

selects `mem_pytest_importlib_v1` after installation.

### Do not

- Do not write registry API routes or database tables.
- Do not edit `backend/app/main.py`.
- Do not edit `frontend/`.
- Do not claim native or hidden Codex memory mutation.

### Verify

```bash
cd backend
uv run pytest tests/memory_runtime -q
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
```

---

## Branch: `feat/memory-usage-verification`

### Your role

You are **Person 3: Usage Receipt, coordinator verification, and demo fixture owner**.

### You own

```text
backend/app/usage/**
backend/tests/usage/**
demo/memory-fixture/**
demo/memory-evidence/**
demo/run-memory-demo.py
```

### Build

1. Create a minimal Python fixture that reproduces pytest import-file-mismatch from duplicate test module basenames.
2. Preserve a sanitized failing-baseline evidence artifact.
3. Write failing tests for the frozen Usage Receipt contract.
4. Build receipts from memory match, injected memory id, Codex-reported usage, changed files, and coordinator verification.
5. Reject incomplete receipts.
6. Reuse the existing safe subprocess verification runner; never use `shell=True`.
7. Create a demo runner supporting explicit `live` and `replay` modes.
8. Ensure the final fixture uses the expected changed file `pyproject.toml` and `pytest -q` exits `0`.
9. Generate sanitized replay data for Person 4.

### Required observable result

```text
baseline failure
→ mem_pytest_importlib_v1 selected
→ memory injected into Codex context
→ pyproject.toml changed
→ pytest -q exits 0
→ valid Usage Receipt generated
```

### Do not

- Do not add Registry API routes.
- Do not edit `backend/app/main.py` or `backend/app/db/database.py`.
- Do not edit `frontend/`.
- Do not fabricate live Codex output. Label Replay clearly.

### Verify

```bash
cd backend
uv run pytest tests/usage -q
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
```

Also run the final fixture verification from its own directory.

---

## Branch: `feat/memory-marketplace-ui`

### Your role

You are **Person 4: Memory Marketplace UI and demo story owner**.

### You own

```text
frontend/**
demo/start-memory-demo.mjs
demo/README_MEMORY_DEMO.md
```

### Build

Create a UI that is immediately understandable as **GitHub or a package registry for Codex memories**, not as an agent-control dashboard.

Required screens:

1. **Explore** — search, tag filters, verified badges, author, stars, installs, version.
2. **Memory Detail** — problem, triggers, steps, compatibility, evidence, version, fork lineage, Install button.
3. **Publish** — fixed validated form for a Memory Capsule; no raw transcript upload.
4. **My Codex** — installed memory state and version.
5. **Usage Receipt** — publisher → memory → consumer → changed file → verification passed.

Required demo path:

```text
Explore
→ search pytest
→ open Fix duplicate pytest module collisions
→ Install to Codex
→ show installed state
→ run or replay the use
→ show verified Usage Receipt
```

### Do not

- Do not use Scout, Builder, Tester, or Reviewer as primary product concepts.
- Do not show the old Mission Control dashboard.
- Do not modify backend files.
- Do not invent response fields outside the frozen contract.
- Do not present recorded data as live.

### Verify

```bash
cd frontend
npm ci
npm test -- --run
npm run typecheck
npm run build
npm audit
```

Then inspect every screen in a real browser at the projector viewport and confirm zero JavaScript errors.

---

## Engineering rules for every branch

1. Use RED → GREEN → REFACTOR for every behavior change.
2. Run the smallest failing test first, then the full suite.
3. Do not modify another person's owned paths.
4. Do not delete old modules just to make the repository look cleaner.
5. Keep changes minimal and aligned with the fixed demo.
6. Use executable-and-argument arrays for subprocesses; never `shell=True`.
7. Open a Draft PR targeting `pivot/memory-registry-v1`.
8. PR description must include actual test output and any remaining blocker.
9. Do not claim end-to-end completion unless Publish → Discover → Install → Codex Uses → Verify has been exercised with real output.

## Merge order

```text
1. feat/memory-registry-api
2. feat/codex-memory-runtime
3. feat/memory-usage-verification
4. feat/memory-marketplace-ui
```

## Definition of done

The build is complete only when the demo can prove:

```text
Developer A published a verified memory
Developer B discovered and installed it
Pluribus injected it into Codex context
Codex used it on a matching failure
A named file changed
Coordinator-run tests passed
A Usage Receipt connected the full chain
```
