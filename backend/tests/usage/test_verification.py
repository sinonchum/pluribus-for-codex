from __future__ import annotations

import asyncio
import shutil
import sys
from pathlib import Path

from app.usage.verification import run_coordinator_verification

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_ROOT = REPOSITORY_ROOT / "demo" / "memory-fixture"


def _completed_handoff(tmp_path: Path) -> Path:
    workspace = tmp_path / "billing-service"
    shutil.copytree(FIXTURE_ROOT, workspace, ignore=shutil.ignore_patterns(".venv"))
    path = workspace / "billing" / "invoices.py"
    source = path.read_text(encoding="utf-8").replace(
        '    PAID = "paid"\n',
        '    PAID = "paid"\n    CANCELLED = "cancelled"\n',
    )
    source += """


def cancel_invoice(invoice: Invoice, ledger: list[LedgerEvent]) -> None:
    transition_invoice(invoice, to_status=InvoiceStatus.CANCELLED, ledger=ledger, reason="customer_request")
"""
    path.write_text(source, encoding="utf-8")
    return workspace


def test_coordinator_verification_returns_sanitized_passing_proof(
    tmp_path: Path,
) -> None:
    workspace = _completed_handoff(tmp_path)
    proof = asyncio.run(
        run_coordinator_verification(workspace, command=("pytest", "-q"))
    )

    assert proof.command == ("pytest", "-q")
    assert proof.exit_code == 0
    assert "3 passed" in proof.output_excerpt
    assert str(workspace) not in proof.output_excerpt


def test_coordinator_verification_redacts_secret_values(monkeypatch) -> None:
    secret = "sk-" + "per...3456"
    monkeypatch.setenv("PLURIBUS_TEST_SECRET", secret)

    proof = asyncio.run(
        run_coordinator_verification(
            FIXTURE_ROOT,
            command=(
                sys.executable,
                "-c",
                f"print('API_KEY={secret}'); print('Bearer {secret}')",
            ),
        )
    )

    assert secret not in proof.output_excerpt
    assert "<redacted>" in proof.output_excerpt
