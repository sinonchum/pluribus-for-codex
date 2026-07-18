from __future__ import annotations

import os
from pathlib import Path

from app.memory_runtime import install_memory
from app.registry.seed import SEEDED_MEMORY
from app.usage.codex_cli_adapter import run_codex_cli_usage


def test_codex_cli_adapter_injects_installed_memory_and_reports_real_change(
    tmp_path: Path,
) -> None:
    installed_root = tmp_path / "consumer"
    installed_root.mkdir()
    install_memory(installed_root, SEEDED_MEMORY.model_dump(mode="json"))

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "tests_alpha").mkdir()
    (workspace / "tests_beta").mkdir()
    (workspace / "tests_alpha" / "test_runner.py").write_text(
        "def test_alpha(): assert True\n", encoding="utf-8"
    )
    (workspace / "tests_beta" / "test_runner.py").write_text(
        "def test_beta(): assert True\n", encoding="utf-8"
    )

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
assert "mem_pytest_importlib_v1" in prompt
assert "--import-mode=importlib" in prompt
(workspace / "pyproject.toml").write_text(
    '[project]\\nname = "live-fixture"\\nversion = "0.1.0"\\n'
    '[tool.pytest.ini_options]\\naddopts = "--import-mode=importlib"\\n',
    encoding="utf-8",
)
output.write_text(json.dumps({
    "memory_id": "mem_pytest_importlib_v1",
    "matched_trigger": "import file mismatch",
    "injected_into_codex": True,
    "codex_reported_use": True,
    "effect": "Configured pytest importlib collection mode.",
    "changed_files": ["pyproject.toml"],
}), encoding="utf-8")
""",
        encoding="utf-8",
    )
    os.chmod(fake_codex, 0o755)

    result = run_codex_cli_usage(
        installed_root,
        workspace,
        codex_executable=str(fake_codex),
    )

    assert result["memory_id"] == "mem_pytest_importlib_v1"
    assert result["codex_reported_use"] is True
    assert result["changed_files"] == ["pyproject.toml"]
    assert "--import-mode=importlib" in (workspace / "pyproject.toml").read_text(
        encoding="utf-8"
    )
