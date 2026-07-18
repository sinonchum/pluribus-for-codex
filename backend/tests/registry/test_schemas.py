from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.memories import MemoryCapsule


@pytest.fixture
def frozen_capsule() -> dict[str, object]:
    return {
        "id": "mem_pytest_importlib_v1",
        "slug": "fix-pytest-module-collisions",
        "title": "Fix duplicate pytest module collisions",
        "summary": "Use pytest importlib mode when duplicate test module names collide.",
        "problem": "Pytest raises import file mismatch during collection.",
        "triggers": [
            "import file mismatch",
            "duplicate test module",
            "test_runner.py collision",
        ],
        "steps": [
            "Confirm the collision is caused by duplicate test module basenames.",
            "Set pytest addopts to --import-mode=importlib.",
            "Run the full suite and preserve the output as evidence.",
        ],
        "tags": ["python", "pytest", "debugging", "codex"],
        "author": {"id": "dev_alice", "display_name": "Alice Chen"},
        "version": "1.0.0",
        "compatibility": ["python>=3.11", "pytest>=8"],
        "status": "verified",
        "verification": {
            "command": ["pytest", "-q"],
            "exit_code": 0,
            "passed": 4,
            "evidence_excerpt": "4 passed",
        },
        "stars": 128,
        "installs": 1402,
        "fork_of": None,
        "created_at": "2026-07-18T10:00:00Z",
    }


def test_memory_capsule_accepts_and_round_trips_frozen_contract(
    frozen_capsule: dict[str, object],
) -> None:
    capsule = MemoryCapsule.model_validate(frozen_capsule)

    assert capsule.model_dump(mode="json") == frozen_capsule
    assert capsule.verification.command == ["pytest", "-q"]


def test_memory_capsule_rejects_unknown_contract_fields(
    frozen_capsule: dict[str, object],
) -> None:
    frozen_capsule["invented_field"] = True

    with pytest.raises(ValidationError):
        MemoryCapsule.model_validate(frozen_capsule)


def test_memory_capsule_rejects_shell_verification_command(
    frozen_capsule: dict[str, object],
) -> None:
    frozen_capsule["verification"] = {
        "command": "pytest -q",
        "exit_code": 0,
        "passed": 4,
        "evidence_excerpt": "4 passed",
    }

    with pytest.raises(ValidationError):
        MemoryCapsule.model_validate(frozen_capsule)


def test_verified_memory_requires_successful_verification(
    frozen_capsule: dict[str, object],
) -> None:
    frozen_capsule["verification"] = {
        "command": ["pytest", "-q"],
        "exit_code": 1,
        "passed": 0,
        "evidence_excerpt": "1 failed",
    }

    with pytest.raises(ValidationError):
        MemoryCapsule.model_validate(frozen_capsule)


def test_memory_capsule_requires_timezone_aware_created_at(
    frozen_capsule: dict[str, object],
) -> None:
    frozen_capsule["created_at"] = "not-a-timestamp"

    with pytest.raises(ValidationError):
        MemoryCapsule.model_validate(frozen_capsule)


def test_memory_capsule_bounds_each_list_entry(
    frozen_capsule: dict[str, object],
) -> None:
    frozen_capsule["triggers"] = ["x" * 501]

    with pytest.raises(ValidationError):
        MemoryCapsule.model_validate(frozen_capsule)
