# Pluribus for Codex

**Many Codex agents. One shared, evidence-backed working memory.**

Pluribus for Codex is a local multi-agent orchestration layer that coordinates several Codex workers on one software mission. Each agent receives a specialized role and an isolated Git worktree, while verified discoveries, constraints, risks, decisions, and test results propagate through a shared Hive Blackboard.

The goal is not merely to run several agents in parallel. The goal is to make an insight discovered by one agent change the work performed by the others—without giving agents a shared, collision-prone filesystem or allowing unsupported claims to become collective truth.

## Core loop

```text
Scout discovers a repository fact
              ↓
Fact is linked to file/test evidence
              ↓
Hive Blackboard verifies and stores it
              ↓
Builder, Tester, and Reviewer consume it
              ↓
Coordinator integrates one candidate patch
              ↓
Independent verification proves the result
```

## Four-person hackathon MVP

The MVP deliberately uses a fixed, reliable workflow with a two-turn Tester:

```text
Scout → Builder + Tester planning → candidate assembly
      → Reviewer + Tester execution → optional repair
      → Coordinator verification
```

- **Scout:** maps the repository and publishes evidence-backed findings.
- **Builder:** implements the smallest compliant patch in an isolated worktree.
- **Tester:** plans acceptance evidence in parallel with Builder, then executes focused tests against the assembled candidate.
- **Reviewer:** challenges the candidate diff for scope, security, and regressions.
- **Coordinator:** owns scheduling, context synchronization, Git integration, and final verification.

## Key principles

1. **Shared evidence, not shared chatter** — agents publish structured Knowledge Patches rather than unbounded conversations.
2. **Independent reasoning, isolated execution** — writing agents use separate Git worktrees and branches.
3. **Evidence-weighted consensus** — executed tests and source references outrank unsupported agent opinions.
4. **Turn-boundary synchronization** — the latest relevant Hive context is injected before each bounded Codex turn.
5. **Coordinator-owned verification** — an agent's claim of success never substitutes for real test output.

## MVP technology

- Python 3.11 + FastAPI
- SQLite event and knowledge store
- `asyncio` subprocess supervision
- Git branches/worktrees
- Server-Sent Events
- React/Vite or HTMX dashboard
- Local Codex CLI adapter

## Product and implementation documents

- [Product requirements](docs/PRD.md)
- [Detailed implementation, testing, dependency, and four-person delivery plan](docs/IMPLEMENTATION_PLAN.md)

## Status

Build-ready product and implementation specification. The implementation is scoped as a focused four-person hackathon vertical slice.

## License

MIT
