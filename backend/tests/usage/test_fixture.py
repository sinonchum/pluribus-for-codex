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
                name="memory-fixture",
            )
        )
    )


def test_fixture_reproduces_baseline_failure_and_passes_with_memory_method(
    tmp_path: Path,
) -> None:
    assert FIXTURE_ROOT.is_dir(), "demo/memory-fixture is missing"
    baseline = tmp_path / "baseline"
    shutil.copytree(FIXTURE_ROOT, baseline)
    (baseline / "pyproject.toml").unlink()

    failing = _run_pytest(baseline)
    failing_output = f"{failing.stdout}\n{failing.stderr}".lower()
    assert failing.status is CommandStatus.FAILED
    assert "import file mismatch" in failing_output
    assert "test_runner.py" in failing_output

    passing = _run_pytest(FIXTURE_ROOT)
    assert passing.status is CommandStatus.PASSED
    assert passing.exit_code == 0
