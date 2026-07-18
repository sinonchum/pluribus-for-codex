from __future__ import annotations

import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


class RecordingMissionController:
    def __init__(self) -> None:
        self.started: list[str] = []
        self.stopped: list[str] = []

    async def start(self, mission_id: str) -> dict[str, str]:
        self.started.append(mission_id)
        return {"mission_id": mission_id, "status": "starting"}

    async def stop(self, mission_id: str) -> None:
        self.stopped.append(mission_id)


@pytest.fixture
def clean_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "demo-repo"
    repo.mkdir()
    subprocess.run(
        ["git", "init", "-b", "main", str(repo)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "tests@example.com"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "Test User"],
        check=True,
    )
    (repo / "README.md").write_text("# Demo\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "README.md"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "initial"],
        check=True,
        capture_output=True,
    )
    return repo


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    app = create_app(database_path=tmp_path / "pluribus.db")
    with TestClient(app) as test_client:
        yield test_client


def mission_payload(repo: Path, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "repository_path": str(repo),
        "objective": "Add a detailed health endpoint with tests.",
        "agent_count": 4,
        "max_concurrency": 2,
        "allow_dirty_repository": False,
        "protected_paths": [".env", ".git/**", "src/auth/**"],
        "verification_commands": [
            {"executable": "pytest", "args": ["-q"], "timeout_seconds": 120}
        ],
    }
    payload.update(overrides)
    return payload


def test_health_endpoint_reports_ready(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_local_frontend_cors_preflight_is_allowed(client: TestClient) -> None:
    response = client.options(
        "/api/missions",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"


def test_create_and_get_mission_persists_repository_baseline(
    client: TestClient, clean_repo: Path
) -> None:
    expected_commit = subprocess.run(
        ["git", "-C", str(clean_repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    created = client.post("/api/missions", json=mission_payload(clean_repo))

    assert created.status_code == 201
    body = created.json()
    assert body["id"].startswith("mission_")
    assert body["repository_path"] == str(clean_repo.resolve())
    assert body["objective"] == "Add a detailed health endpoint with tests."
    assert body["starting_commit"] == expected_commit
    assert body["starting_branch"] == "main"
    assert body["was_dirty"] is False
    assert body["integration_branch"].endswith("/integration")
    assert body["status"] == "created"
    assert body["agent_count"] == 4
    assert body["max_concurrency"] == 2

    fetched = client.get(f"/api/missions/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == body


def test_create_mission_rejects_non_git_directory(
    client: TestClient, tmp_path: Path
) -> None:
    directory = tmp_path / "not-git"
    directory.mkdir()

    response = client.post("/api/missions", json=mission_payload(directory))

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "not_a_git_repository"


def test_create_mission_rejects_dirty_repository_by_default(
    client: TestClient, clean_repo: Path
) -> None:
    (clean_repo / "uncommitted.txt").write_text("dirty", encoding="utf-8")

    response = client.post("/api/missions", json=mission_payload(clean_repo))

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "dirty_repository"


def test_create_mission_records_dirty_state_when_explicitly_allowed(
    client: TestClient, clean_repo: Path
) -> None:
    (clean_repo / "uncommitted.txt").write_text("dirty", encoding="utf-8")

    response = client.post(
        "/api/missions",
        json=mission_payload(clean_repo, allow_dirty_repository=True),
    )

    assert response.status_code == 201
    assert response.json()["was_dirty"] is True


def test_create_mission_enforces_scope_frozen_worker_limits(
    client: TestClient, clean_repo: Path
) -> None:
    wrong_agents = client.post(
        "/api/missions", json=mission_payload(clean_repo, agent_count=3)
    )
    excessive_concurrency = client.post(
        "/api/missions", json=mission_payload(clean_repo, max_concurrency=3)
    )

    assert wrong_agents.status_code == 422
    assert excessive_concurrency.status_code == 422


def test_create_mission_creates_four_specialized_agents(
    client: TestClient, clean_repo: Path
) -> None:
    mission = client.post("/api/missions", json=mission_payload(clean_repo)).json()

    agents = [
        client.get(f"/api/missions/{mission['id']}/agents/{role}_1")
        for role in ("scout", "builder", "tester", "reviewer")
    ]

    assert all(response.status_code == 200 for response in agents)
    assert [response.json()["role"] for response in agents] == [
        "scout",
        "builder",
        "tester",
        "reviewer",
    ]
    assert all(response.json()["status"] == "pending" for response in agents)


def test_unknown_resources_return_not_found(client: TestClient) -> None:
    assert client.get("/api/missions/missing").status_code == 404
    assert client.get("/api/missions/missing/agents/scout_1").status_code == 404
    assert client.get("/api/missions/missing/knowledge").status_code == 404
    assert client.get("/api/missions/missing/report").status_code == 404


def test_start_mission_delegates_to_injected_controller(
    tmp_path: Path, clean_repo: Path
) -> None:
    controller = RecordingMissionController()
    app = create_app(
        database_path=tmp_path / "controlled.db",
        mission_controller=controller,
    )
    with TestClient(app) as controlled_client:
        mission = controlled_client.post(
            "/api/missions", json=mission_payload(clean_repo)
        ).json()

        response = controlled_client.post(f"/api/missions/{mission['id']}/start")

    assert response.status_code == 200
    assert response.json() == {"mission_id": mission["id"], "status": "starting"}
    assert controller.started == [mission["id"]]


def test_start_mission_fails_explicitly_without_controller(
    client: TestClient, clean_repo: Path
) -> None:
    mission = client.post("/api/missions", json=mission_payload(clean_repo)).json()

    response = client.post(f"/api/missions/{mission['id']}/start")

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "mission_controller_unavailable"


def test_stop_mission_changes_status_and_persists_event(
    client: TestClient, clean_repo: Path
) -> None:
    mission = client.post("/api/missions", json=mission_payload(clean_repo)).json()

    stopped = client.post(f"/api/missions/{mission['id']}/stop")

    assert stopped.status_code == 200
    assert stopped.json()["status"] == "stopped"
    events = client.get(
        f"/api/missions/{mission['id']}/events", params={"follow": "false"}
    )
    assert events.status_code == 200
    assert events.headers["content-type"].startswith("text/event-stream")
    assert "event: mission.created" in events.text
    assert "event: mission.stopped" in events.text


def test_knowledge_and_report_endpoints_return_inspectable_empty_state(
    client: TestClient, clean_repo: Path
) -> None:
    mission = client.post("/api/missions", json=mission_payload(clean_repo)).json()

    knowledge = client.get(f"/api/missions/{mission['id']}/knowledge")
    report = client.get(f"/api/missions/{mission['id']}/report")

    assert knowledge.status_code == 200
    assert knowledge.json() == []
    assert report.status_code == 200
    assert report.json()["mission"]["id"] == mission["id"]
    assert len(report.json()["agents"]) == 4
    assert report.json()["knowledge_patches"] == []
    assert report.json()["events"][0]["event_type"] == "mission.created"


def test_database_survives_application_restart(
    tmp_path: Path, clean_repo: Path
) -> None:
    database_path = tmp_path / "persistent.db"
    with TestClient(create_app(database_path=database_path)) as first_client:
        mission = first_client.post(
            "/api/missions", json=mission_payload(clean_repo)
        ).json()

    with TestClient(create_app(database_path=database_path)) as second_client:
        fetched = second_client.get(f"/api/missions/{mission['id']}")

    assert fetched.status_code == 200
    assert fetched.json()["starting_commit"] == mission["starting_commit"]
