# Pluribus for Codex

**Many Codex agents. One shared, evidence-backed working memory.**

> Codex agents do not need a group chat. They need a shared evidence ledger.

Pluribus for Codex is a local multi-agent orchestration layer that coordinates several Codex workers on one software mission. Each agent receives a specialized role, writing agents use isolated Git worktrees, and evidence-backed discoveries, constraints, risks, decisions, and test results propagate through a shared Hive Blackboard.

The goal is not merely to run several agents in parallel. The goal is to make an insight discovered by one agent change the work performed by the others—without giving agents a shared, collision-prone filesystem or allowing unsupported claims to become collective truth.

## Core loop

```text
Scout discovers a repository fact
              ↓
Fact is linked to file/test evidence
              ↓
Hive Blackboard validates, labels, and stores it
              ↓
Builder, Tester, and Reviewer consume it
              ↓
Coordinator deterministically integrates test and implementation patches
              ↓
Independent verification proves the result
```

## One-day hackathon MVP

The MVP deliberately uses a fixed, reliable workflow:

```text
Scout → Builder + Tester Phase A → Integrate → Verify → Reviewer → Final Verify
```

- **Scout:** maps the repository and publishes evidence-backed findings.
- **Builder:** implements the smallest compliant patch in an isolated worktree.
- **Tester:** creates acceptance criteria and a focused test patch in parallel with Builder; the Coordinator later runs those tests against the integrated result.
- **Reviewer:** challenges the integrated diff and Coordinator-run test evidence for scope, security, and regressions.
- **Coordinator:** owns bounded scheduling, context synchronization, deterministic Git integration, and independent verification.

## Key principles

1. **Shared evidence, not shared chatter** — agents publish structured Knowledge Patches rather than unbounded conversations.
2. **Independent reasoning, isolated execution** — writing agents use separate Git worktrees and branches.
3. **Evidence-weighted consensus** — executed tests and source references outrank unsupported agent opinions.
4. **Turn-boundary synchronization** — the latest relevant Hive context is injected before each bounded Codex turn.
5. **Coordinator-owned verification** — an agent's claim of success never substitutes for real test output.
6. **Causal knowledge tracking** — the system distinguishes a patch delivered to a worker from a patch the worker actually consumed and used.

## MVP technology

- Python 3.11 + FastAPI
- SQLite event and knowledge store
- `asyncio` subprocess supervision
- Git branches/worktrees
- Server-Sent Events
- React/Vite or HTMX dashboard
- Local Codex CLI adapter

## Product requirements

The complete product requirements document is available at [docs/PRD.md](docs/PRD.md).

## Status

Scope-frozen v0.2 product specification. The implementation is intentionally limited to one fixed demo repository and mission, four fixed Codex roles, maximum concurrency of two, a three-panel dashboard, and one independently verified result.

## License

MIT
