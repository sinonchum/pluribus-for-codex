from __future__ import annotations

import os
import shutil
from pathlib import Path

from app.memory_runtime import install_memory
from app.registry.seed import SEEDED_MEMORY
from app.usage.codex_cli_adapter import run_codex_cli_usage

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_ROOT = REPOSITORY_ROOT / "demo" / "memory-fixture"


def test_codex_cli_adapter_injects_alice_handoff_and_reports_billing_change(
    tmp_path: Path,
) -> None:
    installed_root = tmp_path / "consumer"
    installed_root.mkdir()
    install_memory(installed_root, SEEDED_MEMORY.model_dump(mode="json"))
    workspace = tmp_path / "workspace"
    shutil.copytree(FIXTURE_ROOT, workspace, ignore=shutil.ignore_patterns(".venv"))

    fake_codex = tmp_path / "fake-codex"
    fake_codex.write_text(
        """#!/usr/bin/env python3
import json
import pathlib
import sys

args = sys.argv[1:]
assert args[0] == "exec"
assert "--sandbox" in args and args[args.index("--sandbox") + 1] == "workspace-write"
assert "--dangerously-bypass-approvals-and-sandbox" not in args
workspace = pathlib.Path(args[args.index("-C") + 1])
output = pathlib.Path(args[args.index("-o") + 1])
prompt = sys.stdin.read()
assert "mem_billing_audit_handoff_v1" in prompt
assert "transition_invoice" in prompt
path = workspace / "billing" / "invoices.py"
source = path.read_text().replace(
    '    PAID = "paid"\\n',
    '    PAID = "paid"\\n    CANCELLED = "cancelled"\\n',
)
source += '''\\n\\ndef cancel_invoice(invoice: Invoice, ledger: list[LedgerEvent]) -> None:\n    transition_invoice(invoice, to_status=InvoiceStatus.CANCELLED, ledger=ledger, reason="customer_request")\n'''
path.write_text(source)
output.write_text(json.dumps({
    "memory_id": "mem_billing_audit_handoff_v1",
    "matched_trigger": "add a new invoice status",
    "injected_into_codex": True,
    "codex_reported_use": True,
    "effect": "Preserved the append-only billing audit trail while adding cancellation.",
    "changed_files": ["billing/invoices.py"],
}))
""",
        encoding="utf-8",
    )
    os.chmod(fake_codex, 0o755)

    result = run_codex_cli_usage(
        installed_root,
        workspace,
        codex_executable=str(fake_codex),
    )

    assert result["memory_id"] == "mem_billing_audit_handoff_v1"
    assert result["codex_reported_use"] is True
    assert result["changed_files"] == ["billing/invoices.py"]
    source = (workspace / "billing" / "invoices.py").read_text(encoding="utf-8")
    assert "CANCELLED" in source
    assert "transition_invoice(" in source
