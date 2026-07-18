from __future__ import annotations

import fnmatch
import re
from collections.abc import Iterable, Mapping, Sequence
from pathlib import PurePosixPath


class PathPolicyError(ValueError):
    pass


DEFAULT_ALLOWED_GLOBS: Mapping[str, tuple[str, ...]] = {
    "builder": ("**",),
    "tester": (
        "tests/**",
        "test/**",
        "**/tests/**",
        "**/test/**",
        "**/test_*.py",
        "**/*_test.py",
        "**/*.test.js",
        "**/*.test.ts",
        "**/*.spec.js",
        "**/*.spec.ts",
    ),
}

DEFAULT_PROTECTED_GLOBS: tuple[str, ...] = (
    ".git",
    ".git/**",
    ".env",
    ".env.*",
)

_DRIVE = re.compile(r"^[A-Za-z]:")


def normalize_repository_path(path: str) -> str:
    if not isinstance(path, str) or not path:
        raise PathPolicyError("repository-relative path must be a non-empty string")
    if "\x00" in path:
        raise PathPolicyError("repository-relative path contains NUL")
    candidate = path.replace("\\", "/")
    if candidate.startswith("/") or _DRIVE.match(candidate):
        raise PathPolicyError("absolute paths are not allowed")

    parts: list[str] = []
    for part in candidate.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            raise PathPolicyError("path traversal is not allowed")
        parts.append(part)
    if not parts:
        raise PathPolicyError("path does not name a repository file")
    normalized = PurePosixPath(*parts).as_posix()
    if normalized == ".git" or normalized.startswith(".git/"):
        raise PathPolicyError("Git metadata paths are not allowed")
    return normalized


def _matches(path: str, pattern: str) -> bool:
    normalized_pattern = pattern.replace("\\", "/").lstrip("./")
    if not normalized_pattern:
        return False
    if normalized_pattern == "**":
        return True
    if normalized_pattern.endswith("/**"):
        directory = normalized_pattern[:-3].rstrip("/")
        if path == directory or path.startswith(f"{directory}/"):
            return True
    return fnmatch.fnmatchcase(path, normalized_pattern) or PurePosixPath(path).match(
        normalized_pattern
    )


def validate_changed_paths(
    paths: Iterable[str],
    *,
    role: str,
    protected_globs: Sequence[str] = DEFAULT_PROTECTED_GLOBS,
    allowed_globs: Mapping[str, Sequence[str]] = DEFAULT_ALLOWED_GLOBS,
) -> tuple[str, ...]:
    try:
        role_globs = allowed_globs[role]
    except KeyError as error:
        raise PathPolicyError(f"role has no write policy: {role}") from error

    normalized = tuple(sorted({normalize_repository_path(path) for path in paths}))
    protected = [
        path
        for path in normalized
        if any(_matches(path, pattern) for pattern in protected_globs)
    ]
    if protected:
        raise PathPolicyError(f"protected paths changed: {', '.join(protected)}")

    outside = [
        path
        for path in normalized
        if not any(_matches(path, pattern) for pattern in role_globs)
    ]
    if outside:
        raise PathPolicyError(f"paths outside {role} write scope: {', '.join(outside)}")
    return normalized
