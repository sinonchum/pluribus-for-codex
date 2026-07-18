from __future__ import annotations

import copy
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
RUNNER = REPOSITORY_ROOT / "demo" / "run-memory-demo.py"
FIXTURE_ROOT = REPOSITORY_ROOT / "demo" / "memory-fixture"
SNAPSHOT_PATH = REPOSITORY_ROOT / "demo" / "memory-evidence" / "demo_snapshot.json"


def _load_runner_module():
    spec = importlib.util.spec_from_file_location("person3_demo_runner", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_replay_mode_is_explicit_and_emits_frozen_receipt() -> None:
    result = subprocess.run(
        [sys.executable, str(RUNNER), "--mode", "replay"],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    assert lines[0] == "REPLAY — RECORDED EVIDENCE"
    snapshot = json.loads("\n".join(lines[1:]))
    receipt = snapshot["latest_receipt"]
    assert receipt["memory_id"] == "mem_billing_audit_handoff_v1"
    assert receipt["matched_trigger"] == "add a new invoice status"
    assert receipt["injected_into_codex"] is True
    assert receipt["codex_reported_use"] is True
    assert receipt["changed_files"] == ["billing/invoices.py"]
    assert receipt["verification"]["command"] == ["uv", "run", "pytest", "-q"]
    assert receipt["verification"]["exit_code"] == 0


def test_replay_validation_rejects_blank_required_proof() -> None:
    runner = _load_runner_module()
    snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))

    for field_path in (
        ("latest_receipt", "matched_trigger"),
        ("latest_receipt", "verification", "output_excerpt"),
    ):
        invalid = copy.deepcopy(snapshot)
        target = invalid
        for key in field_path[:-1]:
            target = target[key]
        target[field_path[-1]] = "   "
        with pytest.raises(ValueError, match="required proof"):
            runner._validate_snapshot(invalid)


def test_live_mode_runs_direct_adapter_and_emits_verified_receipt(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    shutil.copytree(FIXTURE_ROOT, workspace, ignore=shutil.ignore_patterns(".venv"))
    installed_root = tmp_path / "installed"
    installed_root.mkdir()
    adapter_script = tmp_path / "codex_adapter.py"
    adapter_script.write_text(
        """from __future__ import annotations
import json
import sys
from pathlib import Path

installed_root = Path(sys.argv[1])
workspace = Path(sys.argv[2])
assert installed_root.is_dir()
path = workspace / "billing" / "invoices.py"
source = path.read_text(encoding="utf-8").replace(
    '    PAID = "paid"\\n',
    '    PAID = "paid"\\n    CANCELLED = "cancelled"\\n',
)
source += '''\\n\\ndef cancel_invoice(invoice: Invoice, ledger: list[LedgerEvent]) -> None:\n    transition_invoice(invoice, to_status=InvoiceStatus.CANCELLED, ledger=ledger, reason="customer_request")\n'''
path.write_text(source, encoding="utf-8")
print(json.dumps({
    "memory_id": "mem_billing_audit_handoff_v1",
    "matched_trigger": "add a new invoice status",
    "injected_into_codex": True,
    "codex_reported_use": True,
    "effect": "Preserved the append-only billing audit trail.",
    "changed_files": ["billing/invoices.py"],
}))
""",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--mode",
            "live",
            "--installed-memory-root",
            str(installed_root),
            "--workspace",
            str(workspace),
            "--adapter-command",
            sys.executable,
            str(adapter_script),
        ],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    assert lines[0] == "LIVE — KNOWLEDGE HANDOFF"
    receipt = json.loads("\n".join(lines[1:]))
    assert receipt["memory_id"] == "mem_billing_audit_handoff_v1"
    assert receipt["changed_files"] == ["billing/invoices.py"]
    assert receipt["verification"]["exit_code"] == 0
