from __future__ import annotations

import subprocess
from pathlib import Path

from app.git import capture_baseline, create_artifact


def _status(repository: Path) -> bytes:
    return subprocess.run(
        ["git", "-C", str(repository), "status", "--porcelain=v1", "-z"],
        check=True,
        capture_output=True,
    ).stdout


def test_artifact_is_stable_binary_safe_and_includes_all_git_changes(
    git_repository: Path,
) -> None:
    baseline = capture_baseline(git_repository)
    before_status = _status(git_repository)
    (git_repository / "src" / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    (git_repository / "delete_me.txt").unlink()
    (git_repository / "src" / "old_name.py").rename(
        git_repository / "src" / "new name.py"
    )
    (git_repository / "binary.bin").write_bytes(b"\x00\xffafter\x10")
    (git_repository / "untracked binary.dat").write_bytes(b"\x00new\xfe")
    dirty_status = _status(git_repository)

    first = create_artifact(git_repository, role="builder", base_commit=baseline.commit)
    second = create_artifact(
        git_repository, role="builder", base_commit=baseline.commit
    )

    assert before_status == b""
    assert _status(git_repository) == dirty_status
    assert first == second
    assert len(first.sha256) == 64
    assert set(first.changed_paths) == {
        "binary.bin",
        "delete_me.txt",
        "src/app.py",
        "src/new name.py",
        "src/old_name.py",
        "untracked binary.dat",
    }
    assert b"GIT binary patch" in first.patch
    first.verify()
