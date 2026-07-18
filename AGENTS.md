# AGENTS.md — Pluribus Engineering Handoff

## Current product

Pluribus preserves company-specific engineering judgment when an experienced engineer leaves. It packages sanitized, employee-approved knowledge as explicit local Codex memories and proves their use through coordinator-verified Usage Receipts.

Do not describe the product as raw conversation upload, hidden model-state transfer, or automatic employee surveillance.

## Frozen demo contract

- Publisher: `Alice Chen · Billing, 4 years`
- Successor: `Bob · Successor Engineer`
- Memory ID: `mem_billing_audit_handoff_v1`
- Slug: `preserve-billing-audit-trail`
- Title: `Preserve billing audit trail during invoice transitions`
- Trigger: `add a new invoice status`
- Rule: never assign `invoice.status` directly; use `transition_invoice()` so the append-only ledger is recorded first.
- Task: add `InvoiceStatus.CANCELLED` and `cancel_invoice()`.
- Exact changed file: `billing/invoices.py`
- Verification: `uv run pytest -q` → exit `0` → `3 passed`

Golden path:

```text
Alice publishes handoff
→ Bob discovers and installs it
→ Pluribus matches the cancellation task
→ explicit Memory Context is injected into real Codex CLI
→ Codex changes billing/invoices.py only
→ coordinator verification passes
→ Usage Receipt proves Alice → Memory → Bob → change → tests
```

## Trust and security boundaries

- Local extraction and secret removal precede publication.
- The departing engineer must review and approve the capsule.
- Installations are explicit files under `.pluribus/installed/<slug>/`.
- Reject path traversal, unsafe symlinks, manifest tampering, and unbounded context.
- Verification commands are executable/argument arrays; never use `shell=True`.
- CORS remains localhost-only.
- Never record or print OAuth credentials.

## Development commands

```bash
cd backend
uv run pytest -q
uv run ruff check .
uv run ruff format --check .

cd ../frontend
npm test -- --run
npm run typecheck
npm run build
npm audit --audit-level=high
```

## Real demo command

```bash
uv run --project backend python demo/run-handoff-live.py \
  --api-base http://127.0.0.1:8011
```

The runner must prove the failing baseline, invoke the real `codex exec` CLI in workspace-write sandbox mode, report the exact one-file delta, verify three tests, and optionally publish the receipt to Live API.
