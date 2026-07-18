from __future__ import annotations

from app.db import Database
from app.schemas.memories import MemoryCapsule

SEEDED_MEMORY = MemoryCapsule.model_validate(
    {
        "id": "mem_billing_audit_handoff_v1",
        "slug": "preserve-billing-audit-trail",
        "title": "Preserve billing audit trail during invoice transitions",
        "summary": "Alice Chen's four-year Billing Platform handoff: route every invoice state change through the audited transition primitive.",
        "problem": "Direct invoice status assignments bypass Northstar's append-only financial ledger, erasing the audit evidence required by Finance and Compliance.",
        "triggers": [
            "add a new invoice status",
            "cancel an invoice",
            "change billing state",
            "update invoice status",
        ],
        "steps": [
            "Never assign invoice.status directly in Billing Service workflows.",
            "Add the new status to InvoiceStatus, then route the operation through transition_invoice().",
            "Record the ledger event before persisting the new invoice state.",
            "Run uv run pytest -q and preserve the billing audit-trail output as evidence.",
        ],
        "tags": ["billing", "audit", "handoff", "codex"],
        "author": {"id": "dev_alice", "display_name": "Alice Chen · Billing, 4 years"},
        "version": "1.0.0",
        "compatibility": ["northstar-billing>=0.1", "python>=3.11"],
        "status": "verified",
        "verification": {
            "command": ["uv", "run", "pytest", "-q"],
            "exit_code": 0,
            "passed": 3,
            "evidence_excerpt": "3 passed",
        },
        "stars": 47,
        "installs": 18,
        "fork_of": None,
        "created_at": "2026-07-18T10:00:00Z",
    }
)


def seed_registry(database: Database) -> None:
    database.create_memory(
        SEEDED_MEMORY.model_dump(mode="json"),
        ignore_existing=True,
    )
