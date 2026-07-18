# Pluribus for Codex

**The open registry for reusable, verified Codex memories.**

> GitHub for useful Codex memories.

Pluribus lets developers publish debugging methods and coding best practices learned with Codex, discover memories created by others, install them into a local Pluribus-managed Codex memory pack, and preserve evidence that an installed memory was actually used and followed by successful verification.

## Core loop

```text
Publish → Discover → Install → Codex Uses → Verify
```

A useful technique should not disappear inside one developer's Codex conversation. Pluribus turns it into a versioned Memory Capsule with explicit triggers, reusable steps, compatibility metadata, sanitized evidence, and usage receipts.

## Fixed hackathon demo

Developer A publishes a verified memory for fixing duplicate pytest module collisions with `--import-mode=importlib`. Developer B finds and installs it. Pluribus injects the matching memory into a bounded Codex task. The resulting repository change passes coordinator-run verification, and a receipt connects the publisher, memory, consumer, changed file, and test output.

## Honest boundary

Pluribus does not claim to mutate hidden Codex model memory. It manages explicit local memory packages and injects relevant installed memories into Codex task context through the Codex adapter.

## Pivot documents

- [Memory Registry scope and shared contract](docs/MEMORY_REGISTRY_SCOPE.md)
- [Four-person execution plan](docs/TEAM_EXECUTION_PLAN_V2.md)

The earlier mission-orchestration PRD and execution plan remain in the repository as historical hackathon work but are superseded by the documents above for the current build.

## MVP technology

- Python 3.11 + FastAPI
- SQLite registry and usage-receipt store
- Local Markdown memory packages with hashed manifests
- Local Codex CLI adapter
- Safe coordinator-run verification
- React/Vite marketplace UI

## Status

Pivot scope frozen for the one-day hackathon MVP. The only required end-to-end story is:

```text
one developer publishes a verified memory
→ another developer discovers and installs it
→ Codex receives and uses it
→ coordinator verification passes
```

## License

MIT
