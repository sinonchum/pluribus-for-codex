from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
RUNNER = REPOSITORY_ROOT / "demo" / "run-handoff-live.py"


def test_terminal_handoff_runner_uses_codex_and_emits_receipt(
    tmp_path: Path,
) -> None:
    fake_codex = tmp_path / "fake-codex"
    fake_codex.write_text(
        """#!/usr/bin/env python3
import json
import pathlib
import sys
args = sys.argv[1:]
workspace = pathlib.Path(args[args.index("-C") + 1])
output = pathlib.Path(args[args.index("-o") + 1])
assert "mem_billing_audit_handoff_v1" in sys.stdin.read()
path = workspace / "billing" / "invoices.py"
source = path.read_text().replace('    PAID = "paid"\\n', '    PAID = "paid"\\n    CANCELLED = "cancelled"\\n')
source += '''\\n\\ndef cancel_invoice(invoice: Invoice, ledger: list[LedgerEvent]) -> None:\n    transition_invoice(invoice, to_status=InvoiceStatus.CANCELLED, ledger=ledger, reason="customer_request")\n'''
path.write_text(source)
output.write_text(json.dumps({
  "memory_id": "mem_billing_audit_handoff_v1",
  "matched_trigger": "add a new invoice status",
  "injected_into_codex": True,
  "codex_reported_use": True,
  "effect": "Preserved Alice's billing audit rule.",
  "changed_files": ["billing/invoices.py"]
}))
""",
        encoding="utf-8",
    )
    os.chmod(fake_codex, 0o755)
    env = {**os.environ, "CODEX_EXECUTABLE": str(fake_codex)}

    result = subprocess.run(
        [sys.executable, str(RUNNER)],
        cwd=REPOSITORY_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    assert "BASELINE — KNOWLEDGE GAP" in result.stdout
    assert "LIVE — KNOWLEDGE HANDOFF" in result.stdout
    payload = json.loads(result.stdout.split("LIVE — KNOWLEDGE HANDOFF\n", 1)[1])
    assert payload["memory_id"] == "mem_billing_audit_handoff_v1"
    assert payload["consumer"] == "Bob · Successor Engineer"
    assert payload["changed_files"] == ["billing/invoices.py"]
    assert payload["verification"]["exit_code"] == 0
    assert "VIRTUAL_ENV" not in payload["verification"]["output_excerpt"]
