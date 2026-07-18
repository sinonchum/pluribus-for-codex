from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, TypeVar

from .models import (
    STATE_TRANSITIONS,
    TERMINAL_STATES,
    Artifact,
    EventKind,
    Mission,
    MissionEvent,
    MissionResult,
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
from .protocols import (
    EventSink,
    GitIntegrator,
    MissionStore,
    ReportBuilder,
    VerificationRunner,
    WorkerRuntime,
)

T = TypeVar("T")


class MissionControllerError(RuntimeError):
    """Base exception for orchestration contract errors."""


class MissionNotFoundError(MissionControllerError):
    pass


class InvalidMissionStartError(MissionControllerError):
    pass


class InvalidStateTransitionError(MissionControllerError):
    pass


class AssemblyConflictError(MissionControllerError):
    """Raised by a GitIntegrator when an artifact cannot be applied cleanly."""


class _MissionFailure(MissionControllerError):
    pass


@dataclass(slots=True)
class _RunContext:
    mission: Mission
    state: MissionState
    workspace: Workspace | None = None
    candidate_commit: str | None = None
    focused: VerificationResult | None = None
    final: VerificationResult | None = None
    failure_reason: str | None = None


class MissionController:
    """Dependency-inverted executor for the scope-frozen four-worker mission graph."""

    def __init__(
        self,
        *,
        store: MissionStore,
        events: EventSink,
        workers: WorkerRuntime,
        git: GitIntegrator,
        verification: VerificationRunner,
        reports: ReportBuilder,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._store = store
        self._events = events
        self._workers = workers
        self._git = git
        self._verification = verification
        self._reports = reports
        self._clock = clock or (lambda: datetime.now(UTC))
        self._worker_slots = asyncio.Semaphore(2)
        self._guard = asyncio.Lock()
        self._active: dict[str, asyncio.Task[Any]] = {}
        self._sequences: dict[str, int] = {}

    async def start(self, mission_id: str) -> dict[str, Any]:
        task = asyncio.current_task()
        if task is None:  # pragma: no cover - asyncio always provides one here
            raise RuntimeError("start must run inside an asyncio task")

        async with self._guard:
            mission = await self._store.get(mission_id)
            if mission is None:
                raise MissionNotFoundError(mission_id)
            if mission_id in self._active:
                raise InvalidMissionStartError(
                    f"mission {mission_id} is already active"
                )
            if mission.state is not MissionState.CREATED:
                qualifier = "terminal" if mission.state in TERMINAL_STATES else "active"
                raise InvalidMissionStartError(
                    f"cannot start {qualifier} mission {mission_id} "
                    f"from {mission.state.value}"
                )
            self._active[mission_id] = task

        context = _RunContext(mission=mission, state=mission.state)
        try:
            result = await self._execute(context)
        except asyncio.CancelledError:
            result = await self._stop_result(context)
        finally:
            async with self._guard:
                if self._active.get(mission_id) is task:
                    del self._active[mission_id]
        return result.as_dict()

    async def stop(self, mission_id: str) -> None:
        async with self._guard:
            mission = await self._store.get(mission_id)
            if mission is None:
                raise MissionNotFoundError(mission_id)
            if mission.state in TERMINAL_STATES:
                return
            task = self._active.get(mission_id)
            if task is None:
                raise InvalidStateTransitionError(
                    f"mission {mission_id} is not currently active"
                )
            await self._workers.cancel(mission_id)
            task.cancel()
        if task is not asyncio.current_task():
            with suppress(asyncio.CancelledError):
                await task

    async def _execute(self, context: _RunContext) -> MissionResult:
        try:
            await self._transition(context, MissionState.BASELINE_VALIDATING)
            await self._action(
                context,
                "baseline.validate",
                self._git.validate_baseline(
                    context.mission, deadline=context.mission.deadline
                ),
            )

            await self._transition(context, MissionState.WORKSPACE_CREATING)
            context.workspace = await self._action(
                context,
                "workspace.create",
                self._git.create_workspace(
                    context.mission, deadline=context.mission.deadline
                ),
            )
            context.candidate_commit = context.workspace.commit

            await self._transition(context, MissionState.SCOUTING)
            scout = await self._run_worker(context, WorkerRole.SCOUT)
            self._require_worker_success(scout)

            await self._transition(context, MissionState.PHASE_A)
            builder, tester = await asyncio.gather(
                self._run_worker(context, WorkerRole.BUILDER, scout.notes),
                self._run_worker(context, WorkerRole.TESTER, scout.notes),
            )
            self._require_worker_success(builder, artifact=True)
            self._require_worker_success(tester, artifact=True)

            # Assembly order is intentionally fixed: tests first, implementation second.
            await self._transition(context, MissionState.ASSEMBLING_TESTER)
            await self._apply(context, tester.artifact)
            await self._transition(context, MissionState.ASSEMBLING_BUILDER)
            await self._apply(context, builder.artifact)

            await self._transition(context, MissionState.FOCUSED_VERIFICATION)
            context.focused = await self._verify(context, VerificationScope.FOCUSED)
            if context.focused.status is VerificationStatus.TIMED_OUT:
                raise _MissionFailure("focused_verification_timeout")

            await self._transition(context, MissionState.REVIEWING)
            reviewer = await self._run_worker(context, WorkerRole.REVIEWER, scout.notes)
            self._require_worker_success(reviewer)
            if reviewer.review_decision is ReviewDecision.ESCALATE:
                return await self._finish(
                    context,
                    MissionState.REQUIRES_HUMAN_REVIEW,
                    "reviewer_escalation",
                )
            if reviewer.review_decision is ReviewDecision.REPAIR:
                await self._transition(context, MissionState.REPAIRING)
                repair = await self._run_worker(context, WorkerRole.REPAIR, scout.notes)
                self._require_worker_success(repair, artifact=True)
                await self._transition(context, MissionState.ASSEMBLING_REPAIR)
                await self._apply(context, repair.artifact)
            elif reviewer.review_decision is not ReviewDecision.ACCEPT:
                raise _MissionFailure("reviewer_missing_decision")

            await self._transition(context, MissionState.FINAL_VERIFICATION)
            context.final = await self._verify(context, VerificationScope.FINAL)
            if context.final.status is VerificationStatus.TIMED_OUT:
                raise _MissionFailure("final_verification_timeout")
            outcome = (
                MissionState.VERIFIED
                if context.focused.status is VerificationStatus.PASSED
                and context.final.status is VerificationStatus.PASSED
                else MissionState.PARTIALLY_VERIFIED
            )
            return await self._finish(context, outcome)
        except AssemblyConflictError as error:
            return await self._finish(
                context, MissionState.FAILED, f"assembly_conflict:{error}"
            )
        except TimeoutError:
            return await self._finish(
                context, MissionState.FAILED, "mission_deadline_exceeded"
            )
        except _MissionFailure as error:
            return await self._finish(context, MissionState.FAILED, str(error))
        except asyncio.CancelledError:
            raise
        # Dependency failures are mission failures, not controller crashes.
        except Exception as error:
            return await self._finish(
                context,
                MissionState.FAILED,
                f"{type(error).__name__}:{error}",
            )

    async def _run_worker(
        self,
        context: _RunContext,
        role: WorkerRole,
        scout_notes: str | None = None,
    ) -> WorkerResult:
        workspace = self._workspace(context)
        request = WorkerRequest(
            mission_id=context.mission.id,
            role=role,
            objective=context.mission.objective,
            deadline=context.mission.deadline,
            workspace=workspace,
            scout_notes=scout_notes,
            candidate_commit=context.candidate_commit,
        )
        async with self._worker_slots:
            try:
                return await self._action(
                    context, f"worker.{role.value}", self._workers.run(request)
                )
            except TimeoutError as error:
                raise _MissionFailure(f"worker_timeout:{role.value}") from error

    async def _apply(self, context: _RunContext, artifact: Artifact | None) -> None:
        if artifact is None:  # guarded by _require_worker_success
            raise _MissionFailure("worker_missing_artifact")
        context.candidate_commit = await self._action(
            context,
            f"artifact.apply.{artifact.role.value}",
            self._git.apply_artifact(
                self._workspace(context),
                artifact,
                deadline=context.mission.deadline,
            ),
        )

    async def _verify(
        self, context: _RunContext, scope: VerificationScope
    ) -> VerificationResult:
        if context.candidate_commit is None:
            raise _MissionFailure("candidate_commit_missing")
        request = VerificationRequest(
            mission_id=context.mission.id,
            scope=scope,
            candidate_commit=context.candidate_commit,
            deadline=context.mission.deadline,
        )
        return await self._action(
            context,
            f"verification.{scope.value}",
            self._verification.run(request),
        )

    async def _finish(
        self,
        context: _RunContext,
        outcome: MissionState,
        failure_reason: str | None = None,
    ) -> MissionResult:
        context.failure_reason = failure_reason
        if context.state is not MissionState.REPORTING:
            await self._transition(context, MissionState.REPORTING)
        report_request = ReportRequest(
            mission_id=context.mission.id,
            outcome=outcome,
            candidate_commit=context.candidate_commit,
            focused_verification=context.focused,
            final_verification=context.final,
            deadline=context.mission.deadline,
            failure_reason=failure_reason,
        )
        try:
            report = await self._report_action(context, report_request)
        except Exception as error:
            report = {"error": f"{type(error).__name__}:{error}"}
            if (
                outcome
                not in {MissionState.STOPPED, MissionState.REQUIRES_HUMAN_REVIEW}
                and context.failure_reason is None
            ):
                outcome = MissionState.FAILED
                context.failure_reason = "report_build_failed"
        await self._transition(context, outcome)
        return MissionResult(
            mission_id=context.mission.id,
            status=outcome,
            candidate_commit=context.candidate_commit,
            report=report,
            failure_reason=context.failure_reason,
        )

    async def _stop_result(self, context: _RunContext) -> MissionResult:
        if context.state not in TERMINAL_STATES:
            await self._transition(context, MissionState.STOPPED)
        request = ReportRequest(
            mission_id=context.mission.id,
            outcome=MissionState.STOPPED,
            candidate_commit=context.candidate_commit,
            focused_verification=context.focused,
            final_verification=context.final,
            deadline=context.mission.deadline,
            failure_reason="cancelled",
        )
        try:
            report = await self._report_action(context, request)
        except Exception as error:  # cancellation must remain terminal
            report = {"error": f"{type(error).__name__}:{error}"}
        return MissionResult(
            mission_id=context.mission.id,
            status=MissionState.STOPPED,
            candidate_commit=context.candidate_commit,
            report=report,
            failure_reason="cancelled",
        )

    async def _transition(self, context: _RunContext, target: MissionState) -> None:
        allowed = STATE_TRANSITIONS[context.state]
        if target not in allowed:
            raise InvalidStateTransitionError(
                f"invalid mission transition {context.state.value} -> {target.value}"
            )
        previous = context.state
        mission = await self._store.transition(
            context.mission.id,
            expected=previous,
            target=target,
        )
        context.mission = mission
        context.state = target
        await self._emit(
            context,
            EventKind.STATE_TRANSITION,
            "state.transition",
            {"from": previous.value, "to": target.value},
        )

    async def _action(
        self, context: _RunContext, name: str, awaitable: Awaitable[T]
    ) -> T:
        await self._emit(context, EventKind.ACTION_STARTED, name)
        try:
            result = await self._before_deadline(context.mission.deadline, awaitable)
        except (Exception, asyncio.CancelledError) as error:
            await self._emit(
                context,
                EventKind.ACTION_FAILED,
                name,
                {"error": type(error).__name__},
            )
            raise
        await self._emit(context, EventKind.ACTION_COMPLETED, name)
        return result

    async def _report_action(
        self, context: _RunContext, request: ReportRequest
    ) -> dict[str, Any]:
        """Build the terminal report even when the execution deadline has elapsed."""
        name = "report.build"
        await self._emit(context, EventKind.ACTION_STARTED, name)
        try:
            report = await self._reports.build(request)
        except (Exception, asyncio.CancelledError) as error:
            await self._emit(
                context,
                EventKind.ACTION_FAILED,
                name,
                {"error": type(error).__name__},
            )
            raise
        await self._emit(context, EventKind.ACTION_COMPLETED, name)
        return report

    async def _before_deadline(self, deadline: datetime, awaitable: Awaitable[T]) -> T:
        remaining = (deadline - self._clock()).total_seconds()
        if remaining <= 0:
            if hasattr(awaitable, "close"):
                awaitable.close()  # type: ignore[attr-defined]
            raise TimeoutError
        async with asyncio.timeout(remaining):
            return await awaitable

    async def _emit(
        self,
        context: _RunContext,
        kind: EventKind,
        action: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        mission_id = context.mission.id
        sequence = self._sequences.get(mission_id, 0) + 1
        self._sequences[mission_id] = sequence
        await self._events.emit(
            MissionEvent(
                sequence=sequence,
                mission_id=mission_id,
                kind=kind,
                state=context.state,
                action=action,
                deadline=context.mission.deadline,
                details=details or {},
            )
        )

    @staticmethod
    def _require_worker_success(
        result: WorkerResult, *, artifact: bool = False
    ) -> None:
        if result.status is WorkerStatus.TIMED_OUT:
            raise _MissionFailure(f"worker_timeout:{result.role.value}")
        if result.status is WorkerStatus.FAILED:
            raise _MissionFailure(
                f"worker_failed:{result.role.value}:{result.error or ''}"
            )
        if artifact and result.artifact is None:
            raise _MissionFailure(f"worker_missing_artifact:{result.role.value}")

    @staticmethod
    def _workspace(context: _RunContext) -> Workspace:
        if context.workspace is None:
            raise _MissionFailure("workspace_missing")
        return context.workspace


# Descriptive compatibility name for callers that want to emphasize the fixed graph.
FixedMissionController = MissionController
