from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.usage import UsageProof, VerificationProof, build_usage_receipt


def test_build_usage_receipt_matches_frozen_contract() -> None:
    receipt = build_usage_receipt(
        UsageProof(
            receipt_id="use_demo_001",
            memory_id="mem_pytest_importlib_v1",
            consumer="dev_bob",
            matched_trigger="import file mismatch",
            injected_memory_id="mem_pytest_importlib_v1",
            codex_reported_use=True,
            effect="Configured pytest importlib collection mode.",
            changed_files=("pyproject.toml",),
            verification=VerificationProof(
                command=("pytest", "-q"),
                exit_code=0,
                output_excerpt="4 passed",
            ),
            created_at=datetime(2026, 7, 18, 10, 8, tzinfo=UTC),
        )
    )

    assert receipt.to_dict() == {
        "id": "use_demo_001",
        "memory_id": "mem_pytest_importlib_v1",
        "consumer": "dev_bob",
        "matched_trigger": "import file mismatch",
        "injected_into_codex": True,
        "codex_reported_use": True,
        "effect": "Configured pytest importlib collection mode.",
        "changed_files": ["pyproject.toml"],
        "verification": {
            "command": ["pytest", "-q"],
            "exit_code": 0,
            "output_excerpt": "4 passed",
        },
        "created_at": "2026-07-18T10:08:00Z",
    }


def test_build_usage_receipt_rejects_unconfirmed_codex_use() -> None:
    proof = UsageProof(
        receipt_id="use_demo_001",
        memory_id="mem_pytest_importlib_v1",
        consumer="dev_bob",
        matched_trigger="import file mismatch",
        injected_memory_id="mem_pytest_importlib_v1",
        codex_reported_use=False,
        effect="Configured pytest importlib collection mode.",
        changed_files=("pyproject.toml",),
        verification=VerificationProof(
            command=("pytest", "-q"), exit_code=0, output_excerpt="4 passed"
        ),
        created_at=datetime(2026, 7, 18, 10, 8, tzinfo=UTC),
    )

    with pytest.raises(ValueError, match="Codex-reported use is required"):
        build_usage_receipt(proof)


def test_build_usage_receipt_rejects_failed_coordinator_verification() -> None:
    proof = UsageProof(
        receipt_id="use_demo_001",
        memory_id="mem_pytest_importlib_v1",
        consumer="dev_bob",
        matched_trigger="import file mismatch",
        injected_memory_id="mem_pytest_importlib_v1",
        codex_reported_use=True,
        effect="Configured pytest importlib collection mode.",
        changed_files=("pyproject.toml",),
        verification=VerificationProof(
            command=("pytest", "-q"), exit_code=1, output_excerpt="1 failed"
        ),
        created_at=datetime(2026, 7, 18, 10, 8, tzinfo=UTC),
    )

    with pytest.raises(ValueError, match="Coordinator verification must pass"):
        build_usage_receipt(proof)
