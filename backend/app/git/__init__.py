"""Safe Git isolation, artifact, and deterministic integration primitives."""

from app.git.artifacts import ArtifactError, GitArtifact, create_artifact
from app.git.paths import (
    DEFAULT_ALLOWED_GLOBS,
    DEFAULT_PROTECTED_GLOBS,
    PathPolicyError,
    normalize_repository_path,
    validate_changed_paths,
)
from app.git.repository import (
    BaselineChangedError,
    DirtyRepositoryError,
    GitBaseline,
    RepositoryError,
    capture_baseline,
    revalidate_baseline,
)
from app.git.runner import GitCommandError, GitResult, GitRunner
from app.git.workspace import (
    CleanupRefusedError,
    IntegrationError,
    MissionWorkspace,
    WorkspaceError,
)

__all__ = [
    "DEFAULT_ALLOWED_GLOBS",
    "DEFAULT_PROTECTED_GLOBS",
    "ArtifactError",
    "BaselineChangedError",
    "CleanupRefusedError",
    "DirtyRepositoryError",
    "GitArtifact",
    "GitBaseline",
    "GitCommandError",
    "GitResult",
    "GitRunner",
    "IntegrationError",
    "MissionWorkspace",
    "PathPolicyError",
    "RepositoryError",
    "WorkspaceError",
    "capture_baseline",
    "create_artifact",
    "normalize_repository_path",
    "revalidate_baseline",
    "validate_changed_paths",
]
