from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.usage.evidence import record_baseline_failure

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_ROOT = REPOSITORY_ROOT / "demo" / "memory-fixture"


def test_record_baseline_failure_runs_pytest_and_sanitizes_evidence(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "baseline_failure.json"

    evidence = asyncio.run(record_baseline_failure(FIXTURE_ROOT, destination))

    assert evidence["label"] == "REPLAY — RECORDED EVIDENCE"
    assert evidence["kind"] == "pytest_import_file_mismatch_baseline"
    assert evidence["command"] == ["pytest", "-q"]
    assert evidence["exit_code"] == 2
    assert evidence["failure_signature"] == "import file mismatch"
    assert "import file mismatch" in evidence["output_excerpt"].lower()
    assert "test_runner.py" in evidence["output_excerpt"]
    assert str(FIXTURE_ROOT) not in evidence["output_excerpt"]
    assert str(tmp_path) not in evidence["output_excerpt"]
    assert json.loads(destination.read_text(encoding="utf-8")) == evidence
