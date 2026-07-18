from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from app.db import Database
from app.orchestration.models import EventKind, MissionEvent, MissionState
from app.orchestration.persistence import (
    DatabaseEventSink,
    DatabaseMissionStore,
    MissionPersistenceError,
)


def create_mission(database: Database, *, status: str = "created") -> dict[str, object]:
    created_at = datetime.now(UTC).replace(microsecond=0)
    return database.create_mission(
        {
            "id": "mission-persistence",
            "objective": "Implement a verified feature",
            "repository_path": "/repo",
            "starting_commit": "a" * 40,
            "starting_branch": "main",
            "was_dirty": False,
            "integration_branch": "hive/mission-persistence/integration",
            "status": status,
            "agent_count": 4,
            "max_concurrency": 2,
            "allow_dirty_repository": False,
            "protected_paths": [".git/**"],
            "verification_commands": [],
            "created_at": created_at.isoformat(),
            "completed_at": None,
        },
        [
            {
                "id": f"{role}_1",
                "mission_id": "mission-persistence",
                "role": role,
                "status": "pending",
            }
            for role in ("scout", "builder", "tester", "reviewer")
        ],
    )


def test_database_store_loads_and_transitions_atomically(tmp_path) -> None:
    database = Database(tmp_path / "pluribus.db")
    database.initialize()
    record = create_mission(database)
    store = DatabaseMissionStore(database, mission_timeout_seconds=90)

    mission = asyncio.run(store.get("mission-persistence"))
    assert mission is not None
    assert mission.state is MissionState.CREATED
    assert mission.deadline == datetime.fromisoformat(record["created_at"]) + timedelta(
        seconds=90
    )

    updated = asyncio.run(
        store.transition(
            mission.id,
            MissionState.CREATED,
            MissionState.BASELINE_VALIDATING,
        )
    )

    assert updated.state is MissionState.BASELINE_VALIDATING
    persisted = database.get_mission(mission.id)
    assert persisted is not None
    assert persisted["status"] == "baseline_validating"
    transition_events = [
        event
        for event in database.list_events(mission.id)
        if event["event_type"] == "mission.state_changed"
    ]
    assert transition_events[-1]["payload"] == {
        "schema_version": 1,
        "from": "created",
        "to": "baseline_validating",
    }


def test_database_store_rejects_stale_expected_state(tmp_path) -> None:
    database = Database(tmp_path / "pluribus.db")
    database.initialize()
    create_mission(database, status="scouting")
    store = DatabaseMissionStore(database)

    with pytest.raises(
        MissionPersistenceError, match="expected created, found scouting"
    ):
        asyncio.run(
            store.transition(
                "mission-persistence",
                MissionState.CREATED,
                MissionState.BASELINE_VALIDATING,
            )
        )

    assert database.get_mission("mission-persistence")["status"] == "scouting"  # type: ignore[index]


def test_database_event_sink_preserves_sequence_and_details(tmp_path) -> None:
    database = Database(tmp_path / "pluribus.db")
    database.initialize()
    create_mission(database)
    deadline = datetime.now(UTC) + timedelta(minutes=5)
    sink = DatabaseEventSink(database)

    asyncio.run(
        sink.emit(
            MissionEvent(
                sequence=7,
                mission_id="mission-persistence",
                kind=EventKind.ACTION_COMPLETED,
                state=MissionState.SCOUTING,
                action="worker.scout",
                deadline=deadline,
                details={"artifact": "knowledge-1"},
            )
        )
    )

    event = database.list_events("mission-persistence")[-1]
    assert event["event_type"] == "orchestration.action_completed"
    assert event["payload"] == {
        "schema_version": 1,
        "sequence": 7,
        "state": "scouting",
        "action": "worker.scout",
        "deadline": deadline.isoformat(),
        "details": {"artifact": "knowledge-1"},
    }


def test_database_store_marks_terminal_completion_time(tmp_path) -> None:
    database = Database(tmp_path / "pluribus.db")
    database.initialize()
    create_mission(database, status="reporting")
    store = DatabaseMissionStore(database)

    asyncio.run(
        store.transition(
            "mission-persistence",
            MissionState.REPORTING,
            MissionState.VERIFIED,
        )
    )

    persisted = database.get_mission("mission-persistence")
    assert persisted is not None
    assert persisted["completed_at"] is not None
