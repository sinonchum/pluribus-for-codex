from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.db import Database


def now() -> str:
    return datetime.now(UTC).isoformat()


@pytest.fixture
def database(tmp_path: Path) -> Database:
    db = Database(tmp_path / "orchestration.db")
    db.initialize()
    created_at = now()
    db.create_mission(
        {
            "id": "mission_test",
            "repository_path": str(tmp_path),
            "objective": "test orchestration persistence",
            "starting_commit": "a" * 40,
            "starting_branch": "main",
            "was_dirty": False,
            "integration_branch": "pluribus/mission_test/integration",
            "status": "created",
            "agent_count": 4,
            "max_concurrency": 2,
            "allow_dirty_repository": False,
            "protected_paths": [".git/**"],
            "verification_commands": [],
            "created_at": created_at,
            "completed_at": None,
        },
        [
            {
                "id": f"{role}_1",
                "mission_id": "mission_test",
                "role": role,
                "status": "pending",
            }
            for role in ("scout", "builder", "tester", "reviewer")
        ],
    )
    return db


def test_append_event_returns_persisted_ordered_event(database: Database) -> None:
    event = database.append_event(
        mission_id="mission_test",
        event_type="repository.baseline_validated",
        payload={"commit": "a" * 40, "schema_version": 1},
        created_at=now(),
    )

    assert event["event_type"] == "repository.baseline_validated"
    assert event["payload"]["schema_version"] == 1
    assert database.list_events("mission_test")[-1] == event


def test_transition_mission_changes_state_and_event_atomically(
    database: Database,
) -> None:
    changed = database.transition_mission(
        mission_id="mission_test",
        expected_statuses={"created"},
        new_status="starting",
        event_type="mission.starting",
        payload={"status": "starting", "schema_version": 1},
        created_at=now(),
    )

    assert changed is not None
    assert changed["status"] == "starting"
    assert database.list_events("mission_test")[-1]["event_type"] == "mission.starting"


def test_transition_rejects_stale_expected_state_without_event(
    database: Database,
) -> None:
    before = database.list_events("mission_test")

    changed = database.transition_mission(
        mission_id="mission_test",
        expected_statuses={"running"},
        new_status="verified",
        event_type="mission.completed",
        payload={"status": "verified"},
        created_at=now(),
    )

    assert changed is None
    assert database.get_mission("mission_test")["status"] == "created"
    assert database.list_events("mission_test") == before


def test_update_agent_persists_runtime_fields_and_event(database: Database) -> None:
    started_at = now()
    updated = database.update_agent(
        mission_id="mission_test",
        agent_id="builder_1",
        status="running",
        created_at=started_at,
        worktree_path="C:/worktrees/builder",
        branch_name="hive/mission_test/builder-1",
        process_id=1234,
        started_at=started_at,
    )

    assert updated is not None
    assert updated["status"] == "running"
    assert updated["worktree_path"] == "C:/worktrees/builder"
    assert updated["process_id"] == 1234
    event = database.list_events("mission_test")[-1]
    assert event["event_type"] == "agent.running"
    assert event["agent_id"] == "builder_1"


def test_append_event_for_unknown_mission_rolls_back(database: Database) -> None:
    before = database.list_events("mission_test")

    with pytest.raises(sqlite3.IntegrityError):
        database.append_event(
            mission_id="missing",
            event_type="mission.starting",
            payload={},
            created_at=now(),
        )

    assert database.list_events("mission_test") == before
