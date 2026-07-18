from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    with TestClient(create_app(database_path=tmp_path / "registry.db")) as test_client:
        yield test_client


def receipt_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": "use_live_cli_001",
        "memory_id": "mem_pytest_importlib_v1",
        "consumer": "demo_consumer",
        "matched_trigger": "import file mismatch",
        "injected_into_codex": True,
        "codex_reported_use": True,
        "effect": "Configured pytest importlib mode with the installed memory.",
        "changed_files": ["pyproject.toml"],
        "verification": {
            "command": ["pytest", "-q"],
            "exit_code": 0,
            "output_excerpt": "2 passed",
        },
        "created_at": "2026-07-18T13:43:29Z",
    }
    payload.update(overrides)
    return payload


def test_cli_receipt_is_persisted_retrievable_and_exposed_in_snapshot(
    client: TestClient,
) -> None:
    payload = receipt_payload()

    created = client.post("/api/usage-receipts", json=payload)
    fetched = client.get(f"/api/usage-receipts/{payload['id']}")
    snapshot = client.get("/api/demo/snapshot")

    assert created.status_code == 201
    assert created.json() == payload
    assert fetched.status_code == 200
    assert fetched.json() == payload
    assert snapshot.json()["latest_receipt"] == payload
    assert snapshot.json()["stats"]["successful_uses"] == 1


def test_cli_receipt_rejects_unknown_memory_and_duplicate_id(
    client: TestClient,
) -> None:
    payload = receipt_payload()

    assert client.post("/api/usage-receipts", json=payload).status_code == 201
    duplicate = client.post("/api/usage-receipts", json=payload)
    unknown = client.post(
        "/api/usage-receipts",
        json=receipt_payload(id="use_unknown", memory_id="mem_missing"),
    )

    assert duplicate.status_code == 409
    assert unknown.status_code == 404
