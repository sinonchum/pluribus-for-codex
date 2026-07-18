from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import datetime
from typing import Any

_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*\Z")
_MEMORY_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,127}\Z")
_VERSION = re.compile(r"^\d+\.\d+\.\d+\Z")
_CAPSULE_FIELDS = {
    "id",
    "slug",
    "title",
    "summary",
    "problem",
    "triggers",
    "steps",
    "tags",
    "author",
    "version",
    "compatibility",
    "status",
    "verification",
    "stars",
    "installs",
    "fork_of",
    "created_at",
}
_AUTHOR_FIELDS = {"id", "display_name"}
_VERIFICATION_FIELDS = {"command", "exit_code", "passed", "evidence_excerpt"}


def validate_slug(slug: str) -> str:
    if not _SLUG.fullmatch(slug):
        raise ValueError(
            "slug must contain lowercase letters, digits, and hyphens only"
        )
    return slug


def validate_memory_id(memory_id: str, field: str = "id") -> str:
    if not _MEMORY_ID.fullmatch(memory_id):
        raise ValueError(
            f"{field} must contain lowercase letters, digits, underscores, or hyphens"
        )
    return memory_id


def validate_version(version: str) -> str:
    if not _VERSION.fullmatch(version):
        raise ValueError("version must use semantic numeric form, for example 1.0.0")
    return version


def validate_timestamp(value: str, field: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{field} must be an ISO-8601 timestamp") from error
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone")
    return value


def _exact_fields(data: Mapping[str, Any], expected: set[str], name: str) -> None:
    actual = set(data)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        raise ValueError(
            f"{name} fields mismatch; missing={missing}, unknown={unknown}"
        )


def _text(data: Mapping[str, Any], key: str, *, maximum: int = 4000) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    if len(value) > maximum:
        raise ValueError(f"{key} exceeds {maximum} characters")
    return value.strip()


def _text_list(
    data: Mapping[str, Any],
    key: str,
    *,
    maximum_items: int = 64,
    maximum_length: int = 4000,
) -> list[str]:
    value = data.get(key)
    if not isinstance(value, list) or not value or len(value) > maximum_items:
        raise ValueError(f"{key} must be a non-empty bounded array")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise ValueError(f"{key} must contain non-empty strings")
    if any(len(item) > maximum_length for item in value):
        raise ValueError(f"{key} entries are too long")
    return [item.strip() for item in value]


def _non_negative_integer(data: Mapping[str, Any], key: str) -> int:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{key} must be a non-negative integer")
    return value


def validate_capsule(capsule: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and copy the exact frozen Memory Capsule contract."""

    _exact_fields(capsule, _CAPSULE_FIELDS, "Memory Capsule")
    memory_id = validate_memory_id(_text(capsule, "id", maximum=128))
    slug = validate_slug(_text(capsule, "slug", maximum=128))
    version = validate_version(_text(capsule, "version", maximum=64))
    status = _text(capsule, "status", maximum=32)
    if status not in {"draft", "verified"}:
        raise ValueError("status must be draft or verified")
    created_at = validate_timestamp(
        _text(capsule, "created_at", maximum=64), "created_at"
    )

    author = capsule.get("author")
    if not isinstance(author, Mapping):
        raise ValueError("author must be an object")
    _exact_fields(author, _AUTHOR_FIELDS, "author")
    validated_author = {
        "id": validate_memory_id(_text(author, "id", maximum=128), "author.id"),
        "display_name": _text(author, "display_name", maximum=256),
    }

    verification = capsule.get("verification")
    if not isinstance(verification, Mapping):
        raise ValueError("verification must be an object")
    _exact_fields(verification, _VERIFICATION_FIELDS, "verification")
    command = verification.get("command")
    if not isinstance(command, list) or not command or len(command) > 64:
        raise ValueError(
            "verification.command must be an executable and argument array"
        )
    if not all(isinstance(part, str) and part.strip() for part in command):
        raise ValueError("verification.command parts must be non-empty strings")
    if any(len(part) > 512 for part in command):
        raise ValueError("verification.command parts are too long")
    exit_code = verification.get("exit_code")
    passed = verification.get("passed")
    if isinstance(exit_code, bool) or not isinstance(exit_code, int):
        raise ValueError("verification.exit_code must be an integer")
    if isinstance(passed, bool) or not isinstance(passed, int) or passed < 0:
        raise ValueError("verification.passed must be a non-negative integer")
    if status == "verified" and (exit_code != 0 or passed < 1):
        raise ValueError("verified memories require successful verification evidence")
    validated_verification = {
        "command": [part.strip() for part in command],
        "exit_code": exit_code,
        "passed": passed,
        "evidence_excerpt": _text(verification, "evidence_excerpt", maximum=4000),
    }

    fork_of = capsule.get("fork_of")
    if fork_of is not None:
        if not isinstance(fork_of, str):
            raise ValueError("fork_of must be a memory id or null")
        fork_of = validate_memory_id(fork_of, "fork_of")

    return {
        "id": memory_id,
        "slug": slug,
        "title": _text(capsule, "title", maximum=256),
        "summary": _text(capsule, "summary", maximum=1000),
        "problem": _text(capsule, "problem", maximum=4000),
        "triggers": _text_list(
            capsule, "triggers", maximum_items=32, maximum_length=500
        ),
        "steps": _text_list(capsule, "steps", maximum_items=64, maximum_length=4000),
        "tags": _text_list(capsule, "tags", maximum_items=32, maximum_length=128),
        "author": validated_author,
        "version": version,
        "compatibility": _text_list(
            capsule, "compatibility", maximum_items=32, maximum_length=500
        ),
        "status": status,
        "verification": validated_verification,
        "stars": _non_negative_integer(capsule, "stars"),
        "installs": _non_negative_integer(capsule, "installs"),
        "fork_of": fork_of,
        "created_at": created_at,
    }
