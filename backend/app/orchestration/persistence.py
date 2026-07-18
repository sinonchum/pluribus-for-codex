from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any

from app.db import Database

from .models import Mission, MissionEvent, MissionState


class MissionPersistenceError(RuntimeError):
    """Raised when persisted state no longer matches orchestration expectations."""


class DatabaseMissionStore:
    """SQLite-backed MissionStore adapter for the fixed mission controller."""

    def __init__(
        self, database: Database, *, mission_timeout_seconds: int = 720
    ) -> None:
        if mission_timeout_seconds <= 0:
            raise ValueError("mission_timeout_seconds must be positive")
        self._database = database
        self._mission_timeout = timedelta(seconds=mission_timeout_seconds)

    async def get(self, mission_id: str) -> Mission | None:
        record = self._database.get_mission(mission_id)
        return self._to_mission(record) if record is not None else None

    async def transition(
        self,
        mission_id: str,
        expected: MissionState,
        target: MissionState,
    ) -> Mission:
        now = datetime.now(UTC)
        terminal = target in {
            MissionState.VERIFIED,
            MissionState.PARTIALLY_VERIFIED,
            MissionState.FAILED,
            MissionState.REQUIRES_HUMAN_REVIEW,
            MissionState.STOPPED,
        }
        record = self._database.transition_mission(
            mission_id=mission_id,
            expected_statuses={expected.value},
            new_status=target.value,
            event_type="mission.state_changed",
            payload={
                "schema_version": 1,
                "from": expected.value,
                "to": target.value,
            },
            created_at=now.isoformat(),
            completed_at=now.isoformat() if terminal else None,
        )
        if record is None:
            current = self._database.get_mission(mission_id)
            current_status = current["status"] if current else "missing"
            raise MissionPersistenceError(
                f"mission {mission_id} expected {expected.value}, "
                f"found {current_status}"
            )
        return self._to_mission(record)

    def _to_mission(self, record: dict[str, Any]) -> Mission:
        created_at = datetime.fromisoformat(record["created_at"])
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        return Mission(
            id=record["id"],
            objective=record["objective"],
            starting_commit=record["starting_commit"],
            integration_branch=record["integration_branch"],
            deadline=created_at + self._mission_timeout,
            state=MissionState(record["status"]),
        )


class DatabaseEventSink:
    """Persist ordered Coordinator events before SSE projects them to clients."""

    def __init__(self, database: Database) -> None:
        self._database = database

    async def emit(self, event: MissionEvent) -> None:
        self._database.append_event(
            mission_id=event.mission_id,
            event_type=f"orchestration.{event.kind.value}",
            payload={
                "schema_version": 1,
                "sequence": event.sequence,
                "state": event.state.value,
                "action": event.action,
                "deadline": event.deadline.isoformat(),
                "details": event.details,
            },
            created_at=datetime.now(UTC).isoformat(),
        )


class InMemoryMissionStore:
    """Small public fake useful for adapter and end-to-end tests."""

    def __init__(self, mission: Mission) -> None:
        self.missions = {mission.id: mission}

    async def get(self, mission_id: str) -> Mission | None:
        return self.missions.get(mission_id)

    async def transition(
        self,
        mission_id: str,
        expected: MissionState,
        target: MissionState,
    ) -> Mission:
        mission = self.missions[mission_id]
        if mission.state is not expected:
            raise MissionPersistenceError(
                f"mission {mission_id} expected {expected.value}, "
                f"found {mission.state.value}"
            )
        mission = replace(mission, state=target)
        self.missions[mission_id] = mission
        return mission
