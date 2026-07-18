from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.git.runner import GitCommandError, GitRunner


class RepositoryError(RuntimeError):
    """The repository cannot safely participate in a mission."""


class DirtyRepositoryError(RepositoryError):
    pass


class BaselineChangedError(RepositoryError):
    pass


@dataclass(frozen=True, slots=True)
class GitBaseline:
    root: Path
    commit: str
    branch: str | None


def capture_baseline(
    repository: str | Path,
    *,
    runner: GitRunner | None = None,
    require_clean: bool = True,
) -> GitBaseline:
    git = runner or GitRunner()
    requested = Path(repository).expanduser()
    if not requested.is_dir():
        raise RepositoryError("repository path is not a directory")
    try:
        root = Path(git.text(requested, ("rev-parse", "--show-toplevel"))).resolve()
        commit = git.text(root, ("rev-parse", "--verify", "HEAD^{commit}"))
        branch_result = git.run(
            root,
            ("symbolic-ref", "--quiet", "--short", "HEAD"),
            check=False,
        )
        branch = branch_result.text() if branch_result.returncode == 0 else None
    except GitCommandError as error:
        raise RepositoryError("not a usable Git repository with a commit") from error

    baseline = GitBaseline(root=root, commit=commit, branch=branch)
    if require_clean:
        ensure_clean(root, runner=git)
    return baseline


def status_porcelain(repository: Path, *, runner: GitRunner | None = None) -> bytes:
    git = runner or GitRunner()
    return git.run(
        repository,
        ("status", "--porcelain=v1", "-z", "--untracked-files=all"),
    ).stdout


def ensure_clean(repository: Path, *, runner: GitRunner | None = None) -> None:
    if status_porcelain(repository, runner=runner):
        raise DirtyRepositoryError("repository contains tracked or untracked changes")


def revalidate_baseline(
    baseline: GitBaseline,
    *,
    runner: GitRunner | None = None,
    require_clean: bool = True,
) -> None:
    git = runner or GitRunner()
    try:
        current_root = Path(
            git.text(baseline.root, ("rev-parse", "--show-toplevel"))
        ).resolve()
        current_commit = git.text(baseline.root, ("rev-parse", "HEAD"))
    except GitCommandError as error:
        raise BaselineChangedError(
            "repository baseline is no longer available"
        ) from error
    if current_root != baseline.root or current_commit != baseline.commit:
        raise BaselineChangedError("repository HEAD changed after baseline capture")
    if require_clean:
        ensure_clean(baseline.root, runner=git)
