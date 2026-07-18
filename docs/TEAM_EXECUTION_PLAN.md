# Pluribus for Codex — Four-Person Execution Plan

**Goal:** Build the scope-frozen v0.2 hackathon MVP with four parallel contributors while minimizing merge conflicts.

**Shared constraints:**

- One fixed demo repository and one fixed mission.
- Four fixed runtime roles: Scout, Builder, Tester, Reviewer.
- Maximum runtime worker concurrency: two.
- Python 3.11, FastAPI, SQLite, Git CLI, Server-Sent Events, React/Vite.
- Dirty repositories are rejected by default.
- Verification commands use executable-plus-argument arrays; never `shell=True`.
- Integration order is Tester patch, then Builder patch.
- Secrets and OAuth tokens must never enter source, Git history, fixtures, or logs.

## Branch and ownership map

### Person 1 — Backend API and persistence

**Branch:** `feat/backend-api-persistence`

**Owns:**

- `backend/pyproject.toml`
- `backend/app/main.py`
- `backend/app/api/**`
- `backend/app/models/**`
- `backend/app/schemas/**`
- `backend/app/db/**`
- `backend/tests/api/**`
- `backend/tests/db/**`

**Tasks:**

1. Scaffold the Python 3.11 FastAPI application and test setup.
2. Implement SQLite initialization and repositories for missions, agents, knowledge patches, and events.
3. Implement typed request/response schemas for the PRD API surface.
4. Implement mission create/get, agent get, knowledge get, report get, and stop endpoints.
5. Implement SSE event streaming at `GET /api/missions/{id}/events`.
6. Expose explicit service interfaces that Person 3 can connect to mission start and orchestration.

**Acceptance criteria:**

- A mission can be created and retrieved from a fresh SQLite database.
- Invalid/non-Git repository input is rejected.
- Dirty repositories are rejected unless explicitly allowed.
- SSE sends persisted lifecycle events without WebSockets.
- API and persistence tests pass.

**Do not edit:** `frontend/**`, Codex adapter internals, Git/worktree orchestration internals.

---

### Person 2 — Codex adapter and Hive memory

**Branch:** `feat/codex-adapter-memory`

**Owns:**

- `backend/app/adapters/codex/**`
- `backend/app/prompts/**`
- `backend/app/hive/**`
- `backend/tests/adapters/**`
- `backend/tests/hive/**`

**Tasks:**

1. Implement a Codex CLI preflight check and bounded asynchronous subprocess runner.
2. Add Scout, Builder, Tester, and Reviewer prompt templates.
3. Parse the machine-readable agent output contract, including `consumed_patch_ids` and `knowledge_usage`.
4. Validate Knowledge Patch shape, statuses, evidence paths, and baseline commit.
5. Compile relevance-filtered role context packets.
6. Track which patches were delivered and causally consumed by later agents.
7. Return raw logs, structured handoff, exit code, timeout state, and parse errors.

**Acceptance criteria:**

- Missing/unusable Codex CLI fails preflight with an actionable error.
- Subprocesses have explicit timeouts and never use `shell=True`.
- All four role prompts can be rendered deterministically.
- Valid output parses; malformed output is preserved and reported safely.
- A Scout patch can appear in a Builder context packet and later be recorded as consumed.

**Do not edit:** `frontend/**`, SQLite schema/repositories, Git/worktree integration.

---

### Person 3 — Git isolation, orchestration, and verification

**Branch:** `feat/git-orchestration-verification`

**Owns:**

- `backend/app/git/**`
- `backend/app/orchestration/**`
- `backend/app/verification/**`
- `backend/app/reporting/**`
- `backend/tests/git/**`
- `backend/tests/orchestration/**`
- `backend/tests/verification/**`
- `backend/tests/reporting/**`

**Tasks:**

1. Capture the repository baseline and create an integration branch.
2. Create isolated worktrees for writing agents.
3. Enforce static role path boundaries and protected paths.
4. Implement the fixed mission graph: Scout → Builder + Tester Phase A → integrate → verify → Reviewer → optional repair → final verify.
5. Enforce maximum worker concurrency of two.
6. Apply the Tester patch before the Builder patch and report conflicts.
7. Run verification commands using executable-plus-argument arrays with timeouts.
8. Produce a deterministic evidence report and cleanup/reset operations.

**Acceptance criteria:**

- Worktrees and branches are reproducible from the recorded baseline.
- Out-of-bound or protected-path edits are rejected.
- Integration order is proven in tests.
- Verification records command, args, exit code, duration, and bounded output.
- A complete fake-adapter mission reaches a final report without needing the real Codex CLI.

**Do not edit:** `frontend/**`, prompt templates/parser internals, core database schema.

---

### Person 4 — Mission Control frontend and demo experience

**Branch:** `feat/mission-control-ui`

**Owns:**

- `frontend/**`
- `demo/**`
- UI screenshots and visual assets under `docs/assets/**`

**Tasks:**

1. Scaffold React/Vite with a fast, dark Mission Control visual system.
2. Build mission creation for the fixed demo repository and objective.
3. Build the three required panels:
   - Agent roster and live status
   - Hive memory and causal knowledge flow
   - Integrated diff, verification, and evidence
4. Consume REST endpoints and SSE lifecycle events.
5. Clearly distinguish live execution, completed execution, failure, and replay mode.
6. Add a deterministic replay fixture as a labeled fallback—not as fake live execution.
7. Prepare the fixed demo repository/task and a one-command demo launcher.

**Acceptance criteria:**

- An observer can understand mission status without reading terminal logs.
- At least one Scout → Builder causal knowledge-use event is visibly inspectable.
- Integrated diff and real verification result are visible.
- Replay mode is unmistakably labeled.
- Production build completes successfully.

**Do not edit:** backend implementation files. Use local typed API mocks until backend contracts land.

## Shared API contract

Person 1 owns the canonical request/response schemas. Until those files land, all contributors use the PRD endpoints:

- `POST /api/missions`
- `POST /api/missions/{id}/start`
- `POST /api/missions/{id}/stop`
- `GET /api/missions/{id}`
- `GET /api/missions/{id}/agents/{agent_id}`
- `GET /api/missions/{id}/knowledge`
- `GET /api/missions/{id}/events`
- `GET /api/missions/{id}/report`

Cross-branch contract changes must be documented in the PR description. Do not solve a missing dependency by editing another person's owned directory.

## Daily integration order

1. Merge `feat/backend-api-persistence` first to establish schemas and application wiring.
2. Rebase the other three branches onto the updated `main`.
3. Merge `feat/codex-adapter-memory`.
4. Merge `feat/git-orchestration-verification` and connect it to the API service interfaces.
5. Merge `feat/mission-control-ui` last and replace mocks with the final contracts.
6. Run an end-to-end mission three consecutive times before presentation freeze.

## Pull request rules

- Open a draft PR as soon as the first working vertical slice exists.
- Keep commits small and use Conventional Commits.
- Include changed paths, tests run, known risks, and contract changes.
- Do not merge your own PR.
- Do not commit `.env`, tokens, local databases, worktrees, agent logs containing secrets, or generated dependency directories.
- Before requesting review, rebase on `origin/main` and run all tests owned by the branch.

## First checkpoint

Each person should deliver within the first 60–90 minutes:

- Person 1: running FastAPI health endpoint plus SQLite migration/init test.
- Person 2: Codex preflight plus one deterministic prompt/parser test.
- Person 3: baseline capture plus isolated worktree integration test.
- Person 4: running three-panel UI populated by a labeled replay fixture.

These four slices can be demonstrated independently and expose integration risks early.
