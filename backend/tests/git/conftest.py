from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


def git(repository: Path, *arguments: str, input_bytes: bytes | None = None) -> bytes:
    return subprocess.run(
        ["git", "-C", str(repository), *arguments],
        input=input_bytes,
        check=True,
        capture_output=True,
    ).stdout


@pytest.fixture
def git_repository(tmp_path: Path) -> Path:
    repository = tmp_path / "repository with spaces"
    repository.mkdir()
    subprocess.run(
        ["git", "init", "-b", "main", str(repository)],
        check=True,
        capture_output=True,
    )
    git(repository, "config", "user.name", "Test User")
    git(repository, "config", "user.email", "test@example.com")
    (repository / "src").mkdir()
    (repository / "tests").mkdir()
    (repository / "protected").mkdir()
    (repository / "src" / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    (repository / "src" / "old_name.py").write_text("OLD = True\n", encoding="utf-8")
    (repository / "tests" / "test_app.py").write_text(
        "def test_value():\n    assert True\n", encoding="utf-8"
    )
    (repository / "protected" / "secret.txt").write_text("secret\n", encoding="utf-8")
    (repository / "delete_me.txt").write_text("delete me\n", encoding="utf-8")
    (repository / "binary.bin").write_bytes(b"\x00\x01before\xff")
    git(repository, "add", "--all")
    git(repository, "commit", "-m", "initial")
    return repository
