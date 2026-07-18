from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import Any

from app.usage.sanitization import sanitize_output
from app.verification.runner import CommandSpec, CommandStatus, run_command

_OUTPUT_LIMIT_BYTES = 16_384


async def record_baseline_failure(
    fixture_root: Path, destination: Path
) -> dict[str, Any]:
    fixture_root = Path(fixture_root).resolve()
    destination = Path(destination)

    with TemporaryDirectory(prefix="pluribus-baseline-") as temporary_directory:
        temporary_root = Path(temporary_directory)
        copied_fixture = temporary_root / "fixture"
        shutil.copytree(
            fixture_root,
            copied_fixture,
            ignore=shutil.ignore_patterns(
                ".venv", ".pytest_cache", "__pycache__", "*.pyc"
            ),
        )
        (copied_fixture / "pyproject.toml").unlink()

        result = await run_command(
            CommandSpec(
                executable=sys.executable,
                args=("-m", "pytest", "-q"),
                cwd=copied_fixture,
                timeout_seconds=30,
                output_limit_bytes=_OUTPUT_LIMIT_BYTES,
                name="pytest-import-mismatch-baseline",
            )
        )
        output = f"{result.stdout}\n{result.stderr}"
        if result.status is not CommandStatus.FAILED or result.exit_code != 2:
            raise RuntimeError("Baseline pytest collection must fail with exit code 2")
        if "import file mismatch" not in output or "test_runner.py" not in output:
            raise RuntimeError("Baseline failure signature was not reproduced")

        excerpt = sanitize_output(
            output, paths=(fixture_root, copied_fixture, temporary_root)
        )
        evidence: dict[str, Any] = {
            "label": "REPLAY — RECORDED EVIDENCE",
            "kind": "pytest_import_file_mismatch_baseline",
            "command": ["pytest", "-q"],
            "exit_code": 2,
            "failure_signature": "import file mismatch",
            "output_excerpt": excerpt,
        }

    payload = json.dumps(evidence, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    temporary_path: Path | None = None
    try:
        with NamedTemporaryFile(
            "w",
            encoding="utf-8",
            newline="\n",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_file.write(payload)
            temporary_path = Path(temporary_file.name)
        os.replace(temporary_path, destination)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

    return evidence


__all__ = ["record_baseline_failure"]
