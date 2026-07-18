from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


class RepositoryInspectionError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class RepositoryBaseline:
    root: Path
    commit: str
    branch: str
    is_dirty: bool


def _git(path: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(path), *args],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (
        FileNotFoundError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
    ) as error:
        raise RepositoryInspectionError("not a usable Git repository") from error
    return result.stdout.strip()


def inspect_repository(repository_path: str) -> RepositoryBaseline:
    requested = Path(repository_path).expanduser()
    if not requested.is_dir():
        raise RepositoryInspectionError("repository path is not a directory")

    root = Path(_git(requested, "rev-parse", "--show-toplevel")).resolve()
    commit = _git(root, "rev-parse", "HEAD")
    try:
        branch = _git(root, "symbolic-ref", "--quiet", "--short", "HEAD")
    except RepositoryInspectionError:
        branch = "HEAD"
    is_dirty = bool(_git(root, "status", "--porcelain", "--untracked-files=normal"))
    return RepositoryBaseline(
        root=root,
        commit=commit,
        branch=branch,
        is_dirty=is_dirty,
    )
