from __future__ import annotations

import json
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from app.git import (
    BaselineChangedError,
    CleanupRefusedError,
    DirtyRepositoryError,
    GitArtifact,
    IntegrationError,
    MissionWorkspace,
    capture_baseline,
    create_artifact,
)
from app.git.artifacts import artifact_sha256


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _workspace(repository: Path, tmp_path: Path, mission: str) -> MissionWorkspace:
    return MissionWorkspace(
        mission_id=mission,
        baseline=capture_baseline(repository),
        workspace_root=tmp_path / "mission worktrees",
        protected_globs=(".git/**", ".env", "protected/**"),
    )


def test_worktrees_integrate_tester_then_builder_without_mutating_source(
    git_repository: Path, tmp_path: Path
) -> None:
    source_head = _git(git_repository, "rev-parse", "HEAD")
    source_branch = _git(git_repository, "branch", "--show-current")
    workspace = _workspace(git_repository, tmp_path, "mission-positive")
    workspace.initialize()
    try:
        tester_tree = workspace.worktree_for("tester")
        builder_tree = workspace.worktree_for("builder")
        (tester_tree / "tests" / "test added.py").write_text(
            "def test_added():\n    assert True\n", encoding="utf-8"
        )
        (builder_tree / "src" / "app.py").write_text("VALUE = 42\n", encoding="utf-8")
        (builder_tree / "generated.bin").write_bytes(b"\x00\xffgenerated")
        tester = create_artifact(
            tester_tree, role="tester", base_commit=workspace.baseline.commit
        )
        builder = create_artifact(
            builder_tree, role="builder", base_commit=workspace.baseline.commit
        )

        tester_head = workspace.integrate(tester)
        final_head = workspace.integrate(builder)

        assert tester_head != source_head
        assert final_head != tester_head
        assert (workspace.integration_worktree / "tests" / "test added.py").is_file()
        assert (workspace.integration_worktree / "src" / "app.py").read_text(
            encoding="utf-8"
        ) == "VALUE = 42\n"
        assert (workspace.integration_worktree / "generated.bin").read_bytes() == (
            b"\x00\xffgenerated"
        )
        assert _git(git_repository, "rev-parse", "HEAD") == source_head
        assert _git(git_repository, "branch", "--show-current") == source_branch
        assert _git(git_repository, "status", "--porcelain") == ""
    finally:
        workspace.cleanup()

    assert not workspace.mission_path.exists()
    branches = _git(git_repository, "branch", "--format=%(refname:short)").splitlines()
    assert not any(
        branch.startswith(f"hive/{workspace.mission_id}/") for branch in branches
    )


def test_integration_rejects_order_wrong_base_scope_and_protected_edits(
    git_repository: Path, tmp_path: Path
) -> None:
    workspace = _workspace(git_repository, tmp_path, "mission-policy")
    workspace.initialize()
    try:
        tester_tree = workspace.worktree_for("tester")
        builder_tree = workspace.worktree_for("builder")
        (tester_tree / "src" / "illegal.py").write_text("bad\n", encoding="utf-8")
        outside = create_artifact(
            tester_tree, role="tester", base_commit=workspace.baseline.commit
        )
        falsified_paths = ("tests/fake.py",)
        falsified = replace(
            outside,
            changed_paths=falsified_paths,
            sha256=artifact_sha256(
                outside.role,
                outside.base_commit,
                outside.patch,
                falsified_paths,
            ),
        )
        with pytest.raises(IntegrationError, match="metadata does not match"):
            workspace.integrate(falsified)
        with pytest.raises(IntegrationError, match="outside tester"):
            workspace.integrate(outside)

        (builder_tree / "src" / "app.py").write_text("VALUE = 3\n", encoding="utf-8")
        builder = create_artifact(
            builder_tree, role="builder", base_commit=workspace.baseline.commit
        )
        with pytest.raises(IntegrationError, match="requires tester"):
            workspace.integrate(builder)

        empty_tester = GitArtifact(
            role="tester",
            base_commit=workspace.baseline.commit,
            changed_paths=(),
            patch=b"",
            sha256=artifact_sha256("tester", workspace.baseline.commit, b""),
        )
        wrong_base = replace(
            empty_tester,
            base_commit="0" * 40,
            sha256=artifact_sha256("tester", "0" * 40, b""),
        )
        with pytest.raises(IntegrationError, match="wrong baseline"):
            workspace.integrate(wrong_base)

        (builder_tree / "protected" / "secret.txt").write_text(
            "exposed\n", encoding="utf-8"
        )
        protected = create_artifact(
            builder_tree, role="builder", base_commit=workspace.baseline.commit
        )
        protected_as_tester = GitArtifact(
            role="tester",
            base_commit=protected.base_commit,
            changed_paths=protected.changed_paths,
            patch=protected.patch,
            sha256=artifact_sha256(
                "tester",
                protected.base_commit,
                protected.patch,
                protected.changed_paths,
            ),
        )
        with pytest.raises(IntegrationError, match="protected"):
            workspace.integrate(protected_as_tester)

        assert _git(workspace.integration_worktree, "rev-parse", "HEAD") == (
            workspace.baseline.commit
        )
        assert _git(workspace.integration_worktree, "status", "--porcelain") == ""
    finally:
        workspace.cleanup()


def test_conflicting_second_artifact_is_rejected_without_partial_mutation(
    git_repository: Path, tmp_path: Path
) -> None:
    workspace = _workspace(git_repository, tmp_path, "mission-conflict")
    workspace.initialize()
    try:
        tester_path = workspace.worktree_for("tester") / "tests" / "test_app.py"
        builder_path = workspace.worktree_for("builder") / "tests" / "test_app.py"
        tester_path.write_text("TESTER = True\n", encoding="utf-8")
        builder_path.write_text("BUILDER = True\n", encoding="utf-8")
        tester = create_artifact(
            workspace.worktree_for("tester"),
            role="tester",
            base_commit=workspace.baseline.commit,
        )
        builder = create_artifact(
            workspace.worktree_for("builder"),
            role="builder",
            base_commit=workspace.baseline.commit,
        )
        workspace.integrate(tester)
        head_before = _git(workspace.integration_worktree, "rev-parse", "HEAD")

        with pytest.raises(IntegrationError, match="conflicts"):
            workspace.integrate(builder)

        assert _git(workspace.integration_worktree, "rev-parse", "HEAD") == head_before
        assert _git(workspace.integration_worktree, "status", "--porcelain") == ""
        assert tester_path.name == "test_app.py"
    finally:
        workspace.cleanup()


def test_initialize_revalidates_clean_baseline_and_supports_detached_head(
    git_repository: Path, tmp_path: Path
) -> None:
    dirty_workspace = _workspace(git_repository, tmp_path, "mission-dirty")
    (git_repository / "dirty.txt").write_text("dirty", encoding="utf-8")
    with pytest.raises(DirtyRepositoryError):
        dirty_workspace.initialize()
    (git_repository / "dirty.txt").unlink()

    changed_workspace = _workspace(git_repository, tmp_path, "mission-changed")
    (git_repository / "commit.txt").write_text("commit", encoding="utf-8")
    _git(git_repository, "add", "commit.txt")
    _git(git_repository, "commit", "-m", "move baseline")
    with pytest.raises(BaselineChangedError):
        changed_workspace.initialize()

    _git(git_repository, "checkout", "--detach", "--quiet")
    detached = _workspace(git_repository, tmp_path, "mission-detached")
    detached.initialize()
    try:
        assert detached.baseline.branch is None
        assert _git(git_repository, "branch", "--show-current") == ""
    finally:
        detached.cleanup()


def test_cleanup_refuses_missing_or_tampered_ownership_marker(
    git_repository: Path, tmp_path: Path
) -> None:
    workspace = _workspace(git_repository, tmp_path, "mission-cleanup")
    workspace.initialize()
    marker_path = workspace.mission_path / ".pluribus-mission-workspace.json"
    original = marker_path.read_text(encoding="utf-8")
    try:
        marker_path.unlink()
        with pytest.raises(CleanupRefusedError):
            workspace.cleanup()
        marker_path.write_text(original, encoding="utf-8")

        marker = json.loads(original)
        marker["worktrees"].append(str(tmp_path / "outside"))
        marker_path.write_text(json.dumps(marker), encoding="utf-8")
        with pytest.raises(CleanupRefusedError):
            workspace.cleanup()
    finally:
        marker_path.write_text(original, encoding="utf-8")
        workspace.cleanup()
