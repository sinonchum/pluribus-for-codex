# Pluribus for Codex

**Engineering knowledge handoff for Codex.**

When an experienced engineer leaves, Git preserves the code but not the judgment behind it. Pluribus turns company-specific engineering decisions into sanitized, employee-approved Memory Capsules that a successor can install into Codex—and proves when that knowledge changed a real outcome.

## Demo story

Alice maintained Northstar Billing for four years. Before leaving, she publishes one implicit rule:

> Never assign `invoice.status` directly. Every billing transition must use `transition_invoice()` so the append-only financial audit trail is recorded first.

Bob inherits a task to add invoice cancellation. Pluribus matches Alice's handoff, injects it into a bounded real Codex CLI run, Codex changes only `billing/invoices.py`, and coordinator-run verification returns `3 passed`. A Usage Receipt links Alice, the installed memory, Bob, the code delta, and the test proof.

## Interactive Terminal Codex demo

From the repository root:

```bash
env -u VIRTUAL_ENV uv run --project backend \
  python demo/start-handoff-codex.py
```

This opens a normal interactive Codex TUI in a fresh Billing Service workspace. A
project-level `UserPromptSubmit` hook runs on every action, matches installed
Pluribus memories against the user's prompt, and adds the selected Memory ID,
matched trigger, and reusable steps to Codex's model context.

In Codex, enter:

```text
Fix the failing tests by implementing cancel an invoice support. Before editing,
state the exact Pluribus Memory ID and matched trigger injected for this action.
Then implement the fix and run uv run pytest -q.
```

After Codex finishes, ask:

```text
上个 action 使用了什么 Pluribus memory？
```

Codex should answer `mem_billing_audit_handoff_v1`, `cancel an invoice`, and show
`3 passed`. The original fixture remains red so the demo is repeatable.

## Automated Terminal demo and Live Receipt

For a non-interactive fallback that also publishes a Usage Receipt into a running Live UI:

```bash
env -u VIRTUAL_ENV uv run --project backend \
  python demo/run-handoff-live.py --api-base http://127.0.0.1:8011
```

The runner deliberately proves the failing baseline first, installs Alice's Memory Capsule locally, invokes the real `codex exec` CLI in `workspace-write` sandbox mode, runs `uv run pytest -q`, and retains the temporary workspace for inspection.

## Run Live API and UI

Terminal 1:

```bash
cd backend
PLURIBUS_DB_PATH=/tmp/pluribus-handoff.db \
  uv run uvicorn app.main:app --host 127.0.0.1 --port 8011
```

Terminal 2:

```bash
cd frontend
VITE_API_BASE_URL=http://127.0.0.1:8011 npm run dev -- --host 127.0.0.1 --port 5177
```

Open `http://127.0.0.1:5177/?mode=live`.

## Trust boundary

Pluribus does **not** upload raw Codex conversations. The intended publish flow is local extraction, secret removal, departing-employee review, private/team publication, explicit project installation, bounded prompt injection, and coordinator verification.

## Quality gates

```bash
cd backend && uv run pytest -q
cd frontend && npm test -- --run && npm run typecheck && npm run build && npm audit --audit-level=high
```
