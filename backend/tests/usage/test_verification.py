from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from app.usage.verification import run_coordinator_verification

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_ROOT = REPOSITORY_ROOT / "demo" / "memory-fixture"


def test_coordinator_verification_returns_sanitized_passing_proof() -> None:
    proof = asyncio.run(
        run_coordinator_verification(FIXTURE_ROOT, command=("pytest", "-q"))
    )

    assert proof.command == ("pytest", "-q")
    assert proof.exit_code == 0
    assert "2 passed" in proof.output_excerpt
    assert str(FIXTURE_ROOT) not in proof.output_excerpt


def test_coordinator_verification_redacts_secret_values(monkeypatch) -> None:
    secret = "sk-person3-secret-value-123456"
    monkeypatch.setenv("PLURIBUS_TEST_SECRET", secret)

    proof = asyncio.run(
        run_coordinator_verification(
            FIXTURE_ROOT,
            command=(
                sys.executable,
                "-c",
                f"print('API_KEY={secret}'); print('Bearer {secret}')",
            ),
        )
    )

    assert secret not in proof.output_excerpt
    assert "<redacted>" in proof.output_excerpt
