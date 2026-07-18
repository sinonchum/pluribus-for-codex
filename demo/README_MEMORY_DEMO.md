# Pluribus Engineering Handoff Demo

## One-line pitch

**Git saves the code. Pluribus saves the engineering judgment needed to change it safely.**

## Characters

- **Alice Chen:** four-year Northstar Billing maintainer who is leaving the team.
- **Bob:** successor engineer inheriting Billing Service and its Codex workflow.
- **Implicit knowledge:** every invoice state transition must use `transition_invoice()`; direct status assignment silently bypasses the financial audit ledger.

## Golden path

1. **Explore:** search `billing`; open **Preserve billing audit trail during invoice transitions**.
2. **Inspect:** show Alice's tenure, implicit team rule, matching triggers, reusable judgment, and `3 passed` publisher evidence.
3. **Install:** install the reviewed handoff to Bob's Codex.
4. **Terminal:** run the real Codex CLI handoff command.
5. **Receipt:** show Alice → Memory → Bob → `billing/invoices.py` → `uv run pytest -q` → `3 passed`.

## Start Live mode

```bash
# Terminal 1
cd backend
rm -f /tmp/pluribus-handoff.db
PLURIBUS_DB_PATH=/tmp/pluribus-handoff.db \
  uv run uvicorn app.main:app --host 127.0.0.1 --port 8011

# Terminal 2
cd frontend
VITE_API_BASE_URL=http://127.0.0.1:8011 npm run dev -- --host 127.0.0.1 --port 5177
```

Open:

```text
http://127.0.0.1:5177/?mode=live
```

## Run real Codex and publish its receipt

From the repository root:

```bash
uv run --project backend python demo/run-handoff-live.py \
  --api-base http://127.0.0.1:8011
```

Expected proof:

```text
BASELINE — KNOWLEDGE GAP
... cancel_invoice ... failed ...

LIVE — KNOWLEDGE HANDOFF
memory_id: mem_billing_audit_handoff_v1
consumer: Bob · Successor Engineer
changed_files: billing/invoices.py
verification: uv run pytest -q → exit 0 → 3 passed
```

Reload Live UI, install/open the Handoff Memory if needed, then choose **Usage Receipt**.

## 5-minute narration

1. **Problem (30 sec):** “When Alice leaves, Git keeps her code but loses why direct billing state changes are dangerous.”
2. **Publish (45 sec):** “Pluribus extracts locally, removes secrets, and asks Alice to approve a structured handoff—not a transcript.”
3. **Discover/install (45 sec):** “Bob finds the rule by task intent and installs it as an explicit local package.”
4. **Real Codex (90 sec):** run the command; point out the failing baseline, explicit Memory ID, one-file delta, and passing tests.
5. **Receipt (60 sec):** “This is causal proof that Alice's knowledge reached Bob's Codex and preserved the audit trail.”
6. **Close (30 sec):** “Pluribus is continuity infrastructure for engineering teams.”

## Privacy language

Say: **local extraction, automatic secret removal, employee approval, private team publication.**

Do not say: “We upload every Codex conversation” or “we copy an employee's entire brain.”
