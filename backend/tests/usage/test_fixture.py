from __future__ import annotations

import asyncio
import shutil
import sys
from pathlib import Path

from app.verification.runner import CommandSpec, CommandStatus, run_command

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_ROOT = REPOSITORY_ROOT / "demo" / "memory-fixture"


def _run_pytest(cwd: Path):
    return asyncio.run(
        run_command(
            CommandSpec(
                executable=sys.executable,
                args=("-m", "pytest", "-q"),
                cwd=cwd,
                timeout_seconds=30,
                output_limit_bytes=16_384,
                name="billing-handoff-fixture",
            )
        )
    )


def _apply_alice_memory(workspace: Path) -> None:
    path = workspace / "billing" / "invoices.py"
    source = path.read_text(encoding="utf-8")
    source = source.replace(
        '    PAID = "paid"\n',
        '    PAID = "paid"\n    CANCELLED = "cancelled"\n',
    )
    source += """


def cancel_invoice(invoice: Invoice, ledger: list[LedgerEvent]) -> None:
    transition_invoice(
        invoice,
        to_status=InvoiceStatus.CANCELLED,
        ledger=ledger,
        reason="customer_request",
    )
"""
    path.write_text(source, encoding="utf-8")


def test_fixture_fails_before_handoff_and_passes_with_alice_memory(
    tmp_path: Path,
) -> None:
    assert FIXTURE_ROOT.is_dir(), "demo/memory-fixture is missing"
    workspace = tmp_path / "billing-service"
    shutil.copytree(FIXTURE_ROOT, workspace, ignore=shutil.ignore_patterns(".venv"))

    failing = _run_pytest(workspace)
    failing_output = f"{failing.stdout}\n{failing.stderr}".lower()
    assert failing.status is CommandStatus.FAILED
    assert "cancel_invoice" in failing_output

    _apply_alice_memory(workspace)
    passing = _run_pytest(workspace)
    assert passing.status is CommandStatus.PASSED
    assert passing.exit_code == 0
    assert "3 passed" in passing.stdout
