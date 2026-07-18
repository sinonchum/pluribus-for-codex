# Pluribus for Codex: Detailed Implementation Plan

This document converts the v0.2 product requirements into an executable engineering plan. It defines dependencies, package boundaries, feature order, tests, validation gates, and four independently developable workstreams.

## 1. Delivery target

Deliver one reliable vertical slice:

```text
clean repository
  → mission preflight
  → Scout
  → Builder + Tester planning
  → candidate assembly
  → Reviewer + Tester execution
  → optional repair
  → Coordinator verification
  → Markdown/JSON report
```

The plan optimizes for deterministic integration and a five-minute prepared demo. It does not optimize for generalized orchestration, arbitrary agent counts, or production isolation.

## 2. Engineering principles

1. **Git and process output are truth.** Agent summaries are never authoritative for changed files, commands, or exit codes.
2. **Contracts before implementations.** Freeze shared protocols and data models before parallel work begins.
3. **Dependency inversion at team boundaries.** Orchestration depends on typed protocols; each subsystem has an in-memory or fake implementation.
4. **No shell interpolation.** Subprocesses use argument arrays and explicit working directories.
5. **Every state change emits an event.** The dashboard and report consume the same persisted facts.
6. **Every risky feature has a negative test.** Success-path coverage alone is insufficient.
7. **Integration is serial even when development is parallel.** Candidate artifacts are applied in a fixed order.
8. **MVP scope is fixed.** Four roles, one mission, one optional repair, one local repository.

## 3. Selected stack and dependencies

### 3.1 Runtime dependencies

| Package | Version policy | Required by | Rationale |
|---|---|---|---|
| Python | `>=3.11` | All components | `asyncio.TaskGroup`, modern typing, subprocess support |
| `fastapi` | compatible pinned minor | API and dashboard | Typed HTTP API, validation, SSE-compatible streaming |
| `uvicorn` | compatible pinned minor | Application runtime | Local ASGI server |
| `pydantic` | `>=2,<3` | Contracts and API | Strict request, event, handoff, and report schemas |
| `aiosqlite` | compatible pinned minor | Persistence | Small asynchronous SQLite layer without ORM complexity |
| `jinja2` | compatible pinned minor | Dashboard and reports | Server-rendered UI and Markdown generation |

Use standard-library modules for `asyncio`, subprocesses, JSON, hashing, path handling, timestamps, pattern matching, and SQLite migrations where practical.

### 3.2 Development dependencies

| Package | Purpose |
|---|---|
| `pytest` | Unit, integration, and end-to-end test runner |
| `pytest-asyncio` | Async service and orchestration tests |
| `httpx` | FastAPI integration tests |
| `coverage` / `pytest-cov` | Coverage measurement |
| `ruff` | Formatting and linting |
| `mypy` | Static validation of contracts and subsystem boundaries |

### 3.3 Dependencies intentionally avoided

- No React/Vite build: server-rendered HTML plus native `EventSource` is sufficient.
- No ORM: explicit SQL makes state transitions and event ordering easier to inspect.
- No Redis or message broker: one process and SQLite are sufficient for the MVP.
- No embeddings or vector database: deterministic relevance is sufficient.
- No Docker requirement: it would consume MVP time and does not provide complete sandboxing by itself.
- No shell-command helper library: direct argument arrays keep the security boundary visible.

### 3.4 Dependency installation and lock policy

Create a `pyproject.toml` with runtime and `dev` optional dependencies. Use one lock mechanism selected before development begins; `uv.lock` is recommended if `uv` is available to all four developers. If not, commit a fully pinned `requirements-dev.txt` generated from the project metadata.

Validation:

```bash
python -m pip install -e '.[dev]'
python -m pytest
ruff check .
ruff format --check .
mypy src/pluribus
```

The repository must document the selected installation path. CI and local instructions must use the same path.

## 4. Proposed repository layout

```text
pluribus-for-codex/
├── pyproject.toml
├── README.md
├── docs/
│   ├── PRD.md
│   ├── IMPLEMENTATION_PLAN.md
│   ├── CODEX_ADAPTER.md
│   └── adr/
├── src/pluribus/
│   ├── __init__.py
│   ├── app.py
│   ├── config.py
│   ├── contracts/
│   │   ├── enums.py
│   │   ├── models.py
│   │   ├── protocols.py
│   │   └── events.py
│   ├── storage/
│   │   ├── database.py
│   │   ├── migrations.py
│   │   └── repositories.py
│   ├── api/
│   │   ├── routes.py
│   │   ├── dependencies.py
│   │   └── sse.py
│   ├── codex/
│   │   ├── adapter.py
│   │   ├── parser.py
│   │   ├── prompts.py
│   │   └── redaction.py
│   ├── knowledge/
│   │   ├── validator.py
│   │   ├── context.py
│   │   └── relevance.py
│   ├── gitops/
│   │   ├── repository.py
│   │   ├── worktrees.py
│   │   ├── leases.py
│   │   ├── artifacts.py
│   │   └── integration.py
│   ├── verification/
│   │   ├── runner.py
│   │   └── policy.py
│   ├── orchestration/
│   │   ├── coordinator.py
│   │   ├── state_machine.py
│   │   ├── scheduler.py
│   │   └── cancellation.py
│   ├── reporting/
│   │   ├── builder.py
│   │   └── schemas.py
│   ├── web/
│   │   ├── routes.py
│   │   ├── templates/
│   │   └── static/
│   └── cli.py
└── tests/
    ├── unit/
    ├── integration/
    ├── e2e/
    ├── fixtures/
    │   ├── fake_codex.py
    │   └── demo_repo_factory.py
    └── contract/
```

Package boundaries are ownership boundaries. During parallel development, a developer must not edit another developer's owned package without agreement.

## 5. Shared contracts to freeze before parallel work

Parallel development begins only after a bootstrap commit defines the following contracts.

### 5.1 Identifiers and enums

- `MissionId`, `TaskId`, `WorkerId`, `RunId`, `PatchId`, `ArtifactId` as validated strings or typed aliases.
- `MissionState` including every valid terminal and non-terminal state.
- `WorkerRole`: Scout, Builder, Tester, Reviewer.
- `KnowledgeType` and `KnowledgeState`.
- `WorkerRunState`, `TaskState`, `ArtifactState`.
- `ReviewVerdict` and finding severity.

### 5.2 Core immutable models

- `RepositoryBaseline`.
- `MissionSpec`.
- `TaskSpec` and dependency IDs.
- `WorkerTurnRequest` and `WorkerTurnResult`.
- `ProcessResult`.
- `KnowledgePatch` and evidence variants.
- `ContextPacket` and delivery receipts.
- `FileLease`.
- `CandidateArtifact`.
- `ReviewFinding` and `ReviewResult`.
- `VerificationCommand` and `VerificationResult`.
- `EvidenceReport`.

Models must reject unknown fields at external boundaries and use timezone-aware UTC timestamps.

### 5.3 Protocols

```python
class EventStore(Protocol): ...
class MissionRepository(Protocol): ...
class WorkerRuntime(Protocol): ...
class KnowledgeService(Protocol): ...
class GitWorkspace(Protocol): ...
class ArtifactIntegrator(Protocol): ...
class VerificationRunner(Protocol): ...
class ReportBuilder(Protocol): ...
```

Each protocol must have an in-memory fake suitable for independent unit tests. No subsystem test should require all other real subsystems.

### 5.4 Event envelope

Every observable event uses:

```json
{
  "id": 142,
  "mission_id": "mission_001",
  "type": "knowledge_patch_delivered",
  "source": "coordinator",
  "occurred_at": "2026-07-18T11:04:20Z",
  "payload": {},
  "schema_version": 1
}
```

Events are stored before they are broadcast. SSE is a projection of persisted events, not an independent source of truth.

### 5.5 Contract tests

Create tests before subsystem development:

- Every enum serializes to the documented value.
- Unknown external fields fail validation.
- Every event round-trips through JSON.
- Every protocol fake passes a shared behavioral test suite.
- Mission-state transition table rejects invalid transitions.
- Evidence variants require the correct fields.
- Paths reject absolute paths and `..` escapes.

Contract changes after freeze require:

1. A short ADR.
2. Updated contract tests.
3. Notification to all workstream owners.
4. Rebase or merge of the contract commit before further development.

## 6. Feature dependency map

| Feature | Requires | Enables |
|---|---|---|
| Project scaffold | Python and dependency decision | All workstreams |
| Shared contracts | Scaffold | Independent subsystem development |
| SQLite migrations | Contracts | Mission persistence, events, reports |
| Event store | Migrations | SSE, audit trail, report timeline |
| Repository preflight | Git command runner, contracts | Mission start |
| Worktree manager | Successful preflight | Writing worker isolation |
| Codex probe | Process runner | Adapter preflight |
| Codex process runner | Contracts, cancellation | All worker turns |
| Handoff parser | Output contract | Knowledge ingestion and worker summaries |
| Evidence validator | Git reader, contracts | Supported/verified knowledge |
| Context compiler | Knowledge store, task/lease data | Cross-worker synchronization |
| Lease validator | Contracts, Git changed paths | Artifact acceptance |
| Artifact builder | Worktree diff, scope validation | Candidate assembly |
| Candidate integrator | Valid artifacts, integration worktree | Review/test execution |
| State machine | Contracts and event store | Safe orchestration |
| Scheduler | State machine and subsystem protocols | Complete mission flow |
| Verification runner | Candidate commit and commands | Terminal status |
| Report builder | Persisted events and artifacts | Auditable result |
| SSE API | Persisted event store | Live dashboard |
| Dashboard | API and SSE event schema | Demo usability |
| End-to-end mission | All protocol implementations | Release qualification |

No feature may bypass its prerequisite merely to make the UI appear complete.

## 7. Implementation sequence and validation

### Phase 0 — Contract and scaffold freeze

#### Step 0.1: Create project metadata

Implement:

- `pyproject.toml`.
- `src/` layout.
- Test configuration.
- Ruff and mypy configuration.
- Minimal application and CLI entry points.

Tests and validation:

- Clean editable installation succeeds.
- `python -c "import pluribus"` succeeds.
- Empty test suite command is wired correctly.
- Ruff and mypy execute without configuration errors.

Dependencies: none beyond selected Python toolchain.

#### Step 0.2: Implement shared contracts

Implement all models, enums, protocols, errors, and events listed in Section 5.

Tests:

- Serialization round trips.
- Invalid state, path, timestamp, and evidence cases.
- Equality and immutability expectations.
- Protocol fake behavioral suites.

Exit gate:

- All four developers review and sign off the contract commit.
- No placeholder `Any` at subsystem boundaries without a documented reason.

### Phase 1 — Platform foundations

#### Step 1.1: SQLite schema and migrations

Implement tables for:

- Missions.
- Tasks and dependencies.
- Worker runs.
- Knowledge patches and state events.
- Context receipts.
- Leases.
- Artifacts and application attempts.
- Review findings.
- Verification runs.
- Ordered mission events.

Requirements:

- Foreign keys enabled.
- Transactions used for state change plus event append.
- Mission-scoped indexes.
- Migration version recorded.
- UTC timestamps stored consistently.

Tests:

- New in-memory and temporary-file database migration.
- Foreign-key rejection.
- Transaction rollback when event append fails.
- Concurrent event append produces unique increasing IDs.
- Repository queries do not cross mission boundaries.
- Reopening a database preserves state.

#### Step 1.2: Event store and SSE

Implement event append, query-after-ID, live subscription, disconnect handling, and bounded subscriber queues.

Tests:

- Stored event is visible before broadcast.
- `Last-Event-ID` resumes without duplicates.
- Slow client does not block Coordinator progress.
- Subscriber disconnect removes queue.
- Reconnect after process restart replays persisted events.

#### Step 1.3: Mission API

Implement create, start, cancel, query, report, events, and cleanup endpoints. Start and cancellation call protocols initially backed by fakes.

Tests:

- Request validation and response schemas.
- Start is idempotent.
- Cancel is idempotent.
- Starting an invalid state returns `409`.
- Unknown mission returns `404`.
- SSE content type and event IDs are correct.
- API never exposes configured secret values.

### Phase 2 — Repository and execution safety

#### Step 2.1: Git command runner

Build one wrapper that accepts argument arrays, explicit `cwd`, timeout, and output cap. Do not use `shell=True`.

Tests:

- Arguments containing spaces remain one argument.
- Timeout terminates the process.
- Output truncation is recorded.
- Non-zero exit code is returned, not converted into an untyped exception.

#### Step 2.2: Repository preflight

Implement root resolution, HEAD/branch detection, status check, protected-pattern validation, and integration-branch collision check.

Tests with temporary Git repositories:

- Non-Git path rejected.
- Unborn repository rejected.
- Clean branch accepted.
- Detached HEAD recorded accurately.
- Modified, staged, untracked, and conflicted states rejected.
- Paths with spaces work.
- Original repository status is byte-for-byte unchanged after preflight.

#### Step 2.3: Worktree manager

Implement mission directory creation, unique branches, worktree add/remove, and integration worktree creation.

Tests:

- Every worktree starts at the baseline commit.
- Branch and path names are collision-resistant.
- Failure halfway through creation leaves a recoverable record.
- Cleanup only targets paths recorded as mission-owned.
- Cleanup refuses a path outside the configured Pluribus worktree root.
- Original working tree remains unchanged.

#### Step 2.4: Lease and protected-path validation

Implement normalized repository-relative path matching. Decide and document glob semantics once; use the same matcher in API validation and artifact validation.

Tests:

- Allowed exact file.
- Allowed directory pattern.
- Out-of-lease file.
- Protected exact file and recursive directory.
- Path traversal and absolute paths rejected.
- Rename, deletion, symlink, and case-sensitivity behavior tested on supported platforms.
- A protected change cannot be overridden by an agent handoff.

#### Step 2.5: Artifact creation

Derive changed paths and binary-safe patches from Git. Hash patch bytes and record base commit.

Tests:

- Text addition, modification, deletion, and rename.
- Binary file change.
- Empty diff.
- Untracked file included.
- Out-of-lease diff rejected.
- Patch hash stable for the same diff.
- Claimed changed files that differ from Git are recorded as a discrepancy.

#### Step 2.6: Candidate integration

Create a dedicated integration worktree, apply Tester artifact then Builder artifact, and create a Coordinator-owned snapshot commit.

Tests:

- Deterministic two-artifact application.
- Patch conflict stops without partial accepted state.
- Wrong base commit rejected.
- Protected artifact never applied.
- Repeated assembly request is idempotent.
- Repair rebuild starts from baseline and does not accumulate previous failed changes.
- Original branch and worktree remain unchanged.

### Phase 3 — Codex runtime and Hive knowledge

#### Step 3.1: Verify the installed Codex interface

Before implementing the adapter, record the supported CLI version and invocation in `docs/CODEX_ADAPTER.md`.

The spike must answer:

- Exact non-interactive command.
- Prompt input method.
- Structured or JSONL output capabilities.
- Sandbox and approval flags.
- Working-directory behavior.
- Exit semantics.
- Cancellation behavior and child processes.
- Authentication failure signature.

Create a captured, redacted output fixture. Do not build the parser from memory or assumptions.

Validation:

- One read-only Scout prompt completes in a disposable repository.
- One writing prompt completes in a disposable worktree.
- Timeout terminates the process group.
- Unsupported version fails preflight with an actionable message.

#### Step 3.2: Generic bounded process runner

Implement asynchronous start, separate stdout/stderr capture, byte caps, deadline, cancellation, and process-group termination.

Tests use helper child processes rather than Codex:

- Successful exit.
- Non-zero exit.
- Stdout and stderr interleaving.
- Output beyond cap.
- Timeout.
- Explicit cancellation.
- Child process spawning another child; both terminate.
- No zombie process remains.

#### Step 3.3: Codex adapter

Translate `WorkerTurnRequest` into the verified CLI invocation and return `WorkerTurnResult`.

Tests:

- Command arguments and working directory match the request.
- Environment allowlist behavior.
- Version probe caching.
- Authentication and unsupported-version errors classified correctly.
- Raw output always preserved.
- Timeout and cancellation propagate typed results.

Use a fake Codex executable for all automated integration tests. Real Codex tests are an opt-in release gate.

#### Step 3.4: Prompt templates

Create one template per turn type:

- Scout.
- Builder.
- Tester planning.
- Tester execution.
- Reviewer.
- Repair.

Tests:

- Golden-file tests for required sections.
- Prompt includes exact mission, commit, leases, protected paths, and output delimiter.
- Role cannot receive authority it does not have.
- Deterministic ordering produces stable prompt hashes.
- Context byte budget truncates low-priority patches first and never drops active constraints.

#### Step 3.5: Structured handoff parser

Use an explicit start/end delimiter around one JSON object or the supported Codex structured-output mechanism.

Tests:

- Valid handoff.
- No handoff.
- Multiple handoffs.
- Truncated JSON.
- JSON embedded in ordinary prose.
- Unknown fields.
- Oversized handoff.
- Claimed changed paths disagree with Git.

Parsing failure must be a data result, not a Coordinator crash.

#### Step 3.6: Evidence validation

Implement validators per evidence type. File evidence reads the exact baseline or candidate commit using Git, not the mutable worktree filesystem.

Tests:

- Valid file and line range.
- Missing file.
- Invalid range.
- Blob SHA mismatch.
- Repository escape.
- Stale evidence after candidate commit changes.
- Agent interpretation never becomes mechanically verified.
- Coordinator-run test evidence becomes verified.

#### Step 3.7: Context compiler and knowledge receipts

Implement deterministic relevance, mandatory constraints, byte budget, stale filtering, and delivered patch IDs.

Tests:

- Role and tag relevance ordering.
- Active constraints always included.
- Disputed and superseded patches excluded or labeled.
- Evidence from an unrelated commit marked stale.
- Stable input gives stable packet and hash.
- Delivery receipt created exactly once per turn and patch.
- Acknowledged and applied receipts require explicit valid patch IDs.

### Phase 4 — Orchestration and user-visible result

#### Step 4.1: Mission state machine

Encode valid transitions as data, not scattered conditionals.

Tests:

- Every valid path reaches the intended terminal state.
- Every invalid transition fails without changing persisted state.
- State transition and event append are atomic.
- Cancellation is valid from every active state.
- Terminal states cannot restart.

Property-style table tests should enumerate every state pair.

#### Step 4.2: Scheduler and Coordinator

Implement the fixed graph:

```text
Scout
  → Builder
  → TesterPlan
Builder + TesterPlan
  → Assemble
Assemble
  → Reviewer
  → TesterExecute
Reviewer + TesterExecute
  → Repair? or Verify
Repair
  → Reassemble
Reassemble
  → Verify
```

Builder and Tester planning execute concurrently only after Scout succeeds sufficiently. Reviewer and Tester execution execute concurrently against the same immutable candidate commit.

Tests with protocol fakes:

- Happy path without repair.
- Happy path with one repair.
- Scout failure.
- Builder failure.
- Tester-planning failure with and without usable Builder artifact.
- Assembly conflict.
- Reviewer escalate verdict.
- Tester focused-test failure.
- Repair failure.
- Final verification failure.
- Mission timeout during each phase.
- Cancellation during each phase.
- Duplicate start does not duplicate workers.
- No second repair turn can be scheduled.

#### Step 4.3: Verification policy and runner

Represent commands as validated argument arrays where possible. If the UI accepts command strings, parse them with a documented non-shell parser and display the resulting arguments before launch. Never pass them through a shell.

Tests:

- All required commands pass → eligible for `verified`.
- Required command fails → `failed`.
- Optional command fails with required commands passing → `partially_verified`.
- Timeout classification.
- Output cap.
- Commands run at exact candidate commit and working directory.
- Reported result includes command arguments, exit code, duration, and output hash.

#### Step 4.4: Report builder

Generate both formats from one typed `EvidenceReport` model.

Required sections:

- Mission and baseline.
- Original-repository invariant.
- Worker roster and process results.
- Task timeline.
- Knowledge proposed, validated, delivered, acknowledged, and applied.
- Artifacts and application order.
- Combined diff summary and hash.
- Review findings.
- Tester execution.
- Coordinator verification.
- Scope violations.
- Terminal state and unresolved risks.

Tests:

- JSON validates against the Pydantic schema.
- Markdown contains every required section.
- Both formats agree on IDs, counts, commits, commands, and terminal state.
- Secrets in fixture output are redacted.
- Large logs are referenced or truncated consistently.

#### Step 4.5: Minimal Mission Control

Implement server-rendered launch, mission, and result pages. Use a small JavaScript `EventSource` handler to refresh or append event-driven state.

Tests:

- Page routes render with empty and populated missions.
- HTML escapes agent-controlled content.
- SSE reconnect preserves event order.
- Terminal event closes or idles the client cleanly.
- Accessibility smoke checks: labels, headings, status text not conveyed by color alone.

Avoid pixel-perfect work until the end-to-end fake mission passes.

### Phase 5 — End-to-end qualification

#### Step 5.1: Fake Codex executable

Build a configurable executable fixture that can:

- Emit valid and malformed handoffs.
- Modify specified files.
- Sleep or spawn a child process.
- Exit successfully or fail.
- Claim false changed files or test results.
- Produce stdout/stderr beyond caps.

The fixture is essential: it makes every failure mode deterministic and avoids API cost in CI.

#### Step 5.2: Demo repository factory

Create temporary repositories containing:

- A small application module.
- Existing health abstraction.
- Test utilities.
- Protected authentication path.
- Fast deterministic verification command.

Factory scenarios:

- Successful mission.
- Repair required.
- Conflicting artifacts.
- Protected edit.
- Verification failure.

#### Step 5.3: Full fake-worker mission tests

Assert for every scenario:

- Exact mission-state sequence.
- Expected worker-turn count.
- Worktree isolation.
- Knowledge deliveries and applied receipt.
- Artifact order and hashes.
- Correct terminal state.
- Report agreement.
- Original branch, commit, index, and status unchanged.
- Cleanup removes only mission-owned worktrees.

#### Step 5.4: Real Codex smoke tests

Mark these tests opt-in and exclude them from ordinary CI.

Required release run:

1. Scout-only disposable repository smoke test.
2. Builder-only disposable worktree smoke test.
3. Full prepared mission without repair.
4. Full prepared mission with repair.

Store timings and redacted evidence. Never store credentials or complete private prompts in committed fixtures.

#### Step 5.5: Repetition and reliability

- Run fake end-to-end happy path ten consecutive times.
- Run the prepared real-Codex demo three consecutive times.
- Record median and maximum duration.
- Fail release if any run mutates the original branch or exceeds the demo deadline.

## 8. Test strategy

### 8.1 Test layers

| Layer | Scope | External processes | Database | Git |
|---|---|---:|---:|---:|
| Unit | Pure policy, parsing, state, ranking | Fake | In-memory fake | Fake |
| Contract | Shared protocol behavior | Fake | Optional temp DB | Optional temp repo |
| Integration | Real subsystem boundary | Helper/fake Codex | Temp SQLite | Temp repositories |
| End-to-end | Complete mission | Fake Codex, then opt-in real Codex | Temp file DB | Temp repositories |

### 8.2 Required negative-test matrix

| Failure | Expected behavior |
|---|---|
| Dirty repository | Launch rejected; no worktree created |
| Unsupported Codex version | Preflight rejected with actionable error |
| Worker timeout | Process group terminated; run timed out; lease released |
| Worker crash | Failure persisted; Coordinator chooses valid next state |
| Malformed handoff | Raw output preserved; no authoritative knowledge |
| False changed-file claim | Git result wins; discrepancy recorded |
| File evidence at wrong commit | Patch stale or rejected |
| Out-of-lease edit | Artifact rejected |
| Protected-path edit | No integration; human-review state |
| Patch application conflict | Assembly stops; no semantic merge attempt |
| Reviewer escalation | Human-review state |
| Second repair requested | Rejected by state machine |
| Required verification failure | Mission failed |
| Optional verification failure | Mission partially verified |
| SSE reconnect | Missing persisted events replayed once |
| Cleanup path tampering | Cleanup refused |

### 8.3 Coverage expectations

Coverage is a diagnostic, not the release criterion. Targets:

- 90% branch coverage for state machine, lease policy, evidence validation, and verification policy.
- 80% line coverage for the overall Python package.
- Every terminal mission state reached by at least one end-to-end test.
- Every subprocess termination reason covered by an integration test.

### 8.4 Validation commands

Fast developer loop:

```bash
ruff check .
ruff format --check .
pytest tests/unit tests/contract
```

Pre-merge gate:

```bash
ruff check .
ruff format --check .
mypy src/pluribus
pytest --cov=pluribus --cov-report=term-missing
```

Release gate additionally runs fake end-to-end repetitions and the manually approved real-Codex smoke profile.

## 9. Four-person independent development allocation

The four developers work in separate branches or worktrees after the contract-freeze commit. Each owns disjoint packages and supplies fakes for consumers.

### Person 1 — Platform, contracts, persistence, and API

Branch: `feature/platform-api`

Owns:

- `pyproject.toml` and developer tooling.
- `src/pluribus/contracts/`.
- `src/pluribus/storage/`.
- `src/pluribus/api/`.
- Persistence and API contract tests.

Deliverables:

1. Bootstrap project and freeze shared contracts with team review.
2. SQLite migrations and repositories.
3. Atomic state/event transactions.
4. Persisted event stream with SSE resume.
5. Mission CRUD/start/cancel/query/report endpoints wired to orchestration protocols.
6. In-memory and SQLite-backed fakes/adapters for other developers.

Does not own:

- Git commands.
- Codex execution.
- Mission scheduling.
- Dashboard templates.

Independent test strategy:

- Use fake Coordinator and fake report builder.
- API tests run without Git or Codex installed.
- Storage tests use temporary SQLite files.

Completion gate:

- Contract suite passes.
- Migration and transaction tests pass.
- SSE reconnect test passes.
- OpenAPI schema generates without errors.

Estimated focused effort: 9–12 hours.

### Person 2 — Codex runtime, prompts, and Hive knowledge

Branch: `feature/codex-knowledge`

Owns:

- `docs/CODEX_ADAPTER.md`.
- `src/pluribus/codex/`.
- `src/pluribus/knowledge/`.
- Codex and knowledge tests and fixtures.

Deliverables:

1. Installed-Codex interface spike and recorded adapter contract.
2. Bounded asynchronous process runner.
3. Codex version probe and non-interactive adapter.
4. Role-specific prompt templates.
5. Delimited handoff parser.
6. Knowledge evidence validators.
7. Context compiler and delivery/acknowledgment/application receipts.
8. Fake Codex executable used by all workstreams.

Does not own:

- Git worktree creation or patch application.
- SQLite implementation.
- Mission scheduling.
- UI and reports.

Independent test strategy:

- Use protocol fakes for Git blob reading and persistence.
- Use helper processes and fake Codex; do not require real API calls.
- Golden-test prompts and captured redacted adapter fixtures.

Completion gate:

- Timeout terminates child process groups.
- All malformed-handoff cases pass.
- Evidence never reads an unpinned mutable file.
- Context packet output is deterministic.

Estimated focused effort: 10–14 hours.

### Person 3 — Git isolation, artifacts, scope, and verification

Branch: `feature/git-verification`

Owns:

- `src/pluribus/gitops/`.
- `src/pluribus/verification/`.
- Temporary Git repository fixtures.
- Git, lease, integration, and verification tests.

Deliverables:

1. Git command runner.
2. Clean-repository preflight and baseline capture.
3. Worktree and branch lifecycle.
4. File leases and protected-path matcher.
5. Git-derived binary-safe artifacts and hashes.
6. Deterministic candidate assembly.
7. Verification command runner and terminal-status policy.
8. Safe mission-owned cleanup checks.

Does not own:

- Codex prompts or parsing.
- Database or API.
- Coordinator state transitions.
- Dashboard.

Independent test strategy:

- Use temporary real Git repositories.
- Use static artifact fixtures and no Codex dependency.
- Use helper executables for verification pass, fail, output-cap, and timeout cases.

Completion gate:

- Every repository mutation test asserts the original tree is unchanged.
- Protected and out-of-lease artifacts cannot integrate.
- Assembly is reproducible from baseline.
- Cleanup refuses unowned paths.

Estimated focused effort: 10–14 hours.

### Person 4 — Coordinator, dashboard, reporting, and end-to-end flow

Branch: `feature/orchestration-ui`

Owns:

- `src/pluribus/orchestration/`.
- `src/pluribus/reporting/`.
- `src/pluribus/web/`.
- `src/pluribus/app.py` and `cli.py`.
- `tests/e2e/` and demo repository factory.

Deliverables:

1. Mission state machine.
2. Fixed task graph and scheduler.
3. Concurrent Builder/Tester-plan and Reviewer/Tester-execute phases.
4. One-repair-round policy.
5. Cancellation and mission deadline propagation.
6. EvidenceReport builder and Markdown/JSON renderers.
7. Minimal launch, mission, and result pages.
8. Full fake-Codex end-to-end scenarios.

Does not own:

- Shared contract definitions after freeze.
- SQLite internals.
- Codex adapter internals.
- Git worktree or patch mechanics.

Independent test strategy:

- Develop entirely against protocol fakes until integration day.
- Use scripted worker results to cover every mission state.
- Use an in-memory event and mission repository.
- UI tests consume fake events and reports.

Completion gate:

- Every state transition and terminal state is tested.
- No second repair can occur.
- Fake happy path produces matching Markdown/JSON reports.
- UI renders agent-controlled data safely.

Estimated focused effort: 10–14 hours.

## 10. Coordination rules for the four developers

### 10.1 Before branching

All four developers complete a 60–90 minute contract workshop:

1. Agree on Python and dependency versions.
2. Freeze package layout.
3. Review all shared models and protocols.
4. Agree on Git path/glob semantics.
5. Agree on event names and payload versions.
6. Commit contract fakes and behavioral test suites.

Only then create the four feature branches/worktrees.

### 10.2 Independence rules

- Never edit another owner's package without requesting a contract change.
- Add behavior behind existing protocols.
- Keep subsystem-specific models private; convert at the boundary.
- Every branch maintains passing unit and contract tests.
- Every branch includes documentation for operational assumptions.
- Do not solve integration problems by importing another subsystem's private class.

### 10.3 Daily synchronization artifacts

Each developer publishes:

- Latest commit SHA.
- Protocols implemented.
- Fakes available.
- Tests passing.
- Known deviations or contract-change requests.
- One command that validates the branch.

This is structured synchronization, not an unbounded status meeting.

## 11. Integration order and gates

Merge into an integration branch, not directly into `main`.

### Gate 1: Contract baseline

Merge Person 1's scaffold and shared-contract commit after approval from all four developers.

Required checks:

- Installation.
- Contract tests.
- Ruff.
- Mypy on contracts.

### Gate 2: Platform persistence/API

Merge the remainder of Person 1's work.

Required checks:

- Migration suite.
- API suite.
- SSE resume test.

### Gate 3: Git and verification

Merge Person 3's subsystem.

Required checks:

- Temporary-repository integration suite.
- Original-tree invariant tests.
- Scope and protected-path negative tests.

### Gate 4: Codex and knowledge

Merge Person 2's subsystem.

Required checks:

- Process runner suite.
- Parser and prompt golden tests.
- Knowledge validation and context determinism.
- Fake Codex available to the combined repository.

### Gate 5: Orchestration, report, and UI

Merge Person 4's subsystem last because it composes the other protocols.

Required checks:

- State-machine suite.
- Full fake-Codex mission.
- Report consistency.
- API-to-SSE-to-UI smoke test.

### Gate 6: Release qualification

- Full pre-merge validation command.
- Ten consecutive fake happy paths.
- All negative end-to-end scenarios.
- Three consecutive approved real-Codex demo runs.
- Manual report review.
- Confirm no secret is present in tracked fixtures or logs.

## 12. Suggested four-person schedule

The original one-day target is achievable only as a highly focused four-person hackathon, with the adapter behavior confirmed early.

| Time | Person 1 | Person 2 | Person 3 | Person 4 |
|---|---|---|---|---|
| 0:00–1:15 | Joint contract/scaffold freeze | Joint contract/scaffold freeze | Joint contract/scaffold freeze | Joint contract/scaffold freeze |
| 1:15–3:30 | DB and events | Codex spike and process runner | Git preflight and worktrees | State machine with fakes |
| 3:30–5:30 | API and SSE | Parser, prompts, fake Codex | Leases and artifacts | Scheduler and report with fakes |
| 5:30–7:30 | Persistence hardening | Knowledge validation/context | Integration and verification | Minimal dashboard and E2E fixtures |
| 7:30–9:00 | Integrate platform | Integrate adapter | Integrate Git subsystem | Adapt orchestration to real protocols |
| 9:00–10:30 | Cross-system fixes | Cross-system fixes | Cross-system fixes | Full fake end-to-end qualification |
| 10:30–12:00 | Real demo and report review | Real demo and adapter fixes | Original-tree/safety audit | Demo UI and presentation |

If the Codex spike is not complete by hour 2.5, stop adding features and use a documented fake-worker demo while preserving the real adapter as an explicit incomplete risk. Do not disguise a fake as real Codex execution.

## 13. Definition of done by feature

A feature is done only when:

1. It implements an approved contract.
2. Positive and negative tests pass.
3. It emits required events.
4. Failures return typed, persisted results.
5. It does not mutate resources outside its ownership boundary.
6. Operational assumptions are documented.
7. Ruff, mypy, and relevant tests pass.
8. Another developer can run its validation command from a clean checkout.

A mission is done only when the Coordinator reaches a defined terminal state and produces consistent Markdown and JSON evidence. An agent's statement that work is complete is never the definition of done.

## 14. Open decisions that must be resolved before code

1. Exact supported Codex CLI version and invocation.
2. Exact sandbox and approval profile used for each role.
3. Whether verification inputs are strictly argument arrays or parsed command strings.
4. Glob semantics and case sensitivity on each supported operating system.
5. Location and retention policy for mission worktrees and raw logs.
6. Maximum prompt, stdout, stderr, event payload, and database-log sizes.
7. Minimum secret-redaction patterns and user-configurable additions.
8. Whether ignored files cause dirty-preflight rejection in the first release.
9. Whether read-only roles receive dedicated worktrees or a shared immutable baseline view.

Record each decision in a short ADR. Unresolved decisions are blockers for their dependent features, not invitations for four developers to choose different behavior.

## 15. Post-MVP hardening backlog

- Container or VM worker isolation.
- CPU, memory, process, and network quotas.
- Authentication and per-repository authorization.
- Signed artifacts and evidence.
- Durable background-job recovery.
- Multiple concurrent missions.
- Semantic conflict assistance with human approval.
- Cross-repository knowledge namespaces and retention policies.
- Cost and token accounting.
- Load testing before any worker-scale claim.
- Windows-specific process-group and path validation.
- GitHub and CI integrations.
