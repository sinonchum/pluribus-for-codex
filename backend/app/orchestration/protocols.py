from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from .models import (
    Artifact,
    Mission,
    MissionEvent,
    MissionState,
    ReportRequest,
    VerificationRequest,
    VerificationResult,
    WorkerRequest,
    WorkerResult,
    Workspace,
)


class MissionStore(Protocol):
    async def get(self, mission_id: str) -> Mission | None: ...

    async def transition(
        self,
        mission_id: str,
        expected: MissionState,
        target: MissionState,
    ) -> Mission: ...


class EventSink(Protocol):
    async def emit(self, event: MissionEvent) -> None: ...


class WorkerRuntime(Protocol):
    async def run(self, request: WorkerRequest) -> WorkerResult: ...

    async def cancel(self, mission_id: str) -> None: ...


class GitIntegrator(Protocol):
    async def validate_baseline(
        self, mission: Mission, *, deadline: datetime
    ) -> None: ...

    async def create_workspace(
        self, mission: Mission, *, deadline: datetime
    ) -> Workspace: ...

    async def apply_artifact(
        self,
        workspace: Workspace,
        artifact: Artifact,
        *,
        deadline: datetime,
    ) -> str: ...


class VerificationRunner(Protocol):
    async def run(self, request: VerificationRequest) -> VerificationResult: ...


class ReportBuilder(Protocol):
    async def build(self, request: ReportRequest) -> dict[str, Any]: ...
