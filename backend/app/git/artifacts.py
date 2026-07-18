from __future__ import annotations

import hashlib
import hmac
import os
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from app.git.paths import normalize_repository_path
from app.git.runner import GitRunner


class ArtifactError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class GitArtifact:
    role: str
    base_commit: str
    changed_paths: tuple[str, ...]
    patch: bytes
    sha256: str

    def verify(self) -> None:
        expected = artifact_sha256(
            self.role, self.base_commit, self.patch, self.changed_paths
        )
        if not hmac.compare_digest(expected, self.sha256):
            raise ArtifactError("artifact SHA-256 does not match its contents")


def artifact_sha256(
    role: str,
    base_commit: str,
    patch: bytes,
    changed_paths: Sequence[str] = (),
) -> str:
    digest = hashlib.sha256()
    digest.update(b"pluribus-git-artifact-v1\0")
    digest.update(role.encode("utf-8"))
    digest.update(b"\0")
    digest.update(base_commit.encode("ascii"))
    digest.update(b"\0")
    for path in changed_paths:
        digest.update(normalize_repository_path(path).encode("utf-8"))
        digest.update(b"\0")
    digest.update(patch)
    return digest.hexdigest()


def _changed_paths(raw: bytes) -> tuple[str, ...]:
    fields = raw.split(b"\0")
    paths: set[str] = set()
    index = 0
    while index < len(fields) and fields[index]:
        status = fields[index].decode("ascii")
        index += 1
        path_count = 2 if status.startswith(("R", "C")) else 1
        for _ in range(path_count):
            if index >= len(fields) or not fields[index]:
                raise ArtifactError("Git returned malformed changed-path data")
            decoded = fields[index].decode("utf-8", errors="surrogateescape")
            paths.add(normalize_repository_path(decoded))
            index += 1
    return tuple(sorted(paths))


def create_artifact(
    worktree: Path,
    *,
    role: str,
    base_commit: str,
    runner: GitRunner | None = None,
) -> GitArtifact:
    """Create a binary patch with a temporary index, without changing the worktree."""
    git = runner or GitRunner()
    worktree = worktree.resolve()
    current_base = git.text(worktree, ("merge-base", "HEAD", base_commit))
    if current_base != base_commit:
        raise ArtifactError("worktree is not based on the requested baseline")

    descriptor, index_name = tempfile.mkstemp(prefix="pluribus-index-")
    os.close(descriptor)
    index_path = Path(index_name)
    index_path.unlink()
    environment = {"GIT_INDEX_FILE": str(index_path)}
    try:
        git.run(worktree, ("read-tree", base_commit), environment=environment)
        git.run(worktree, ("add", "--all", "--", "."), environment=environment)
        tree = git.text(worktree, ("write-tree",), environment=environment)
        patch = git.run(
            worktree,
            (
                "diff",
                "--binary",
                "--full-index",
                "--find-renames",
                base_commit,
                tree,
                "--",
            ),
        ).stdout
        names = git.run(
            worktree,
            ("diff", "--name-status", "-z", "--find-renames", base_commit, tree, "--"),
        ).stdout
    finally:
        index_path.unlink(missing_ok=True)

    changed_paths = _changed_paths(names)
    return GitArtifact(
        role=role,
        base_commit=base_commit,
        changed_paths=changed_paths,
        patch=patch,
        sha256=artifact_sha256(role, base_commit, patch, changed_paths),
    )


def verify_artifact_patch(
    artifact: GitArtifact,
    repository: Path,
    *,
    runner: GitRunner | None = None,
) -> None:
    """Verify that artifact metadata exactly describes its Git binary patch."""
    git = runner or GitRunner()
    if not artifact.patch:
        if artifact.changed_paths:
            raise ArtifactError("an empty artifact cannot declare changed paths")
        return

    descriptor, index_name = tempfile.mkstemp(prefix="pluribus-verify-index-")
    os.close(descriptor)
    index_path = Path(index_name)
    index_path.unlink()
    environment = {"GIT_INDEX_FILE": str(index_path)}
    try:
        git.run(
            repository,
            ("read-tree", artifact.base_commit),
            environment=environment,
        )
        applied = git.run(
            repository,
            ("apply", "--cached", "--binary", "-"),
            input_bytes=artifact.patch,
            environment=environment,
            check=False,
        )
        if applied.returncode != 0:
            raise ArtifactError("artifact patch is invalid for its baseline")
        tree = git.text(repository, ("write-tree",), environment=environment)
        names = git.run(
            repository,
            (
                "diff",
                "--name-status",
                "-z",
                "--find-renames",
                artifact.base_commit,
                tree,
                "--",
            ),
        ).stdout
    finally:
        index_path.unlink(missing_ok=True)

    if _changed_paths(names) != artifact.changed_paths:
        raise ArtifactError("artifact changed-path metadata does not match its patch")
