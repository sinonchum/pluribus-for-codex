from __future__ import annotations

import json
import re
import shutil
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from app.git.artifacts import ArtifactError, GitArtifact, verify_artifact_patch
from app.git.paths import (
    DEFAULT_ALLOWED_GLOBS,
    DEFAULT_PROTECTED_GLOBS,
    PathPolicyError,
    validate_changed_paths,
)
from app.git.repository import GitBaseline, ensure_clean, revalidate_baseline
from app.git.runner import GitCommandError, GitRunner


class WorkspaceError(RuntimeError):
    pass


class IntegrationError(WorkspaceError):
    pass


class CleanupRefusedError(WorkspaceError):
    pass


_MISSION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_MARKER_NAME = ".pluribus-mission-workspace.json"
_INTEGRATION_ORDER = ("tester", "builder")


@dataclass(slots=True)
class MissionWorkspace:
    mission_id: str
    baseline: GitBaseline
    workspace_root: Path
    protected_globs: Sequence[str] = DEFAULT_PROTECTED_GLOBS
    allowed_globs: Mapping[str, Sequence[str]] = field(
        default_factory=lambda: DEFAULT_ALLOWED_GLOBS
    )
    runner: GitRunner = field(default_factory=GitRunner)
    _integrated_roles: list[str] = field(default_factory=list, init=False)
    _integration_head: str | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        if not _MISSION_ID.fullmatch(self.mission_id):
            raise WorkspaceError("mission ID is not safe for branch or path creation")
        self.workspace_root = self.workspace_root.expanduser().resolve()
        repository = self.baseline.root.resolve()
        if (
            self.workspace_root == repository
            or repository in self.workspace_root.parents
        ):
            raise WorkspaceError("workspace root must be outside the source repository")

    @property
    def mission_path(self) -> Path:
        return self.workspace_root / self.mission_id

    @property
    def integration_branch(self) -> str:
        return f"hive/{self.mission_id}/integration"

    @property
    def integration_worktree(self) -> Path:
        return self.mission_path / "integration"

    def branch_for(self, role: str) -> str:
        if role not in _INTEGRATION_ORDER:
            raise WorkspaceError(f"role does not receive a writing worktree: {role}")
        return f"hive/{self.mission_id}/{role}-1"

    def worktree_for(self, role: str) -> Path:
        self.branch_for(role)
        return self.mission_path / f"{role}-1"

    def initialize(self) -> None:
        revalidate_baseline(self.baseline, runner=self.runner, require_clean=True)
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        if self.mission_path.exists():
            raise WorkspaceError("mission workspace already exists")

        branch_paths = [
            (self.integration_branch, self.integration_worktree),
            *(
                (self.branch_for(role), self.worktree_for(role))
                for role in _INTEGRATION_ORDER
            ),
        ]
        for branch, _ in branch_paths:
            exists = self.runner.run(
                self.baseline.root,
                ("show-ref", "--verify", "--quiet", f"refs/heads/{branch}"),
                check=False,
            )
            if exists.returncode == 0:
                raise WorkspaceError(f"mission branch already exists: {branch}")

        self.mission_path.mkdir()
        created: list[tuple[str, Path]] = []
        try:
            for branch, path in branch_paths:
                self.runner.run(
                    self.baseline.root,
                    (
                        "worktree",
                        "add",
                        "--quiet",
                        "-b",
                        branch,
                        str(path),
                        self.baseline.commit,
                    ),
                )
                created.append((branch, path))
            self._write_marker(branch_paths)
            self._integration_head = self.baseline.commit
        except Exception:
            for branch, path in reversed(created):
                self.runner.run(
                    self.baseline.root,
                    ("worktree", "remove", "--force", str(path)),
                    check=False,
                )
                self.runner.run(
                    self.baseline.root,
                    ("branch", "-D", branch),
                    check=False,
                )
            shutil.rmtree(self.mission_path, ignore_errors=True)
            raise

    def _write_marker(self, branch_paths: Sequence[tuple[str, Path]]) -> None:
        marker = {
            "format": 1,
            "mission_id": self.mission_id,
            "repository": str(self.baseline.root.resolve()),
            "workspace_root": str(self.workspace_root),
            "worktrees": [str(path.resolve()) for _, path in branch_paths],
            "branches": [branch for branch, _ in branch_paths],
        }
        (self.mission_path / _MARKER_NAME).write_text(
            json.dumps(marker, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def integrate(self, artifact: GitArtifact) -> str:
        if not (self.mission_path / _MARKER_NAME).is_file():
            raise IntegrationError("mission workspace marker is missing")
        revalidate_baseline(self.baseline, runner=self.runner, require_clean=True)
        expected_role = (
            _INTEGRATION_ORDER[len(self._integrated_roles)]
            if len(self._integrated_roles) < len(_INTEGRATION_ORDER)
            else None
        )
        if artifact.role != expected_role:
            raise IntegrationError(
                "artifact integration order requires "
                f"{expected_role}, got {artifact.role}"
            )
        if artifact.base_commit != self.baseline.commit:
            raise IntegrationError("artifact was created from the wrong baseline")
        try:
            artifact.verify()
            verify_artifact_patch(
                artifact,
                self.baseline.root,
                runner=self.runner,
            )
        except ArtifactError as error:
            raise IntegrationError(str(error)) from error
        try:
            validate_changed_paths(
                artifact.changed_paths,
                role=artifact.role,
                protected_globs=self.protected_globs,
                allowed_globs=self.allowed_globs,
            )
        except PathPolicyError as error:
            raise IntegrationError(str(error)) from error

        self._validate_integration_worktree()
        if artifact.patch:
            check = self.runner.run(
                self.integration_worktree,
                ("apply", "--check", "--index", "--binary", "-"),
                input_bytes=artifact.patch,
                check=False,
            )
            if check.returncode != 0:
                raise IntegrationError("artifact conflicts with the integration tree")
            try:
                self.runner.run(
                    self.integration_worktree,
                    ("apply", "--index", "--binary", "-"),
                    input_bytes=artifact.patch,
                )
                commit_date = self.runner.text(
                    self.baseline.root,
                    ("show", "-s", "--format=%cI", self.baseline.commit),
                )
                self.runner.run(
                    self.integration_worktree,
                    (
                        "-c",
                        "user.name=Pluribus",
                        "-c",
                        "user.email=pluribus@localhost",
                        "commit",
                        "--quiet",
                        "-m",
                        f"chore(pluribus): integrate {artifact.role} artifact",
                    ),
                    environment={
                        "GIT_AUTHOR_DATE": commit_date,
                        "GIT_COMMITTER_DATE": commit_date,
                    },
                )
            except GitCommandError as error:
                self._restore_integration_head()
                raise IntegrationError("artifact application failed") from error

        self._integration_head = self.runner.text(
            self.integration_worktree, ("rev-parse", "HEAD")
        )
        self._integrated_roles.append(artifact.role)
        return self._integration_head

    def _validate_integration_worktree(self) -> None:
        branch = self.runner.text(
            self.integration_worktree,
            ("symbolic-ref", "--quiet", "--short", "HEAD"),
        )
        head = self.runner.text(self.integration_worktree, ("rev-parse", "HEAD"))
        if branch != self.integration_branch or head != self._integration_head:
            raise IntegrationError(
                "integration worktree branch or HEAD changed unexpectedly"
            )
        try:
            ensure_clean(self.integration_worktree, runner=self.runner)
        except Exception as error:
            raise IntegrationError("integration worktree is dirty") from error

    def _restore_integration_head(self) -> None:
        if self._integration_head is None:
            return
        self.runner.run(
            self.integration_worktree,
            ("reset", "--hard", "--quiet", self._integration_head),
            check=False,
        )
        self.runner.run(
            self.integration_worktree,
            ("clean", "-fd", "--quiet"),
            check=False,
        )

    def cleanup(self) -> None:
        marker_path = self.mission_path / _MARKER_NAME
        marker = self._validated_marker(marker_path)
        worktrees = [Path(value) for value in marker["worktrees"]]
        branches = list(marker["branches"])

        for worktree in reversed(worktrees):
            self.runner.run(
                self.baseline.root,
                ("worktree", "remove", "--force", str(worktree)),
                check=False,
            )
        for branch in reversed(branches):
            self.runner.run(
                self.baseline.root,
                ("branch", "-D", branch),
                check=False,
            )
        shutil.rmtree(self.mission_path)
        self.runner.run(self.baseline.root, ("worktree", "prune"), check=False)

    def _validated_marker(self, marker_path: Path) -> dict[str, object]:
        mission_resolved = self.mission_path.resolve()
        if (
            not self.mission_path.is_dir()
            or self.mission_path.is_symlink()
            or mission_resolved.parent != self.workspace_root
            or not marker_path.is_file()
            or marker_path.is_symlink()
        ):
            raise CleanupRefusedError(
                "cleanup target is not a contained mission workspace"
            )
        try:
            marker = json.loads(marker_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise CleanupRefusedError("mission workspace marker is invalid") from error

        expected = {
            "format": 1,
            "mission_id": self.mission_id,
            "repository": str(self.baseline.root.resolve()),
            "workspace_root": str(self.workspace_root),
        }
        if any(marker.get(key) != value for key, value in expected.items()):
            raise CleanupRefusedError(
                "mission workspace marker does not match cleanup target"
            )
        worktrees = marker.get("worktrees")
        branches = marker.get("branches")
        if (
            not isinstance(worktrees, list)
            or not isinstance(branches, list)
            or not all(isinstance(value, str) for value in worktrees)
            or not all(isinstance(value, str) for value in branches)
        ):
            raise CleanupRefusedError("mission workspace ownership list is invalid")
        expected_worktrees = {
            self.integration_worktree.resolve(),
            *(self.worktree_for(role).resolve() for role in _INTEGRATION_ORDER),
        }
        actual_worktrees = {
            Path(value).resolve() for value in worktrees if isinstance(value, str)
        }
        expected_branches = {
            self.integration_branch,
            *(self.branch_for(role) for role in _INTEGRATION_ORDER),
        }
        if actual_worktrees != expected_worktrees or set(branches) != expected_branches:
            raise CleanupRefusedError("mission workspace ownership list was modified")
        if any(mission_resolved not in path.parents for path in actual_worktrees):
            raise CleanupRefusedError("owned worktree escapes mission workspace")
        return marker
