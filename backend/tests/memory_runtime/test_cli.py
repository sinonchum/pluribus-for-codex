from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    repository = Path(__file__).resolve().parents[3]
    return subprocess.run(
        [sys.executable, str(repository / "tools/pluribus_memory.py"), *args],
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
    )


def test_cli_install_list_and_match(tmp_path: Path, capsule: dict[str, object]) -> None:
    capsule_path = tmp_path / "memory.json"
    capsule_path.write_text(json.dumps(capsule), encoding="utf-8")

    installed = run_cli(
        "install",
        "--capsule",
        str(capsule_path),
        "--root",
        str(tmp_path),
    )
    listed = run_cli("list", "--root", str(tmp_path))
    matched = run_cli(
        "match",
        "--text",
        "pytest import file mismatch in duplicate test_runner.py",
        "--root",
        str(tmp_path),
    )

    assert installed.returncode == 0, installed.stderr
    assert json.loads(installed.stdout)["memory_id"] == "mem_pytest_importlib_v1"
    assert listed.returncode == 0, listed.stderr
    assert json.loads(listed.stdout)[0]["slug"] == "fix-pytest-module-collisions"
    assert matched.returncode == 0, matched.stderr
    match_body = json.loads(matched.stdout)
    assert match_body["matches"][0]["memory_id"] == "mem_pytest_importlib_v1"
    assert "--import-mode=importlib" in match_body["context_packet"]
