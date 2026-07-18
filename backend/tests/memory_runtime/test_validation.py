from __future__ import annotations

import pytest

from app.memory_runtime.validation import validate_capsule


def test_runtime_validates_exact_frozen_capsule(capsule: dict[str, object]) -> None:
    validated = validate_capsule(capsule)

    assert validated["summary"] == capsule["summary"]
    assert validated["stars"] == 128
    assert validated["installs"] == 1402
    assert validated["fork_of"] is None


def test_runtime_rejects_unknown_capsule_fields(capsule: dict[str, object]) -> None:
    capsule["unexpected"] = "field"

    with pytest.raises(ValueError, match="fields"):
        validate_capsule(capsule)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", "/Users/alice/private-token"),
        ("version", "secret=abcdef123456"),
        ("created_at", "not-a-timestamp"),
        ("status", "trusted"),
    ],
)
def test_runtime_rejects_unsafe_or_malformed_identity_fields(
    capsule: dict[str, object], field: str, value: str
) -> None:
    capsule[field] = value

    with pytest.raises(ValueError):
        validate_capsule(capsule)


def test_verified_capsule_requires_successful_evidence(
    capsule: dict[str, object],
) -> None:
    capsule["verification"] = {
        "command": ["pytest", "-q"],
        "exit_code": 1,
        "passed": 0,
        "evidence_excerpt": "1 failed",
    }

    with pytest.raises(ValueError, match="verified"):
        validate_capsule(capsule)
