# Product Requirements Document: Pluribus for Codex

| Field | Value |
|---|---|
| Product | Pluribus for Codex |
| Version | 0.2 Build-ready hackathon MVP |
| Tagline | Many Codex agents. One shared, evidence-backed working memory. |
| Product category | Local multi-agent coding orchestrator |
| MVP worker count | Four fixed Codex workers |
| MVP workflow | Scout → Builder + Tester planning → candidate assembly → Reviewer + Tester execution → optional repair → Coordinator verification |
| Build target | One focused vertical slice; 12 engineering hours only with four developers |
| Supported environment | Local Git repository, Python 3.11+, Codex CLI installed and authenticated |

## 1. Product objective

Build a local orchestration system that accepts a clean Git repository and a software objective, runs four bounded Codex roles in isolated worktrees, propagates evidence-backed discoveries between those roles, integrates approved changes into a separate branch, and returns independently executed verification evidence without modifying the user's original branch or working tree.

The MVP succeeds only when it can prove all of the following:

1. Four real Codex worker processes participated as Scout, Builder, Tester, and Reviewer.
2. Every writing turn ran in an isolated Git worktree.
3. At least two evidence-backed Knowledge Patches were delivered to another worker.
4. At least one worker acknowledged and applied a Knowledge Patch produced by another worker.
5. No protected-path or out-of-lease change was integrated.
6. The Coordinator assembled one deterministic candidate on a dedicated integration branch.
7. The Coordinator, rather than an agent, executed the required verification commands.
8. The original branch, commit, index, and working tree remained unchanged.
9. The mission produced a reviewable report containing prompts, evidence, diffs, commands, exit codes, and unresolved risks.

## 2. Executive summary

Pluribus for Codex coordinates multiple Codex workers toward one repository-level objective. It does not give every worker the same prompt or a shared writable directory. It assigns distinct roles, isolates writing turns with Git worktrees, and synchronizes validated discoveries through a central Hive Blackboard.

The defining product claim is:

> Pluribus turns independent Codex processes into an evidence-sharing engineering collective. Agents reason separately, while repository facts, constraints, risks, decisions, and test results propagate through shared, commit-pinned working memory.

The system does not synchronize model activations, hidden state, or an in-progress generation. It provides operational shared memory at bounded turn boundaries:

1. A worker receives a role-specific task and a context packet.
2. The worker investigates, edits, or reviews inside a bounded Codex turn.
3. The worker returns a structured handoff and optional Knowledge Patches.
4. The Coordinator derives filesystem and process truth independently.
5. Evidence validators classify each patch.
6. Later turns receive only relevant, non-stale knowledge.
7. The Coordinator assembles and verifies the final candidate.

## 3. Problem and product opportunity

### 3.1 Uncoordinated parallel agents

Running several coding agents concurrently commonly causes:

- Repeated repository exploration.
- Contradictory architectural assumptions.
- Overlapping edits and merge conflicts.
- Useful discoveries trapped in individual context windows.
- Unsupported claims copied into later prompts.
- Several disconnected patches instead of one verified result.

### 3.2 One long-running agent

A single sequential agent avoids direct edit conflicts but sacrifices:

- Parallel exploration and test design.
- Role specialization.
- Failure isolation.
- Short, auditable reasoning boundaries.
- Recovery when context becomes confused or stale.

### 3.3 Product opportunity

```text
Independent reasoning
        +
Shared commit-pinned evidence
        +
Isolated Git execution
        +
Deterministic integration
        +
Coordinator-owned verification
        =
A practical Codex engineering collective
```

## 4. Users and jobs to be done

### Primary user

A developer who uses Codex CLI and wants several agents to complete a repository-level task without manually coordinating prompts, worktrees, discoveries, reviews, and tests.

### Primary job

> When a task requires repository discovery, implementation, test design, review, and proof, coordinate specialized Codex workers so their discoveries are reused, their edits remain isolated, and I receive one independently verified candidate branch.

### Secondary users

- Hackathon teams.
- Open-source maintainers.
- Engineering leads evaluating autonomous development.
- Developer-tool builders and multi-agent researchers.

## 5. Scope

### 5.1 P0: required MVP capabilities

- One mission at a time.
- Exactly four fixed worker roles.
- Clean local Git repositories only.
- Recorded repository baseline and immutable original branch.
- Bounded Codex subprocess execution.
- Separate worktree and branch for every writing turn.
- Structured Knowledge Patches with commit-pinned evidence.
- Deterministic evidence validation and knowledge-state transitions.
- Context-packet compilation with delivery receipts.
- File leases and protected-path enforcement before integration.
- Deterministic candidate assembly on a dedicated branch.
- Reviewer verdict and one optional repair turn.
- Coordinator-owned verification.
- Live mission events using Server-Sent Events.
- Markdown and JSON evidence reports.
- Cleanup command that never deletes the original repository or branch.

### 5.2 P1: only after the complete P0 path works

- Rich lease and task-graph visualization.
- Configurable role-specific timeouts in the UI.
- Improved secret redaction.
- Mission replay from stored events.
- Manual approval of otherwise rejected changes.
- Multiple predefined demo profiles.

### 5.3 Explicit non-goals for v0.2

- Variable worker counts or dynamic role generation.
- Multiple competing Builders.
- Distributed or cross-machine workers.
- Production-grade sandboxing.
- Arbitrary semantic conflict resolution.
- Simultaneous writing to the same file.
- Persistent memory shared across repositories.
- Automatic changes to the user's original branch.
- GitHub issue, pull-request, or CI integration.
- Embedding-based knowledge retrieval.
- Supporting coding-agent CLIs other than Codex.
- A claim that the architecture supports 10–20 workers without measured evidence.

## 6. Roles and authority

### 6.1 Scout

Purpose: map the repository and publish useful, evidence-backed findings before implementation.

Responsibilities:

- Locate relevant source, test, configuration, and documentation files.
- Identify established abstractions and conventions.
- Identify realistic verification commands.
- Identify protected or high-risk areas.
- Publish repository facts, constraints, risks, and hypotheses.
- Suggest disjoint Builder and Tester file leases.

Authority:

- Read-only repository access.
- No integration authority.
- No authority to classify its own semantic claims as mechanically verified.

### 6.2 Builder

Purpose: implement the smallest compliant change.

Responsibilities:

- Consume verified or supported Scout findings.
- Edit only leased implementation paths.
- Follow existing repository conventions.
- Run focused checks when available.
- Return a structured handoff and candidate artifact.
- Cite Knowledge Patch identifiers that materially influenced the change.

Authority:

- Write access only inside its isolated worktree.
- Candidate production only; no integration or final-verification authority.

### 6.3 Tester

Purpose: convert the mission into executable proof. Tester has two bounded turns.

Turn A — Test planning, concurrent with Builder:

- Define observable acceptance criteria.
- Locate existing test utilities and conventions.
- Add or modify tests only in leased test paths when tests can be written independently.
- Publish risks, test strategy, and intended commands.

Turn B — Test execution, after candidate assembly:

- Inspect the assembled candidate.
- Execute focused tests against the candidate.
- Record command, working directory, commit, exit code, duration, and bounded output.
- Identify missing coverage or behavior mismatch.

Authority:

- Write access to leased test paths during Turn A.
- Read-only access to the assembled candidate during Turn B.
- No final-verification authority.

### 6.4 Reviewer

Purpose: challenge the assembled candidate independently.

Responsibilities:

- Review the combined implementation-and-test diff.
- Check scope, architecture, security, regression risk, and acceptance coverage.
- Validate whether cited Knowledge Patches were applied appropriately.
- Return findings with severity, evidence, and a verdict.

Verdicts:

- `accept`: no blocking finding.
- `repair`: a bounded, actionable change can resolve the blocking finding.
- `escalate`: human judgment or semantic conflict resolution is required.

Authority:

- Read-only candidate access.
- No code-writing or integration authority in v0.2.

### 6.5 Coordinator

The Coordinator is deterministic application logic, not a fifth coding agent.

It exclusively owns:

- Mission state transitions.
- Repository preflight and baseline capture.
- Branch and worktree lifecycle.
- Codex process supervision.
- Prompt and context-packet construction.
- Knowledge validation and delivery receipts.
- File leases and scope checks.
- Candidate assembly.
- Repair scheduling.
- Final verification.
- Evidence report generation.

Agents never merge, cherry-pick, change the integration branch, or declare the final mission successful.

## 7. Workflow and state machine

### 7.1 Fixed MVP workflow

```text
Repository preflight
        ↓
Scout discovery
        ↓
Builder implementation ─────┐
                            ├─ concurrent
Tester planning/tests ──────┘
        ↓
Candidate assembly
        ↓
Reviewer analysis ──────────┐
                            ├─ concurrent read-only turns
Tester execution ───────────┘
        ↓
Optional one-turn repair
        ↓
Candidate rebuild
        ↓
Coordinator verification
        ↓
Evidence report and cleanup eligibility
```

### 7.2 Mission states

```text
created
  → preflight
  → scouting
  → building_and_test_planning
  → assembling
  → reviewing_and_testing
  → repairing (optional)
  → verifying
  → terminal state
```

Terminal states:

- `verified`: all required commands passed, no scope violation was integrated, and no blocking finding remains.
- `partially_verified`: required commands passed but one or more explicitly optional checks did not pass or could not run.
- `failed`: required verification failed or no valid candidate could be assembled.
- `requires_human_review`: a protected-path change, integration conflict, critical unresolved review finding, or ambiguous decision requires a person.
- `cancelled`: the user cancelled the mission.
- `timed_out`: the mission exceeded its overall deadline.

Every transition is validated. Repeating a start, stop, assembly, or verification request must be idempotent or return a deterministic conflict response.

### 7.3 Turn synchronization

Each bounded worker turn follows the same protocol:

1. Coordinator selects a task whose dependencies are satisfied.
2. Coordinator compiles the latest relevant context at a specific repository commit.
3. Coordinator stores a hash and Knowledge Patch IDs for the context packet.
4. Codex runs with an explicit role, working directory, deadline, and output contract.
5. Coordinator records stdout, stderr, exit code, duration, and termination reason.
6. Coordinator derives changed files and diffs directly from Git.
7. Structured handoff parsing is attempted.
8. Knowledge Patches are validated and stored.
9. Leases, task state, and downstream context are updated.

No context is injected into a turn already in progress.

## 8. Hive Blackboard and evidence model

### 8.1 Knowledge Patch

```json
{
  "id": "kp_018",
  "mission_id": "mission_001",
  "agent_id": "scout_1",
  "type": "repository_fact",
  "summary": "Health routes delegate checks to HealthService.",
  "details": "The route receives HealthService through the application container.",
  "repository_commit": "3f34e7c...",
  "evidence": [
    {
      "type": "file_reference",
      "path": "src/services/health.ts",
      "line_start": 12,
      "line_end": 64,
      "blob_sha": "70c52b..."
    }
  ],
  "tags": ["health", "architecture", "dependency-injection"],
  "relevant_to": ["builder", "tester", "reviewer"],
  "confidence": 0.98,
  "state": "supported",
  "created_at": "2026-07-18T11:04:20Z"
}
```

### 8.2 Patch types

| Type | Purpose |
|---|---|
| `repository_fact` | Existing architecture, convention, or file location |
| `constraint` | Required or forbidden behavior |
| `decision` | Coordinator-accepted implementation choice |
| `hypothesis` | Unverified explanation requiring investigation |
| `risk` | Security, compatibility, or regression concern |
| `test_result` | Executed command and result at a commit |
| `candidate_patch` | Proposed code or test artifact |
| `conflict` | Contradictory findings or overlapping edits |
| `task_update` | Progress, dependency, or blocker |

### 8.3 Knowledge states

- `proposed`: received but not validated.
- `supported`: attached evidence exists at the recorded commit and structurally supports inspection; semantic truth is not mechanically guaranteed.
- `verified`: mechanically established, such as an executed command result, exact diff, blob identity, or Coordinator policy result.
- `disputed`: contradicted by current evidence.
- `superseded`: replaced or invalidated by a later commit or accepted decision.
- `rejected`: malformed, unsupported, unsafe, or outside mission scope.

Agents may propose a state, but only Coordinator validators persist the effective state.

### 8.4 Validation rules

| Evidence type | Required validation |
|---|---|
| File reference | Relative path, no repository escape, file exists at recorded commit, line range valid, blob SHA matches |
| Git diff | Base and head commits exist, diff can be reproduced, changed paths recorded |
| Test result | Coordinator executed command, commit and working directory recorded, exit code and bounded output captured |
| Documentation reference | File and range exist at commit; claim remains `supported` unless mechanical |
| Agent interpretation | May be `proposed` or `supported`, never automatically `verified` |

Active constraints, accepted decisions, critical risks, and mechanically verified results are always considered for downstream context. Stale patches are excluded or clearly labeled.

### 8.5 Knowledge delivery and reuse

Track three separate events:

- `delivered`: patch ID appeared in a worker's context packet.
- `acknowledged`: worker returned the patch ID as relevant.
- `applied`: worker linked the patch ID to a concrete decision, changed file, test, or review finding.

The MVP's mechanical acceptance criterion requires at least two delivered patches. The demo must also show at least one acknowledged-and-applied patch.

## 9. Context packets

Context packets contain:

- Mission objective and observable acceptance criteria.
- Role and bounded task.
- Baseline or candidate commit.
- Relevant supported and verified Hive knowledge.
- Active constraints and critical risks.
- Leased and protected paths.
- Allowed output artifact.
- Expected machine-readable handoff.

Deterministic relevance score:

```text
score = role relevance
      + tag overlap
      + assigned-path overlap
      + task dependency
      + evidence strength
      + recency at current commit
      - disputed penalty
      - stale penalty
```

The MVP uses deterministic filtering and a hard byte limit. It does not require embeddings.

## 10. Repository safety, worktrees, and artifacts

### 10.1 Preflight

The MVP accepts a repository only when:

- The path resolves to a Git working tree.
- `HEAD` resolves to a commit.
- No tracked, staged, untracked, conflicted, or ignored-sensitive change selected by policy makes the baseline ambiguous.
- The Codex CLI is installed and satisfies the supported version check.
- Verification commands are non-empty and explicitly shown to the user.
- The integration branch name does not already conflict with unrelated work.

By default, any non-empty `git status --porcelain=v1 --untracked-files=all` rejects launch. The system never stashes, commits, resets, or cleans the user's repository automatically.

Baseline capture includes:

- Repository root.
- Original branch or detached-HEAD state.
- Starting commit.
- Full porcelain status.
- Configured protected paths.
- Verification commands.

### 10.2 Worktree rules

- Every writing turn receives a dedicated worktree and branch.
- Read-only roles may use a read-only logical view or a dedicated worktree for uniformity.
- Many workers may read the same path.
- Only one active writing lease may cover a path.
- The Coordinator compares actual Git changes with the lease before accepting an artifact.
- Out-of-lease changes reject the artifact by default.
- Protected-path changes always produce `requires_human_review` and are never integrated automatically.

Leases are integration-policy controls, not operating-system filesystem permissions.

### 10.3 Candidate artifact contract

For each writing turn, the Coordinator records:

- Baseline commit.
- Worktree branch.
- Changed paths derived from Git.
- Reproducible binary-safe diff or a single validated worker commit.
- Diff hash.
- Lease-validation result.
- Protected-path-validation result.
- Structured handoff if parseable.

The MVP uses Coordinator-generated patches from the worktree diff. Worker-created merges are rejected. Worker commits may be preserved for inspection but are not trusted as the integration mechanism.

### 10.4 Deterministic assembly

1. Reset the dedicated integration worktree to the recorded baseline, never the user's working tree.
2. Apply the accepted Tester test artifact, if one exists.
3. Apply the accepted Builder implementation artifact.
4. Record application order and resulting commit.
5. If application fails, stop with `requires_human_review`; do not attempt semantic conflict resolution.
6. Reviewer and Tester execution inspect this combined candidate.
7. After repair, rebuild from baseline using the accepted artifacts plus the repair artifact.

The Coordinator alone modifies the integration branch.

## 11. Codex adapter contract

The implementation must define and test one supported Codex invocation mode.

Required adapter behavior:

- Detect CLI presence and record version.
- Invoke Codex non-interactively with explicit working directory and prompt.
- Apply a documented approval and sandbox profile.
- Pass only allowlisted environment variables where practical.
- Capture stdout and stderr separately with byte limits.
- Record start time, end time, duration, exit code, and termination reason.
- Enforce per-turn timeout and mission cancellation.
- Terminate the complete child process group on timeout.
- Preserve raw output even when parsing fails.
- Extract exactly one final structured handoff using an unambiguous delimiter or supported structured-output mode.
- Reject unsupported adapter versions during preflight rather than guessing.
- Prevent agents from receiving integration credentials or authority.

The precise CLI command and supported-version matrix belong in the implementation plan and must be verified against the installed Codex release before coding the adapter.

## 12. Agent output contract

Every worker is instructed to finish with one delimited JSON object:

```json
{
  "status": "completed",
  "summary": "Implemented the detailed health response.",
  "changed_files": ["src/routes/health.ts"],
  "commands_run": [
    {"command": "npm test -- health", "claimed_exit_code": 0}
  ],
  "knowledge_used": [
    {"patch_id": "kp_018", "application": "Reused HealthService rather than adding a second database check."}
  ],
  "knowledge_patches": [],
  "risks": []
}
```

Rules:

- `changed_files` is advisory; Git-derived paths are authoritative.
- Agent-reported commands and exit codes are claims until executed or observed by the Coordinator.
- Parse failure preserves raw output and marks the handoff `unstructured`.
- An unstructured handoff may still yield an inspectable artifact, but cannot introduce authoritative knowledge or claimed test success.

## 13. Functional requirements

### FR-01 — Create and preflight a mission

- Accept repository path, objective, protected paths, verification commands, and timeout profile.
- Reject non-Git or dirty repositories.
- Record baseline and display commands before launch.
- Create a unique mission ID.

### FR-02 — Create four specialized workers

- Create exactly one Scout, Builder, Tester, and Reviewer.
- Give every turn a role-specific prompt and unique run ID.
- Keep logs and state independently inspectable.

### FR-03 — Supervise Codex subprocesses

- Capture real process results and timeouts.
- A worker failure must not crash the Coordinator.
- No worker is successful without a terminal process result.

### FR-04 — Isolate and validate edits

- Use separate worktrees for writing turns.
- Check actual changed paths against leases and protected paths.
- Leave the original repository untouched.

### FR-05 — Publish and validate knowledge

- Parse structured patches.
- Pin evidence to a repository commit.
- Apply evidence-type-specific validators.
- Prevent agents from self-verifying semantic claims.

### FR-06 — Demonstrate synchronization

- Store context-packet hashes and delivered patch IDs.
- Record acknowledgment and application separately.
- Show at least two cross-worker deliveries and one applied reuse in the demo.

### FR-07 — Assemble a candidate deterministically

- Apply accepted artifacts in documented order.
- Stop on conflicts or protected-path violations.
- Never change the original branch.

### FR-08 — Review and test the assembled candidate

- Reviewer receives objective, constraints, combined diff, and available evidence.
- Tester Turn B executes focused commands against the combined candidate.
- Every blocking finding includes severity and evidence.

### FR-09 — Run at most one repair turn

- Repair receives only actionable blocking findings and current candidate evidence.
- Repair writes in a fresh worktree with an explicit lease.
- Candidate is rebuilt deterministically after repair.

### FR-10 — Verify independently

- Run all required commands on the final candidate commit.
- Store exact commands, working directory, exit codes, durations, and bounded output.
- Required-check failure prevents `verified` status.

### FR-11 — Stream observable progress

- Emit ordered mission events with monotonically increasing IDs.
- SSE clients can reconnect using the last event ID.
- UI state can be reconstructed from persisted events and current records.

### FR-12 — Generate an evidence report

Report objective, baseline, worker runs, task timeline, knowledge delivery, artifacts, combined diff, findings, verification results, scope checks, terminal state, and unresolved risks in Markdown and JSON.

## 14. User experience

### Launch

Inputs:

- Repository path.
- Mission objective.
- Protected path patterns.
- Required verification commands.
- Optional verification commands.
- Demo or standard timeout profile.

There is no agent-count control in the MVP.

### Mission Control

The minimum dashboard shows:

1. Mission phase and terminal state.
2. Four worker cards with current turn, duration, and branch.
3. Hive memory with state, evidence, and delivery/application receipts.
4. Candidate diff, findings, commands, and results.

The UI is server-rendered HTML with a small EventSource client for the MVP. A separate frontend build system is not required.

### Result

```text
MISSION RESULT: VERIFIED

Workers:                    4
Knowledge patches:          9
Cross-worker deliveries:    6
Acknowledged and applied:    2
Accepted artifacts:          2
Required checks:             3 passed
Scope violations integrated: 0
Original branch unchanged:   yes
```

## 15. Technical architecture

```text
┌─────────────────────────────────────────────────────────────┐
│ Server-rendered Mission Control + EventSource client        │
└──────────────────────────────┬──────────────────────────────┘
                               │ REST + SSE
┌──────────────────────────────▼──────────────────────────────┐
│ Coordinator API                                             │
│ State machine │ Scheduler │ Context compiler │ Reporter     │
│ Event broker  │ Leases    │ Candidate builder │ Verifier    │
└────────────┬───────────────┬───────────────────┬─────────────┘
             │               │                   │
      ┌──────▼─────┐  ┌──────▼─────┐     ┌──────▼─────┐
      │ SQLite     │  │ Git layer  │     │ Codex      │
      │ state      │  │ worktrees  │     │ adapter    │
      │ events     │  │ artifacts  │     │ processes  │
      │ evidence   │  │ assembly   │     │ parsing    │
      └────────────┘  └────────────┘     └──────┬─────┘
                                                │
                              Scout │ Builder │ Tester │ Reviewer
```

Recommended MVP stack:

- Python 3.11 or newer.
- FastAPI and Uvicorn.
- Pydantic v2.
- SQLite through `aiosqlite`.
- Jinja2 server-rendered templates.
- Native browser `EventSource` API.
- Git CLI.
- `asyncio` subprocess management.
- Pytest, pytest-asyncio, and HTTPX for tests.
- Ruff for formatting and linting; mypy for targeted static checks.

The detailed dependency rationale and package boundaries are defined in [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md).

## 16. Persistence and events

The blackboard uses immutable domain events plus current-state tables. At minimum persist:

- Missions and validated state transitions.
- Tasks and dependencies.
- Worker runs and process results.
- Knowledge Patches and knowledge-state events.
- Context-packet hashes and delivery receipts.
- File leases.
- Candidate artifacts and application attempts.
- Review findings.
- Verification runs.
- Ordered mission events.

Every mission-scoped table is indexed by `mission_id`. Events use a monotonically increasing integer ID for SSE resumption. Database migrations are explicit and tested against a new database and the previous schema version once one exists.

## 17. API surface

```http
POST /api/missions
POST /api/missions/{id}/start
POST /api/missions/{id}/cancel
GET  /api/missions/{id}
GET  /api/missions/{id}/workers
GET  /api/missions/{id}/knowledge
GET  /api/missions/{id}/artifacts
GET  /api/missions/{id}/report
GET  /api/missions/{id}/events
POST /api/missions/{id}/cleanup
```

`GET /events` returns `text/event-stream`, supports `Last-Event-ID`, and emits persisted event IDs. Start, cancel, and cleanup operations are idempotent.

## 18. Failure handling

### Worker crash or malformed output

- Store process evidence and raw output.
- Derive any changed paths from Git.
- Reject authoritative knowledge from an unstructured handoff.
- Continue only when downstream correctness is still possible.

### Timeout or cancellation

- Terminate the entire worker process group.
- Store partial output and termination reason.
- Mark produced semantic claims untrusted.
- Release leases after process termination is confirmed.

### Scope or protected-path violation

- Store the diff and violation.
- Reject automatic integration.
- Use `requires_human_review` for protected-path changes.

### Failed patch application

- Preserve the failed application evidence.
- Do not perform semantic conflict resolution.
- Finish as `requires_human_review`.

### Failed verification

- Publish Coordinator-executed failure evidence.
- Permit one repair turn only if no repair has already run and the failure is actionable.
- Otherwise finish as `failed` or `partially_verified` according to required/optional status.

## 19. Security model

The MVP is a localhost developer tool, not a secure sandbox. Codex subprocesses execute with the current user's operating-system permissions. Protected paths prevent automatic integration; they do not prevent reads or writes outside the repository.

Required safeguards:

- Bind HTTP only to loopback by default.
- Display and require acknowledgment of the execution-risk statement.
- Reject dirty repositories.
- Never interpolate user strings into shell commands.
- Invoke subprocesses with argument arrays, not `shell=True`.
- Apply worktree, lease, and protected-path checks.
- Redact configured secrets and common credential shapes from displayed logs.
- Cap stored and streamed output.
- Terminate process groups on cancellation and timeout.
- Never pass GitHub tokens or integration credentials to workers.
- Never stash, reset, clean, delete, or rewrite the user's repository.
- Require explicit user action before cleanup of Pluribus-created worktrees.

Container or VM isolation, resource quotas, network policy, secret isolation, authentication, and signed evidence remain production requirements.

## 20. Success metrics

### Hackathon acceptance

| Metric | Required result |
|---|---:|
| Codex roles completed or explicitly failed with evidence | 4 |
| Writing turns isolated | 100% |
| Cross-worker Knowledge Patch deliveries | At least 2 |
| Acknowledged and applied reuse | At least 1 |
| Protected or out-of-lease violations integrated | 0 |
| Required verification commands executed by Coordinator | 100% |
| Original repository unchanged | Yes |
| Evidence report generated | Markdown and JSON |
| Prepared demo duration | Under 5 minutes |

### Product metrics

- Delivered, acknowledged, and applied knowledge reuse rates.
- Time to verified candidate.
- Duplicate repository searches avoided.
- Artifact acceptance rate.
- Scope-violation rate.
- Verification pass rate.
- Human interventions.
- Repair success rate.
- Token, cost, and latency relative to a single-agent baseline.

## 21. Demo specification

Use a small prepared web API with existing health infrastructure, a version utility, authentication middleware, established test conventions, fast tests, and a protected authentication directory.

Mission:

> Add an endpoint that reports application version, uptime, and database health. Reuse existing health infrastructure, add degraded-state tests, and update API documentation. Do not change authentication or add dependencies.

Five-minute narrative:

1. Launch a mission against a clean repository.
2. Scout finds `HealthService` and test conventions with commit-pinned evidence.
3. The UI shows those patches delivered to Builder, Tester, and Reviewer.
4. Builder implements while Tester writes acceptance tests in separate worktrees.
5. Coordinator assembles the combined candidate.
6. Reviewer identifies raw exception exposure; Tester demonstrates it with a failing focused test.
7. One repair turn removes the unsafe detail.
8. Coordinator rebuilds the candidate and executes required verification.
9. Report proves tests passed, protected paths were not integrated, and the original branch is unchanged.

## 22. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Codex invocation differs by installed version | Adapter fails | Version-gated adapter contract and preflight probe |
| Turns exceed demo time | Demo stalls | Prepared repository, demo timeout profile, bounded prompts |
| Agent output is malformed | Knowledge parser fails | Raw-output preservation and Git-derived truth |
| Agents edit outside scope | Unsafe artifact | Worktree isolation and pre-integration path validation |
| Evidence becomes stale | Wrong context propagates | Commit-pinned evidence and supersession checks |
| Builder and tests conflict | Candidate cannot assemble | Disjoint leases and deterministic stop on conflict |
| Hallucination propagates | Collective error | Supported versus verified states and evidence validators |
| Verification command is unsafe | Host risk | Explicit display, argument-array execution, documented trust boundary |
| UI consumes implementation time | Core workflow unfinished | Server-rendered HTML and native EventSource |
| Product looks like a launcher | Weak differentiation | Demonstrate acknowledged and applied cross-agent evidence |

## 23. Release exit criteria

The MVP is ready to demonstrate only when:

1. Unit, integration, and end-to-end suites pass from a clean checkout.
2. The fake-Codex end-to-end fixture completes deterministically at least ten consecutive times.
3. Three consecutive real-Codex prepared-demo missions reach `verified` in under five minutes each.
4. Timeout, cancellation, malformed output, out-of-lease edits, protected-path edits, failed application, and failed verification have automated tests.
5. Original-branch invariants are asserted before and after every end-to-end mission.
6. Markdown and JSON reports agree on terminal state, commits, commands, and evidence counts.

## 24. Roadmap

### Phase 1 — Build-ready hackathon MVP

Four fixed roles, local execution, evidence-backed shared memory, Git isolation, deterministic assembly, independent verification, and minimal Mission Control.

### Phase 2 — Adaptive local hive

Dynamic task decomposition, multiple candidate Builders, capability-aware assignment, richer retrieval, cost budgets, and human approval gates.

### Phase 3 — Team integration

GitHub issue and pull-request ingestion, CI integration, container sandboxing, persistent project memory, organization policies, and mission replay.

### Phase 4 — Distributed collective

Remote workers, specialized security and performance roles, cross-mission knowledge, and evidence-based worker evaluation. Scale claims require measured load and reliability testing.

## 25. Positioning

Do not describe Pluribus as merely running several Codex agents at once.

The product is the combination of:

- Structured, commit-pinned shared knowledge.
- Evidence-aware claim states.
- Visible delivery and application of discoveries.
- Isolated execution.
- Deterministic integration.
- Coordinator-owned verification.

The implementation sequence, test matrix, dependencies, four-person ownership model, and integration gates are specified in [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md).
