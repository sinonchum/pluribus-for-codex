from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    app = create_app(database_path=tmp_path / "registry.db")
    with TestClient(app) as test_client:
        yield test_client


def published_capsule(**overrides: object) -> dict[str, object]:
    capsule: dict[str, object] = {
        "id": "mem_custom_v1",
        "slug": "custom-debugging-memory",
        "title": "Custom debugging memory",
        "summary": "A reusable debugging technique.",
        "problem": "A difficult bug needs a repeatable method.",
        "triggers": ["difficult bug"],
        "steps": ["Reproduce the bug.", "Apply the method.", "Verify the suite."],
        "tags": ["debugging", "codex"],
        "author": {"id": "dev_carol", "display_name": "Carol Diaz"},
        "version": "1.0.0",
        "compatibility": ["python>=3.11"],
        "status": "verified",
        "verification": {
            "command": ["pytest", "-q"],
            "exit_code": 0,
            "passed": 2,
            "evidence_excerpt": "2 passed",
        },
        "stars": 0,
        "installs": 0,
        "fork_of": None,
        "created_at": "2026-07-18T11:00:00Z",
    }
    capsule.update(overrides)
    return capsule


def test_seeded_memory_is_searchable_by_query_tag_and_trigger(
    client: TestClient,
) -> None:
    by_query = client.get("/api/memories", params={"query": "pytest"})
    by_tag = client.get("/api/memories", params={"tag": "debugging"})
    by_trigger = client.get(
        "/api/memories", params={"query": "test_runner.py collision"}
    )

    assert by_query.status_code == 200
    assert [memory["id"] for memory in by_query.json()] == ["mem_pytest_importlib_v1"]
    assert [memory["id"] for memory in by_tag.json()] == ["mem_pytest_importlib_v1"]
    assert [memory["id"] for memory in by_trigger.json()] == ["mem_pytest_importlib_v1"]


def test_search_treats_sql_wildcards_as_literal_text(client: TestClient) -> None:
    payload = published_capsule(
        id="mem_percent_v1",
        slug="percent-debugging-memory",
        summary="A 100% reproducible debugging technique.",
    )
    assert client.post("/api/memories", json=payload).status_code == 201

    percent_results = client.get("/api/memories", params={"query": "%"}).json()
    underscore_results = client.get("/api/memories", params={"query": "_"}).json()

    assert [memory["id"] for memory in percent_results] == ["mem_percent_v1"]
    assert [memory["id"] for memory in underscore_results] == [
        "mem_pytest_importlib_v1"
    ]


def test_seed_is_idempotent_across_application_restarts(tmp_path: Path) -> None:
    database_path = tmp_path / "persistent-registry.db"

    with TestClient(create_app(database_path=database_path)) as first_client:
        first = first_client.get("/api/memories").json()
    with TestClient(create_app(database_path=database_path)) as second_client:
        second = second_client.get("/api/memories").json()

    assert len(first) == 1
    assert second == first


def test_get_memory_returns_full_frozen_capsule(client: TestClient) -> None:
    response = client.get("/api/memories/fix-pytest-module-collisions")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "mem_pytest_importlib_v1"
    assert body["verification"] == {
        "command": ["pytest", "-q"],
        "exit_code": 0,
        "passed": 4,
        "evidence_excerpt": "4 passed",
    }
    assert body["fork_of"] is None


def test_create_memory_persists_and_duplicate_slug_conflicts(
    client: TestClient,
) -> None:
    payload = published_capsule()

    created = client.post("/api/memories", json=payload)
    duplicate = client.post(
        "/api/memories",
        json=published_capsule(id="mem_different_v1"),
    )

    assert created.status_code == 201
    assert created.json() == payload
    assert client.get("/api/memories/custom-debugging-memory").json() == payload
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["code"] == "memory_already_exists"


def test_star_increments_once_for_fixed_demo_user(client: TestClient) -> None:
    path = "/api/memories/fix-pytest-module-collisions/star"

    first = client.post(path)
    second = client.post(path)

    assert first.status_code == 200
    assert first.json() == {
        "memory_id": "mem_pytest_importlib_v1",
        "slug": "fix-pytest-module-collisions",
        "starred": True,
        "stars": 129,
    }
    assert second.json() == first.json()
    assert (
        client.get("/api/memories/fix-pytest-module-collisions").json()["stars"] == 129
    )


def test_install_records_once_and_lists_installed_memory(client: TestClient) -> None:
    path = "/api/memories/fix-pytest-module-collisions/install"

    first = client.post(path)
    second = client.post(path)
    installed = client.get("/api/installed")

    assert first.status_code == 200
    assert first.json()["memory_id"] == "mem_pytest_importlib_v1"
    assert first.json()["consumer"] == "dev_bob"
    assert second.json() == first.json()
    assert installed.status_code == 200
    assert [memory["id"] for memory in installed.json()] == ["mem_pytest_importlib_v1"]
    assert installed.json()[0]["installs"] == 1403


def test_demo_snapshot_matches_frozen_aggregate_shape(client: TestClient) -> None:
    client.post("/api/memories/fix-pytest-module-collisions/install")

    response = client.get("/api/demo/snapshot")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "featured_memories",
        "installed_memories",
        "latest_receipt",
        "stats",
    }
    assert body["featured_memories"][0]["id"] == "mem_pytest_importlib_v1"
    assert body["installed_memories"][0]["id"] == "mem_pytest_importlib_v1"
    assert body["latest_receipt"] is None
    assert body["stats"] == {
        "published": 1,
        "verified": 1,
        "installs": 1403,
        "successful_uses": 0,
    }


def test_unknown_memory_routes_return_not_found(client: TestClient) -> None:
    assert client.get("/api/memories/missing").status_code == 404
    assert client.post("/api/memories/missing/star").status_code == 404
    assert client.post("/api/memories/missing/install").status_code == 404
