# Product Requirements Document: Pluribus for Codex

| Field | Value |
|---|---|
| Product | Pluribus for Codex |
| Version | 0.1 Hackathon MVP |
| Tagline | Many Codex agents. One shared working memory. |
| Build constraint | One working day |
| Recommended demo scale | Four Codex agents |
| Architecture ceiling | 10–20 local workers without fundamental redesign |
| Product category | Local multi-agent coding orchestrator |

## 1. Executive summary

Pluribus for Codex coordinates multiple Codex agents working toward one software objective. Instead of giving every agent the same prompt and allowing them to duplicate exploration or collide on files, Pluribus assigns distinct roles, isolates all writing agents with Git worktrees, and synchronizes validated knowledge through a central Hive Blackboard.

The Pluribus-inspired premise is simple:

> An insight discovered by one agent becomes available to the collective, while every agent continues to reason and execute independently.

The MVP does not attempt to synchronize hidden model state or mutate a running Codex context window. That would be fragile and unnecessary. It implements **operational hive memory** at bounded turn boundaries:

1. An agent discovers a repository fact, constraint, risk, or test result.
2. The agent publishes a structured Knowledge Patch with evidence.
3. The Coordinator validates and stores it.
4. Subsequent turns receive the relevant verified patches.
5. The UI shows which agents consumed each discovery.
6. The Coordinator integrates one candidate solution and independently verifies it.

The result should feel like a synchronized engineering collective while remaining feasible, inspectable, and safe enough for a local hackathon demo.

---

## 2. Problem statement

### 2.1 Independent parallel agents

Running multiple coding agents in parallel is easy, but coordination is weak:

- Every agent repeats repository exploration.
- Agents infer contradictory architecture.
- Multiple agents modify the same files.
- Useful discoveries remain trapped in individual context windows.
- The user receives several disconnected patches instead of one verified result.

### 2.2 One large sequential agent

A single agent avoids file conflicts but introduces other limits:

- No parallelism
- Long-context degradation
- Weak role specialization
- Single-agent failure risk
- Difficult recovery after a confused run

### 2.3 Product opportunity

Pluribus combines independent execution with a shared, evidence-backed blackboard:

```text
Independent reasoning
        +
Shared verified memory
        +
Isolated Git execution
        +
Controlled integration
        =
A practical Codex hive mind
```

---

## 3. Product goals

### 3.1 Hackathon goals

The one-day MVP must demonstrate that:

1. Four real Codex workers participate in one mission.
2. Every worker has a distinct role and bounded task.
3. Writing agents never share a mutable working directory.
4. At least two discoveries from one agent are consumed by another.
5. The UI displays agents, tasks, knowledge, and evidence in real time.
6. One candidate solution is integrated into a dedicated branch.
7. Verification commands are run by the Coordinator, not merely reported by an agent.
8. The mission ends with a reviewable evidence report.

### 3.2 Product goals

- Reduce repeated repository exploration.
- Increase useful parallel throughput.
- Prevent destructive concurrent edits.
- Preserve validated knowledge after agent failure.
- Make agent coordination visible and auditable.
- Separate facts from hypotheses and opinions.
- Produce one integrated result rather than several patches.

### 3.3 Explicit non-goals for v0.1

- Synchronizing model activations or hidden state
- Injecting context into a generation already in progress
- Distributed execution across physical machines
- Production-grade sandboxing or authentication
- Arbitrary semantic merge-conflict resolution
- Simultaneous multi-agent editing of the same file
- Support for every coding-agent CLI
- Persistent cross-repository organizational memory
- Training, fine-tuning, or modifying Codex
- Automatically merging into the user's original branch

---

## 4. Users and jobs to be done

### Primary user

A developer who uses Codex CLI and wants multiple agents to solve a repository-level task without manually coordinating prompts, branches, discoveries, and tests.

### Secondary users

- Hackathon teams
- Open-source maintainers
- Engineering leads evaluating autonomous development
- Developer-tool builders
- Multi-agent researchers

### Primary job

> When I have a task involving architecture discovery, implementation, tests, and review, coordinate several Codex agents so their useful discoveries are shared, their edits do not collide, and I receive one independently verified result.

---

## 5. Core abstraction: the Hive Blackboard

The Hive Blackboard is an append-only store of:

- Mission requirements
- Tasks and dependencies
- Repository facts
- Hypotheses
- Decisions
- Constraints
- Risks
- File leases
- Candidate patches
- Test results
- Review findings
- Agent lifecycle events

Agents do not conduct unrestricted peer-to-peer conversations. They publish structured Knowledge Patches. This prevents context explosion and keeps every consequential assertion traceable.

### 5.1 Knowledge Patch schema

```json
{
  "id": "kp_018",
  "mission_id": "mission_001",
  "agent_id": "scout_1",
  "type": "repository_fact",
  "summary": "Health checks are implemented through HealthService.",
  "details": "Routes receive HealthService through the application container.",
  "evidence": [
    {
      "type": "file_reference",
      "path": "src/services/health.ts",
      "line_start": 12,
      "line_end": 64
    }
  ],
  "tags": ["health", "architecture", "dependency-injection"],
  "relevant_to": ["builder", "tester", "reviewer"],
  "confidence": 0.98,
  "status": "verified",
  "created_at": "2026-07-18T11:04:20Z"
}
```

### 5.2 Patch types

| Type | Purpose |
|---|---|
| `repository_fact` | Existing architecture, convention, or file location |
| `constraint` | Required or forbidden behavior |
| `decision` | An accepted implementation choice |
| `hypothesis` | An unverified explanation requiring investigation |
| `risk` | Security, compatibility, or regression concern |
| `test_result` | Command, exit code, and output evidence |
| `candidate_patch` | A proposed code change |
| `conflict` | Contradictory findings or overlapping edits |
| `task_update` | Progress, dependency, or blocker |

### 5.3 Knowledge states

- `proposed`
- `verified`
- `disputed`
- `superseded`
- `rejected`

Only verified facts are presented as authoritative in future prompts. Proposed hypotheses are labeled explicitly.

### 5.4 Evidence priority

When claims conflict, evidence is ranked:

1. Executed test result
2. Current source-code reference
3. Current Git diff
4. Repository documentation
5. Agent interpretation
6. Unsupported assertion

Pluribus uses evidence-weighted consensus, not majority voting. Three unsupported agents do not outrank one executable test.

---

## 6. Agent model

### 6.1 Scout

**Purpose:** Map the repository before implementation.

**Responsibilities:**

- Locate relevant source and test files.
- Identify established abstractions and conventions.
- Find realistic verification commands.
- Publish repository facts with exact evidence.
- Suggest task decomposition.

**Code-write permission:** None.

### 6.2 Builder

**Purpose:** Produce the smallest compliant implementation.

**Responsibilities:**

- Consume verified Scout findings.
- Modify only leased paths in an isolated worktree.
- Follow existing conventions.
- Run focused checks.
- Produce a candidate Git diff and structured handoff.

**Code-write permission:** Assigned implementation files only.

### 6.3 Tester

**Purpose:** Convert the mission into executable proof.

**Responsibilities:**

- Define acceptance criteria.
- Locate or create tests.
- Cover failure and edge cases.
- Evaluate the candidate implementation.
- Publish actual test evidence.

**Code-write permission:** Assigned test files only.

### 6.4 Reviewer

**Purpose:** Challenge the candidate patch.

**Responsibilities:**

- Inspect the candidate diff.
- Check scope, architecture, security, and regressions.
- Identify unsupported claims and missing tests.
- Return `accept`, `repair`, or `escalate` with evidence.

**Code-write permission:** None in the initial review.

### 6.5 Coordinator

The Coordinator is application logic, not a free-running coding agent.

**Responsibilities:**

- Capture repository baseline.
- Build the task graph.
- Create branches and worktrees.
- Start, supervise, and stop Codex processes.
- Construct role-specific context packets.
- Validate Knowledge Patches.
- Manage file leases.
- Apply selected patches.
- Run final verification.
- Produce the evidence report.

The Coordinator owns integration and verification. Agents never merge their own work.

---

## 7. Synchronization model

Pluribus uses turn-boundary synchronization:

```text
1. Coordinator assigns a bounded task.
2. Agent receives the newest relevant verified Hive context.
3. Agent executes one bounded Codex turn.
4. Agent returns a result and Knowledge Patches.
5. Coordinator validates and stores them.
6. Task graph and leases are updated.
7. The next turn receives the context delta.
```

Recommended turn limits:

| Turn | Target duration |
|---|---:|
| Repository exploration | 2–3 minutes |
| Implementation | 5–7 minutes |
| Test design/execution | 3–5 minutes |
| Review | 2–3 minutes |
| Repair | 3–5 minutes |

### 7.1 Context packet

```markdown
## Mission
Add a detailed health endpoint.

## Your role
Builder: implement the smallest compliant patch.

## Verified Hive knowledge
1. Health checks use `HealthService`.
   Evidence: `src/services/health.ts:12-64`
2. Health routes are registered in `src/routes/index.ts`.
   Evidence: `src/routes/index.ts:17-22`

## Active constraints
- Do not modify authentication.
- Do not add dependencies.
- Do not edit migrations.

## Files leased to you
- `src/routes/health.ts`
- `src/services/health.ts`

## Expected output
Return changed files, commands, test results, discoveries, and risks.
```

### 7.2 Relevance filtering

All active constraints, accepted decisions, and critical risks are included. Other patches are ranked using deterministic signals:

```text
score = role relevance
      + tag overlap
      + assigned-file overlap
      + task dependency
      + evidence strength
      - disputed penalty
```

Embeddings are unnecessary for the one-day MVP.

---

## 8. Git isolation and file leases

Every writing agent runs in an isolated worktree:

```text
worktrees/
├── builder-1/
├── tester-1/
└── repair-1/
```

Each worktree uses a dedicated branch:

```text
hive/mission-001/builder-1
hive/mission-001/tester-1
hive/mission-001/repair-1
```

### Lease rules

- Many agents may read the same path.
- Only one agent may hold a write lease on a file at a time.
- The Coordinator checks actual Git changes against the lease.
- Changes outside leased paths are flagged and rejected by default.
- Expired leases are automatically released.
- Protected paths can never be integrated automatically.

If two tasks need the same file, the second task waits. After the first patch is integrated, the second agent receives the updated branch and current Hive context.

---

## 9. Mission workflow

The fixed MVP pipeline is:

```text
Scout → Builder + Tester → Reviewer → Integrate → Verify
```

Detailed algorithm:

```python
capture_repository_baseline()
create_integration_branch()
run_scout()
validate_and_publish_scout_findings()

run_in_parallel(
    builder_with_hive_context,
    tester_with_hive_context,
)

run_reviewer(
    objective,
    verified_hive_memory,
    builder_diff,
    tester_acceptance_criteria,
)

if reviewer_requests_repair:
    run_one_bounded_repair_turn()

apply_selected_patches_to_integration_branch()
run_coordinator_verification()
generate_evidence_report()
```

Scout runs first because its findings reduce duplicated exploration. Builder and Tester then run concurrently. Reviewer runs when a real candidate diff and acceptance criteria exist.

---

## 10. Functional requirements

### FR-01 — Create a mission

The user can select a Git repository, enter an objective, choose 2–6 agents, set protected paths, specify verification commands, and launch the Hive.

**Acceptance criteria:**

- Non-Git directories are rejected.
- Starting commit, branch, and dirty state are recorded.
- Existing changes produce a visible warning.
- A unique mission identifier is created.

### FR-02 — Create specialized workers

**Acceptance criteria:**

- The system creates Scout, Builder, Tester, and Reviewer roles.
- Every worker receives a role-specific prompt.
- Every process has a unique identifier and status.
- Logs remain separately inspectable.

### FR-03 — Supervise Codex subprocesses

**Acceptance criteria:**

- Working directory and full prompt are explicit.
- Stdout, stderr, exit code, duration, and timeout are captured.
- A failed worker does not crash the Coordinator.
- A timed-out worker is terminated.
- No worker is marked successful without a real process result.

### FR-04 — Isolate edits

**Acceptance criteria:**

- Every writing worker has its own worktree and branch.
- The source branch remains unchanged during execution.
- Worktrees can be cleaned up after the mission.

### FR-05 — Publish shared knowledge

**Acceptance criteria:**

- Structured Knowledge Patches are parsed from agent output.
- Every patch records author, timestamp, and status.
- Referenced files are checked for existence.
- Unsupported claims remain proposed.
- Verified patches can enter future context packets.

### FR-06 — Demonstrate synchronization

**Acceptance criteria:**

- New turns receive the latest relevant verified patches.
- The UI records which worker consumed each patch.
- Superseded findings are removed or labeled.
- At least two patches are reused across workers in the demo.

### FR-07 — Enforce scope

**Acceptance criteria:**

- Protected paths cannot be integrated automatically.
- Changes outside a worker's lease are visible.
- Manifest changes can be flagged as dependency additions.
- Violating patches are rejected or require explicit human acceptance.

### FR-08 — Review candidate patches

**Acceptance criteria:**

- Reviewer receives objective, constraints, diff, and test evidence.
- Every finding has severity and evidence.
- Critical findings block integration.
- Verdict is `accept`, `repair`, or `escalate`.

### FR-09 — Integrate deterministically

**Acceptance criteria:**

- Only the Coordinator modifies the integration branch.
- Selected patches are applied and failures are reported.
- The original branch remains recoverable.

### FR-10 — Verify independently

**Acceptance criteria:**

- Required commands run on the integrated result.
- Commands, exit codes, and output are stored.
- Success requires all required checks to pass.
- Agent self-reports cannot replace Coordinator evidence.

### FR-11 — Generate an evidence report

The final report includes objective, baseline commit, agent roster, task timeline, consumed knowledge, candidate patches, final diff, verification output, scope violations, review findings, and unresolved risks.

Valid final states:

- `verified`
- `partially_verified`
- `failed`
- `requires_human_review`

---

## 11. User experience

### 11.1 Launch screen

Inputs:

- Repository path
- Mission objective
- Agent count
- Timeout
- Maximum repair rounds
- Protected paths
- Verification commands

Default configuration:

```yaml
agents: 4
timeout_minutes: 12
repair_rounds: 1
roles: [scout, builder, tester, reviewer]
protected_paths: [.env, .git/**, migrations/**]
verification: [npm test]
```

Primary action: **Launch Hive**.

### 11.2 Mission Control

The dashboard has four primary panels:

1. **Agent roster** — role, task, state, duration, and branch.
2. **Task graph** — dependencies, blocked work, and completion.
3. **Hive memory** — findings, evidence, status, and consumers.
4. **Evidence** — candidate diff, review, tests, and final result.

The key visual should show knowledge propagation:

```text
Scout ──kp_018──▶ Builder
              ├─▶ Tester
              └─▶ Reviewer
```

### 11.3 Result screen

```text
MISSION RESULT: VERIFIED

Agents used:           4
Verified discoveries:  9
Cross-agent reuse:      6
Candidate patches:      2
Accepted patch:         builder-1
Tests:                  18 passed
Scope violations:       0
Protected files:        unchanged
```

---

## 12. Technical architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                    Web Mission Control                      │
│ Objective │ Agents │ Tasks │ Memory │ Diff │ Evidence      │
└──────────────────────────────┬──────────────────────────────┘
                               │ REST + SSE
┌──────────────────────────────▼──────────────────────────────┐
│                    Coordinator API                          │
│ Mission Manager │ Scheduler │ Context Compiler │ Verifier  │
│ Event Broker    │ Leases    │ Git Integrator   │ Reporter  │
└────────────┬───────────────┬───────────────────┬────────────┘
             │               │                   │
      ┌──────▼─────┐  ┌──────▼─────┐     ┌──────▼─────┐
      │ SQLite     │  │ Git Layer  │     │ Codex      │
      │ missions   │  │ branches   │     │ Adapter    │
      │ tasks      │  │ worktrees  │     │ processes  │
      │ patches    │  │ diffs      │     │ timeouts   │
      │ events     │  │ integration│     │ logs       │
      └────────────┘  └────────────┘     └──────┬─────┘
                                                │
                          ┌─────────┬────────────┼──────────┐
                          │         │            │          │
                       Scout     Builder       Tester    Reviewer
```

### Recommended stack

- Python 3.11
- FastAPI
- SQLite
- `asyncio` subprocess management
- Git CLI
- Server-Sent Events
- React/Vite or HTMX

SSE is sufficient because the main real-time requirement is server-to-browser progress. Avoid WebSocket complexity in the MVP.

---

## 13. Minimal persistence model

```sql
CREATE TABLE missions (
  id TEXT PRIMARY KEY,
  repository_path TEXT NOT NULL,
  objective TEXT NOT NULL,
  starting_commit TEXT NOT NULL,
  integration_branch TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  completed_at TEXT
);

CREATE TABLE agents (
  id TEXT PRIMARY KEY,
  mission_id TEXT NOT NULL,
  role TEXT NOT NULL,
  status TEXT NOT NULL,
  worktree_path TEXT,
  branch_name TEXT,
  process_id INTEGER,
  started_at TEXT,
  completed_at TEXT,
  exit_code INTEGER
);

CREATE TABLE knowledge_patches (
  id TEXT PRIMARY KEY,
  mission_id TEXT NOT NULL,
  agent_id TEXT NOT NULL,
  type TEXT NOT NULL,
  summary TEXT NOT NULL,
  details TEXT,
  evidence_json TEXT,
  tags_json TEXT,
  relevant_to_json TEXT,
  confidence REAL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  mission_id TEXT NOT NULL,
  agent_id TEXT,
  event_type TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
```

Additional tables may store tasks, leases, candidate patches, and verification runs.

---

## 14. API surface

```http
POST /api/missions
POST /api/missions/{id}/start
POST /api/missions/{id}/stop
GET  /api/missions/{id}
GET  /api/missions/{id}/agents/{agent_id}
GET  /api/missions/{id}/knowledge
GET  /api/missions/{id}/events
GET  /api/missions/{id}/report
```

`GET /events` returns `text/event-stream`.

Mission creation example:

```json
{
  "repository_path": "C:/projects/demo-api",
  "objective": "Add a detailed health endpoint with tests.",
  "agent_count": 4,
  "protected_paths": [".env", "src/auth/**"],
  "verification_commands": ["npm test"]
}
```

---

## 15. Codex agent output contract

Agents should end with a machine-readable block:

```json
{
  "status": "completed",
  "summary": "Implemented detailed health endpoint.",
  "changed_files": ["src/routes/health.ts"],
  "commands_run": [
    {"command": "npm test -- health", "exit_code": 0}
  ],
  "knowledge_patches": [
    {
      "type": "repository_fact",
      "summary": "Application version comes from package metadata.",
      "evidence": [
        {
          "type": "file_reference",
          "path": "src/config/version.ts",
          "line_start": 4,
          "line_end": 8
        }
      ],
      "tags": ["version", "configuration"],
      "relevant_to": ["tester", "reviewer"],
      "confidence": 0.97
    }
  ],
  "risks": [
    "Database timeout remains inherited from the existing service."
  ]
}
```

If JSON parsing fails, Pluribus preserves raw output, derives changed files from Git, marks the handoff unstructured, and does not trust claimed tests.

---

## 16. Failure handling

### Agent crash

- Store stderr and exit code.
- Preserve worktree and diff.
- Mark task failed.
- Release leases.
- Continue if the task is noncritical.

### Timeout

- Terminate the process.
- Store partial output.
- Mark produced claims unverified.
- Allow one bounded reassignment if configured.

### Unauthorized edits

- Record a scope violation.
- Reject the affected patch by default.
- Never apply protected-path changes automatically.

### Failed verification

- Publish the failure as a verified test result.
- Permit one bounded repair turn.
- Finish as failed or partially verified if checks still fail.

### Merge conflict

The MVP does not attempt arbitrary semantic conflict resolution. It applies patches serially where possible and otherwise requires human review.

---

## 17. Security model

The MVP is a localhost developer tool, not a secure sandbox. Codex processes can execute commands with the current user's permissions.

Minimum protections:

- Bind the API to localhost.
- Do not expose `.env` content in the UI.
- Redact obvious tokens from logs.
- Block `.git/**` edits.
- Support user-defined protected paths.
- Set process timeouts.
- Preserve the starting commit.
- Require explicit action before changing the original branch.

Production versions require containers or VMs, resource limits, network policy, secret isolation, authentication, repository permissions, and signed evidence.

---

## 18. Success metrics

### Hackathon acceptance

| Metric | Required result |
|---|---:|
| Participating Codex workers | At least 4 |
| Writing workers isolated | 100% |
| Shared findings propagated | At least 2 |
| Evidence-backed findings | At least 80% |
| Protected-path violations integrated | 0 |
| Coordinator verification | Executed |
| Live dashboard | Working |
| Deterministic demo duration | Under 5 minutes |

### Core product metric

**Cross-agent knowledge reuse rate**

```text
Knowledge Patches consumed by another worker
────────────────────────────────────────────
Total verified Knowledge Patches
```

This proves that Pluribus is more than a parallel process launcher.

Additional metrics:

- Time to verified solution
- Duplicate repository searches avoided
- Candidate-patch acceptance rate
- Scope-violation rate
- Repair rounds per mission
- Verification pass rate
- Human interventions
- Cost relative to a single-agent baseline

---

## 19. One-day implementation plan

### Hour 0–1 — Freeze scope and demo

- Select one small repository.
- Select one deterministic cross-cutting task.
- Fix the roles at Scout, Builder, Tester, and Reviewer.
- Limit the mission to one repair round.

**Exit criterion:** The task can be solved manually in under ten minutes.

### Hour 1–3 — Backend foundation

- Create mission, agent, event, and patch models.
- Initialize SQLite.
- Capture repository baseline.
- Create integration branch and worktrees.
- Implement bounded subprocess execution.

**Exit criterion:** A process runs in a worktree and its output, exit code, and diff are stored.

### Hour 3–5 — Codex adapter and roles

- Implement four role prompt templates.
- Invoke the local Codex CLI through an adapter.
- Capture raw output.
- Parse final structured handoff.
- Emit agent lifecycle events.

**Exit criterion:** Every role can run independently against the demo repository.

### Hour 5–6.5 — Hive memory

- Parse Knowledge Patches.
- Validate file evidence.
- Implement proposed/verified states.
- Compile role-specific context packets.
- Track patch consumption.

**Exit criterion:** A Scout finding automatically appears in the Builder's next prompt and in the dashboard.

### Hour 6.5–8 — Orchestration and proof

- Implement `Scout → Builder + Tester → Reviewer`.
- Add leases and protected paths.
- Capture candidate diffs.
- Apply selected patch to the integration branch.
- Run verification and one optional repair turn.

**Exit criterion:** A complete mission produces a real verification result.

### Hour 8–10 — Mission Control

Build four panels:

1. Agent roster
2. Task graph
3. Hive memory stream
4. Diff and evidence

**Exit criterion:** An observer understands what the collective is doing without reading terminal logs.

### Hour 10–11 — Hardening

- Run the exact demo repeatedly.
- Cap prompts and timeouts.
- Add reset and cleanup commands.
- Remove unreliable optional behavior.
- Record a fallback demo.

**Exit criterion:** Three consecutive successful runs.

### Hour 11–12 — Presentation

Prepare and rehearse a 90-second pitch and a five-minute demo. Add no new features.

---

## 20. Priority and scope control

### P0 — Must ship

- Mission creation
- Four fixed roles
- Codex subprocess execution
- Git worktree isolation
- Knowledge Patches
- Context propagation
- Live agent status
- Candidate diff
- Coordinator verification
- Evidence report

### P1 — Only after P0 works

- File lease visualization
- Protected-path enforcement
- One repair round
- Conflict display
- Knowledge-consumption animation

### P2 — Post-hackathon

- Dynamic role generation
- Multiple competing Builders
- Semantic memory retrieval
- Cross-machine workers
- GitHub issue and PR integration
- Container sandboxing
- Cost-aware scheduling
- Persistent project memory
- Agent performance scoring

---

## 21. Demo specification

### Demo repository characteristics

Use a small web API containing:

- Existing but non-obvious health infrastructure
- A version utility
- Authentication middleware
- Established test mocking conventions
- Fast tests
- A protected authentication directory

### Mission

> Add an endpoint that reports application version, uptime, and database health. Reuse existing health infrastructure, add degraded-state tests, and update API documentation. Do not change authentication or add dependencies.

### Five-minute narrative

1. **Problem:** Parallel agents repeat work and collide.
2. **Launch:** Create a mission with four roles and protected paths.
3. **Discovery:** Scout finds `HealthService` with source evidence.
4. **Synchronization:** The finding visibly flows to Builder, Tester, and Reviewer.
5. **Parallel work:** Builder implements while Tester defines proof in separate worktrees.
6. **Collective correction:** Reviewer catches unsafe exposure of a raw database exception.
7. **Repair:** A bounded repair turn consumes the shared risk and corrects it.
8. **Proof:** Coordinator runs tests and confirms protected files are unchanged.

The key demonstration is causal:

```text
Scout discovers fact
        ↓
Fact enters Hive memory
        ↓
Builder consumes fact
        ↓
Implementation changes
        ↓
Reviewer challenges result
        ↓
Coordinator proves completion
```

---

## 22. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Codex turns run too long | Demo stalls | Bounded turns and prepared repository |
| Agent output is malformed | Parser fails | Raw fallback and Git-derived truth |
| Edits overlap | Merge conflict | Worktrees and single-writer leases |
| Memory becomes noisy | Poor agent performance | Verification, filtering, and hard limits |
| Hallucination propagates | Collective error | Evidence checks and knowledge states |
| API cost becomes excessive | Weak viability | Four fixed roles and compact context |
| Tests are slow | Weak live demo | Small repository and focused commands |
| Reviewer loops forever | No completion | Maximum one repair round |
| UI consumes the day | Backend unfinished | Backend-first development and SSE |
| Product appears to be a process launcher | Weak novelty | Show one agent's finding changing another's work |

---

## 23. Roadmap

### Phase 1 — Hackathon MVP

- Four fixed roles
- Local execution
- Shared blackboard
- Git isolation
- Evidence report

**Exit criterion:** A complete mission succeeds consistently in under five demo minutes.

### Phase 2 — Adaptive Hive

- Dynamic task decomposition
- Multiple Builder candidates
- Capability-aware role assignment
- Better relevance ranking
- Cost and latency budgets
- Human approval gates

**Exit criterion:** Reliable results across three representative repositories.

### Phase 3 — Team integration

- GitHub issue and pull-request ingestion
- CI integration
- Container sandboxing
- Persistent project memory
- Organization policies
- Mission replay

**Exit criterion:** A real team can use Pluribus safely on pull requests.

### Phase 4 — Distributed collective

- Remote workers
- Specialized security and performance agents
- Shared repository knowledge graph
- Cross-mission learning
- Evidence-based agent reputation

**Exit criterion:** Ten or more agents cooperate without unbounded conflict or context growth.

---

## 24. Positioning

Do not describe Pluribus as:

> We run several Codex agents at once.

That is easy to reproduce. The product claim is:

> **Pluribus turns independent Codex processes into an evidence-sharing engineering collective. Each agent works in isolation, while discoveries, constraints, risks, and test results propagate through shared verified memory.**

The defensible idea is not agent count. It is the combination of:

- Structured shared knowledge
- Evidence-linked claims
- Visible cross-agent consumption
- Isolated execution
- Controlled integration
- Independent verification

That is a credible, feasible implementation of a Codex hive mind—and a focused one-day hackathon product.
