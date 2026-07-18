from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.orchestration import (
    Artifact,
    AssemblyConflictError,
    EventKind,
    FixedMissionController,
    InvalidMissionStartError,
    Mission,
    MissionEvent,
    MissionState,
    ReportRequest,
    ReviewDecision,
    VerificationRequest,
    VerificationResult,
    VerificationScope,
    VerificationStatus,
    WorkerRequest,
    WorkerResult,
    WorkerRole,
    WorkerStatus,
    Workspace,
)


class Gate:
    def __init__(self, action: str | None = None) -> None:
        self.action = action
        self.entered = asyncio.Event()
        self._consumed = False

    async def wait(self, action: str) -> None:
        if action != self.action or self._consumed:
            return
        self._consumed = True
        self.entered.set()
        await asyncio.Event().wait()


class FakeStore:
    def __init__(self, mission: Mission) -> None:
        self.missions = {mission.id: mission}
        self.transitions: list[tuple[MissionState, MissionState]] = []

    async def get(self, mission_id: str) -> Mission | None:
        return self.missions.get(mission_id)

    async def transition(
        self,
        mission_id: str,
        expected: MissionState,
        target: MissionState,
    ) -> Mission:
        mission = self.missions[mission_id]
        assert mission.state is expected
        updated = replace(mission, state=target)
        self.missions[mission_id] = updated
        self.transitions.append((expected, target))
        return updated


class FakeEvents:
    def __init__(self) -> None:
        self.items: list[MissionEvent] = []

    async def emit(self, event: MissionEvent) -> None:
        self.items.append(event)


class FakeWorkers:
    def __init__(self, gate: Gate) -> None:
        self.gate = gate
        self.results: dict[WorkerRole, WorkerResult] = {
            WorkerRole.SCOUT: WorkerResult(
                WorkerRole.SCOUT, WorkerStatus.SUCCEEDED, notes="inspect auth"
            ),
            WorkerRole.BUILDER: self.success(WorkerRole.BUILDER),
            WorkerRole.TESTER: self.success(WorkerRole.TESTER),
            WorkerRole.REVIEWER: WorkerResult(
                WorkerRole.REVIEWER,
                WorkerStatus.SUCCEEDED,
                review_decision=ReviewDecision.ACCEPT,
            ),
            WorkerRole.REPAIR: self.success(WorkerRole.REPAIR),
        }
        self.requests: list[WorkerRequest] = []
        self.cancelled: list[str] = []
        self.running = 0
        self.max_running = 0

    @staticmethod
    def success(role: WorkerRole) -> WorkerResult:
        return WorkerResult(
            role,
            WorkerStatus.SUCCEEDED,
            artifact=Artifact(role, f"{role.value}-artifact"),
        )

    async def run(self, request: WorkerRequest) -> WorkerResult:
        self.requests.append(request)
        self.running += 1
        self.max_running = max(self.max_running, self.running)
        try:
            # Let concurrently-created Phase A tasks overlap deterministically.
            if request.role in {WorkerRole.BUILDER, WorkerRole.TESTER}:
                await asyncio.sleep(0)
            await self.gate.wait(f"worker.{request.role.value}")
            return self.results[request.role]
        finally:
            self.running -= 1

    async def cancel(self, mission_id: str) -> None:
        self.cancelled.append(mission_id)


class FakeGit:
    def __init__(self, gate: Gate) -> None:
        self.gate = gate
        self.applied: list[WorkerRole] = []
        self.deadlines: list[datetime] = []
        self.conflict_role: WorkerRole | None = None

    async def validate_baseline(self, mission: Mission, *, deadline: datetime) -> None:
        self.deadlines.append(deadline)
        await self.gate.wait("baseline.validate")

    async def create_workspace(
        self, mission: Mission, *, deadline: datetime
    ) -> Workspace:
        self.deadlines.append(deadline)
        await self.gate.wait("workspace.create")
        return Workspace(
            "/fake/worktree", mission.integration_branch, mission.starting_commit
        )

    async def apply_artifact(
        self,
        workspace: Workspace,
        artifact: Artifact,
        *,
        deadline: datetime,
    ) -> str:
        self.deadlines.append(deadline)
        self.applied.append(artifact.role)
        await self.gate.wait(f"artifact.apply.{artifact.role.value}")
        if self.conflict_role is artifact.role:
            raise AssemblyConflictError(artifact.role.value)
        return f"integrated-{artifact.role.value}"


class FakeVerification:
    def __init__(self, gate: Gate) -> None:
        self.gate = gate
        self.statuses = {
            VerificationScope.FOCUSED: VerificationStatus.PASSED,
            VerificationScope.FINAL: VerificationStatus.PASSED,
        }
        self.requests: list[VerificationRequest] = []

    async def run(self, request: VerificationRequest) -> VerificationResult:
        self.requests.append(request)
        await self.gate.wait(f"verification.{request.scope.value}")
        return VerificationResult(request.scope, self.statuses[request.scope])


class FakeReports:
    def __init__(self, gate: Gate) -> None:
        self.gate = gate
        self.requests: list[ReportRequest] = []

    async def build(self, request: ReportRequest) -> dict[str, Any]:
        self.requests.append(request)
        await self.gate.wait("report.build")
        return {"outcome": request.outcome.value}


class Harness:
    def __init__(
        self,
        *,
        block: str | None = None,
        deadline: datetime | None = None,
        clock: datetime | None = None,
    ) -> None:
        self.deadline = deadline or datetime.now(UTC) + timedelta(minutes=5)
        mission = Mission(
            id="mission-1",
            objective="Implement and test feature",
            starting_commit="base",
            integration_branch="pluribus/mission-1/integration",
            deadline=self.deadline,
        )
        self.gate = Gate(block)
        self.store = FakeStore(mission)
        self.events = FakeEvents()
        self.workers = FakeWorkers(self.gate)
        self.git = FakeGit(self.gate)
        self.verification = FakeVerification(self.gate)
        self.reports = FakeReports(self.gate)
        self.controller = FixedMissionController(
            store=self.store,
            events=self.events,
            workers=self.workers,
            git=self.git,
            verification=self.verification,
            reports=self.reports,
            clock=(lambda: clock) if clock else None,
        )

    async def run(self) -> dict[str, Any]:
        return await self.controller.start("mission-1")


def run(harness: Harness) -> dict[str, Any]:
    return asyncio.run(harness.run())


def test_happy_path_executes_fixed_graph_with_typed_ordered_events() -> None:
    harness = Harness()

    result = run(harness)

    assert result["status"] == "verified"
    assert harness.git.applied == [WorkerRole.TESTER, WorkerRole.BUILDER]
    assert [request.role for request in harness.workers.requests] == [
        WorkerRole.SCOUT,
        WorkerRole.BUILDER,
        WorkerRole.TESTER,
        WorkerRole.REVIEWER,
    ]
    assert harness.workers.max_running == 2
    assert [event.sequence for event in harness.events.items] == list(
        range(1, len(harness.events.items) + 1)
    )
    assert all(event.deadline == harness.deadline for event in harness.events.items)
    assert harness.events.items[-1].kind is EventKind.STATE_TRANSITION
    assert harness.events.items[-1].details["to"] == "verified"
    assert len(harness.reports.requests) == 1
    assert harness.reports.requests[0].outcome is MissionState.VERIFIED


def test_deadline_is_propagated_to_every_dependency_request() -> None:
    harness = Harness()

    run(harness)

    assert set(harness.git.deadlines) == {harness.deadline}
    assert {request.deadline for request in harness.workers.requests} == {
        harness.deadline
    }
    assert {request.deadline for request in harness.verification.requests} == {
        harness.deadline
    }
    assert harness.reports.requests[0].deadline == harness.deadline


def test_reviewer_can_request_exactly_one_repair_from_candidate_commit() -> None:
    harness = Harness()
    harness.workers.results[WorkerRole.REVIEWER] = WorkerResult(
        WorkerRole.REVIEWER,
        WorkerStatus.SUCCEEDED,
        review_decision=ReviewDecision.REPAIR,
    )

    result = run(harness)

    assert result["status"] == "verified"
    assert harness.git.applied == [
        WorkerRole.TESTER,
        WorkerRole.BUILDER,
        WorkerRole.REPAIR,
    ]
    repair_requests = [
        request
        for request in harness.workers.requests
        if request.role is WorkerRole.REPAIR
    ]
    assert len(repair_requests) == 1
    assert repair_requests[0].candidate_commit == "integrated-builder"
    assert [r.scope for r in harness.verification.requests] == [
        VerificationScope.FOCUSED,
        VerificationScope.FINAL,
    ]


@pytest.mark.parametrize(
    ("role", "status", "reason"),
    [
        (WorkerRole.SCOUT, WorkerStatus.FAILED, "worker_failed:scout"),
        (WorkerRole.BUILDER, WorkerStatus.FAILED, "worker_failed:builder"),
        (WorkerRole.TESTER, WorkerStatus.FAILED, "worker_failed:tester"),
        (WorkerRole.SCOUT, WorkerStatus.TIMED_OUT, "worker_timeout:scout"),
        (WorkerRole.BUILDER, WorkerStatus.TIMED_OUT, "worker_timeout:builder"),
        (WorkerRole.TESTER, WorkerStatus.TIMED_OUT, "worker_timeout:tester"),
    ],
)
def test_phase_worker_failure_and_timeout_are_failed(
    role: WorkerRole, status: WorkerStatus, reason: str
) -> None:
    harness = Harness()
    harness.workers.results[role] = WorkerResult(role, status, error="boom")

    result = run(harness)

    assert result["status"] == "failed"
    assert reason in result["failure_reason"]
    assert len(harness.reports.requests) == 1


@pytest.mark.parametrize("role", [WorkerRole.TESTER, WorkerRole.BUILDER])
def test_assembly_conflict_requires_human_review(role: WorkerRole) -> None:
    harness = Harness()
    harness.git.conflict_role = role

    result = run(harness)

    assert result["status"] == "requires_human_review"
    assert result["failure_reason"] == f"assembly_conflict:{role.value}"


def test_reviewer_escalation_requires_human_review_without_final_verification() -> None:
    harness = Harness()
    harness.workers.results[WorkerRole.REVIEWER] = WorkerResult(
        WorkerRole.REVIEWER,
        WorkerStatus.SUCCEEDED,
        review_decision=ReviewDecision.ESCALATE,
    )

    result = run(harness)

    assert result["status"] == "requires_human_review"
    assert [request.scope for request in harness.verification.requests] == [
        VerificationScope.FOCUSED
    ]


@pytest.mark.parametrize("scope", [VerificationScope.FOCUSED, VerificationScope.FINAL])
def test_required_verification_failure_is_failed(scope: VerificationScope) -> None:
    harness = Harness()
    harness.verification.statuses[scope] = VerificationStatus.FAILED

    result = run(harness)

    assert result["status"] == "failed"
    assert result["failure_reason"] == f"{scope.value}_verification_failed"
    assert len(harness.reports.requests) == 1


@pytest.mark.parametrize("scope", [VerificationScope.FOCUSED, VerificationScope.FINAL])
def test_optional_verification_failure_is_partially_verified(
    scope: VerificationScope,
) -> None:
    harness = Harness()
    harness.verification.statuses[scope] = VerificationStatus.PARTIALLY_VERIFIED

    result = run(harness)

    assert result["status"] == "partially_verified"
    assert result["failure_reason"] is None


@pytest.mark.parametrize("scope", [VerificationScope.FOCUSED, VerificationScope.FINAL])
def test_verification_timeout_is_failed(scope: VerificationScope) -> None:
    harness = Harness()
    harness.verification.statuses[scope] = VerificationStatus.TIMED_OUT

    result = run(harness)

    assert result["status"] == "failed"
    assert result["failure_reason"] == f"{scope.value}_verification_timeout"


def test_repair_failure_does_not_spawn_a_second_repair() -> None:
    harness = Harness()
    harness.workers.results[WorkerRole.REVIEWER] = WorkerResult(
        WorkerRole.REVIEWER,
        WorkerStatus.SUCCEEDED,
        review_decision=ReviewDecision.REPAIR,
    )
    harness.workers.results[WorkerRole.REPAIR] = WorkerResult(
        WorkerRole.REPAIR, WorkerStatus.FAILED, error="still broken"
    )

    result = run(harness)

    assert result["status"] == "failed"
    assert sum(r.role is WorkerRole.REPAIR for r in harness.workers.requests) == 1


@pytest.mark.parametrize(
    ("role", "status"),
    [
        (WorkerRole.REVIEWER, WorkerStatus.FAILED),
        (WorkerRole.REVIEWER, WorkerStatus.TIMED_OUT),
        (WorkerRole.REPAIR, WorkerStatus.TIMED_OUT),
    ],
)
def test_late_worker_failure_and_timeout_are_failed(
    role: WorkerRole, status: WorkerStatus
) -> None:
    harness = Harness()
    if role is WorkerRole.REPAIR:
        harness.workers.results[WorkerRole.REVIEWER] = WorkerResult(
            WorkerRole.REVIEWER,
            WorkerStatus.SUCCEEDED,
            review_decision=ReviewDecision.REPAIR,
        )
    harness.workers.results[role] = WorkerResult(role, status, error="boom")

    result = run(harness)

    assert result["status"] == "failed"
    expected = "worker_timeout" if status is WorkerStatus.TIMED_OUT else "worker_failed"
    assert f"{expected}:{role.value}" in result["failure_reason"]


def test_expired_mission_deadline_fails_before_dependency_execution() -> None:
    now = datetime.now(UTC)
    harness = Harness(deadline=now - timedelta(seconds=1), clock=now)

    result = run(harness)

    assert result["status"] == "failed"
    assert result["failure_reason"] == "mission_deadline_exceeded"
    assert harness.reports.requests  # terminal reporting is still attempted


@pytest.mark.parametrize(
    "action",
    [
        "baseline.validate",
        "workspace.create",
        "worker.scout",
        "worker.builder",
        "artifact.apply.tester",
        "artifact.apply.builder",
        "verification.focused",
        "worker.reviewer",
        "worker.repair",
        "artifact.apply.repair",
        "verification.final",
        "report.build",
    ],
)
def test_cancellation_from_every_active_phase_is_stopped(action: str) -> None:
    async def scenario() -> None:
        harness = Harness(block=action)
        if action in {"worker.repair", "artifact.apply.repair"}:
            harness.workers.results[WorkerRole.REVIEWER] = WorkerResult(
                WorkerRole.REVIEWER,
                WorkerStatus.SUCCEEDED,
                review_decision=ReviewDecision.REPAIR,
            )
        task = asyncio.create_task(harness.run())
        await asyncio.wait_for(harness.gate.entered.wait(), timeout=1)

        await harness.controller.stop("mission-1")
        result = await task

        assert result["status"] == "stopped"
        assert harness.store.missions["mission-1"].state is MissionState.STOPPED
        assert harness.workers.cancelled == ["mission-1"]
        assert harness.reports.requests[-1].outcome is MissionState.STOPPED

    asyncio.run(scenario())


def test_duplicate_start_is_rejected_and_terminal_mission_cannot_restart() -> None:
    async def scenario() -> None:
        harness = Harness(block="worker.scout")
        first = asyncio.create_task(harness.run())
        await asyncio.wait_for(harness.gate.entered.wait(), timeout=1)

        with pytest.raises(InvalidMissionStartError, match="already active"):
            await harness.controller.start("mission-1")
        await harness.controller.stop("mission-1")
        await first
        with pytest.raises(InvalidMissionStartError, match="terminal"):
            await harness.controller.start("mission-1")

    asyncio.run(scenario())


def test_state_machine_rejects_restart_after_success() -> None:
    async def scenario() -> None:
        harness = Harness()
        await harness.run()
        with pytest.raises(InvalidMissionStartError, match="terminal"):
            await harness.run()

    asyncio.run(scenario())
