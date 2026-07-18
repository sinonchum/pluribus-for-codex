from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class MissionState(StrEnum):
    CREATED = "created"
    BASELINE_VALIDATING = "baseline_validating"
    WORKSPACE_CREATING = "workspace_creating"
    SCOUTING = "scouting"
    PHASE_A = "phase_a"
    ASSEMBLING_TESTER = "assembling_tester"
    ASSEMBLING_BUILDER = "assembling_builder"
    FOCUSED_VERIFICATION = "focused_verification"
    REVIEWING = "reviewing"
    REPAIRING = "repairing"
    ASSEMBLING_REPAIR = "assembling_repair"
    FINAL_VERIFICATION = "final_verification"
    REPORTING = "reporting"
    VERIFIED = "verified"
    PARTIALLY_VERIFIED = "partially_verified"
    FAILED = "failed"
    REQUIRES_HUMAN_REVIEW = "requires_human_review"
    STOPPED = "stopped"


TERMINAL_STATES = frozenset(
    {
        MissionState.VERIFIED,
        MissionState.PARTIALLY_VERIFIED,
        MissionState.FAILED,
        MissionState.REQUIRES_HUMAN_REVIEW,
        MissionState.STOPPED,
    }
)
ACTIVE_STATES = frozenset(set(MissionState) - TERMINAL_STATES - {MissionState.CREATED})

# This table is the executable state machine. Keeping transitions as data makes
# invalid transitions reviewable and independently testable.
STATE_TRANSITIONS: dict[MissionState, frozenset[MissionState]] = {
    MissionState.CREATED: frozenset(
        {MissionState.BASELINE_VALIDATING, MissionState.STOPPED}
    ),
    MissionState.BASELINE_VALIDATING: frozenset(
        {MissionState.WORKSPACE_CREATING, MissionState.REPORTING, MissionState.STOPPED}
    ),
    MissionState.WORKSPACE_CREATING: frozenset(
        {MissionState.SCOUTING, MissionState.REPORTING, MissionState.STOPPED}
    ),
    MissionState.SCOUTING: frozenset(
        {MissionState.PHASE_A, MissionState.REPORTING, MissionState.STOPPED}
    ),
    MissionState.PHASE_A: frozenset(
        {MissionState.ASSEMBLING_TESTER, MissionState.REPORTING, MissionState.STOPPED}
    ),
    MissionState.ASSEMBLING_TESTER: frozenset(
        {MissionState.ASSEMBLING_BUILDER, MissionState.REPORTING, MissionState.STOPPED}
    ),
    MissionState.ASSEMBLING_BUILDER: frozenset(
        {
            MissionState.FOCUSED_VERIFICATION,
            MissionState.REPORTING,
            MissionState.STOPPED,
        }
    ),
    MissionState.FOCUSED_VERIFICATION: frozenset(
        {MissionState.REVIEWING, MissionState.REPORTING, MissionState.STOPPED}
    ),
    MissionState.REVIEWING: frozenset(
        {
            MissionState.REPAIRING,
            MissionState.FINAL_VERIFICATION,
            MissionState.REPORTING,
            MissionState.STOPPED,
        }
    ),
    MissionState.REPAIRING: frozenset(
        {MissionState.ASSEMBLING_REPAIR, MissionState.REPORTING, MissionState.STOPPED}
    ),
    MissionState.ASSEMBLING_REPAIR: frozenset(
        {
            MissionState.FINAL_VERIFICATION,
            MissionState.REPORTING,
            MissionState.STOPPED,
        }
    ),
    MissionState.FINAL_VERIFICATION: frozenset(
        {MissionState.REPORTING, MissionState.STOPPED}
    ),
    MissionState.REPORTING: TERMINAL_STATES,
    **{state: frozenset() for state in TERMINAL_STATES},
}


class WorkerRole(StrEnum):
    SCOUT = "scout"
    BUILDER = "builder"
    TESTER = "tester"
    REVIEWER = "reviewer"
    REPAIR = "repair"


class WorkerStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMED_OUT = "timed_out"


class ReviewDecision(StrEnum):
    ACCEPT = "accept"
    REPAIR = "repair"
    ESCALATE = "escalate"


class VerificationScope(StrEnum):
    FOCUSED = "focused"
    FINAL = "final"


class VerificationStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"


class EventKind(StrEnum):
    STATE_TRANSITION = "state_transition"
    ACTION_STARTED = "action_started"
    ACTION_COMPLETED = "action_completed"
    ACTION_FAILED = "action_failed"


@dataclass(frozen=True, slots=True)
class Mission:
    id: str
    objective: str
    starting_commit: str
    integration_branch: str
    deadline: datetime
    state: MissionState = MissionState.CREATED


@dataclass(frozen=True, slots=True)
class Workspace:
    path: str
    branch: str
    commit: str


@dataclass(frozen=True, slots=True)
class Artifact:
    role: WorkerRole
    commit: str


@dataclass(frozen=True, slots=True)
class WorkerRequest:
    mission_id: str
    role: WorkerRole
    objective: str
    deadline: datetime
    workspace: Workspace
    scout_notes: str | None = None
    candidate_commit: str | None = None


@dataclass(frozen=True, slots=True)
class WorkerResult:
    role: WorkerRole
    status: WorkerStatus
    artifact: Artifact | None = None
    notes: str | None = None
    review_decision: ReviewDecision | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class VerificationRequest:
    mission_id: str
    scope: VerificationScope
    candidate_commit: str
    deadline: datetime


@dataclass(frozen=True, slots=True)
class VerificationResult:
    scope: VerificationScope
    status: VerificationStatus
    details: str = ""


@dataclass(frozen=True, slots=True)
class ReportRequest:
    mission_id: str
    outcome: MissionState
    candidate_commit: str | None
    focused_verification: VerificationResult | None
    final_verification: VerificationResult | None
    deadline: datetime
    failure_reason: str | None = None


@dataclass(frozen=True, slots=True)
class MissionEvent:
    sequence: int
    mission_id: str
    kind: EventKind
    state: MissionState
    action: str
    deadline: datetime
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MissionResult:
    mission_id: str
    status: MissionState
    candidate_commit: str | None
    report: dict[str, Any]
    failure_reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "status": self.status.value,
            "candidate_commit": self.candidate_commit,
            "report": self.report,
            "failure_reason": self.failure_reason,
        }
