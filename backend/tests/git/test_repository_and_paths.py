from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from app.git import (
    BaselineChangedError,
    DirtyRepositoryError,
    GitRunner,
    PathPolicyError,
    capture_baseline,
    normalize_repository_path,
    revalidate_baseline,
    validate_changed_paths,
)


def test_runner_uses_argument_array_and_supports_paths_with_spaces(
    git_repository: Path,
) -> None:
    runner = GitRunner()

    result = runner.run(git_repository, ("rev-parse", "--show-toplevel"))

    assert Path(result.text()).resolve() == git_repository.resolve()
    with pytest.raises(TypeError):
        runner.run(git_repository, "status")  # type: ignore[arg-type]


def test_capture_baseline_rejects_tracked_and_untracked_dirty_states(
    git_repository: Path,
) -> None:
    (git_repository / "untracked file.txt").write_text("new", encoding="utf-8")
    with pytest.raises(DirtyRepositoryError):
        capture_baseline(git_repository)

    (git_repository / "untracked file.txt").unlink()
    (git_repository / "src" / "app.py").write_text("changed\n", encoding="utf-8")
    with pytest.raises(DirtyRepositoryError):
        capture_baseline(git_repository)


def test_detached_head_baseline_is_supported(git_repository: Path) -> None:
    subprocess.run(
        ["git", "-C", str(git_repository), "checkout", "--detach", "--quiet"],
        check=True,
    )

    baseline = capture_baseline(git_repository)

    assert baseline.branch is None
    revalidate_baseline(baseline)


def test_start_revalidation_rejects_new_commit_and_new_dirt(
    git_repository: Path,
) -> None:
    baseline = capture_baseline(git_repository)
    (git_repository / "later.txt").write_text("later\n", encoding="utf-8")
    with pytest.raises(DirtyRepositoryError):
        revalidate_baseline(baseline)

    subprocess.run(["git", "-C", str(git_repository), "add", "later.txt"], check=True)
    subprocess.run(
        ["git", "-C", str(git_repository), "commit", "-m", "later", "--quiet"],
        check=True,
    )
    with pytest.raises(BaselineChangedError):
        revalidate_baseline(baseline)


@pytest.mark.parametrize(
    "unsafe",
    ["../outside", "a/../../outside", "/absolute", "C:/absolute", ".git/config", ""],
)
def test_repository_path_normalization_rejects_unsafe_paths(unsafe: str) -> None:
    with pytest.raises(PathPolicyError):
        normalize_repository_path(unsafe)


def test_repository_path_normalization_and_static_role_policy() -> None:
    assert normalize_repository_path(r"tests\unit\test value.py") == (
        "tests/unit/test value.py"
    )
    assert validate_changed_paths([r"tests\unit\test value.py"], role="tester") == (
        "tests/unit/test value.py",
    )

    with pytest.raises(PathPolicyError, match="outside tester"):
        validate_changed_paths(["src/app.py"], role="tester")
    with pytest.raises(PathPolicyError, match="protected"):
        validate_changed_paths(
            ["src/auth/token.py"],
            role="builder",
            protected_globs=("src/auth/**",),
        )
