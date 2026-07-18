"""Typed, deterministic, and defensively redacted evidence reporting."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Final

from app.verification import (
    CommandResult,
    VerificationSummary,
    VerificationTerminalState,
)

DEFAULT_LOG_LIMIT_BYTES: Final = 16 * 1024
_REDACTED: Final = "[REDACTED]"
_SECRET_PATTERNS: Final = (
    re.compile(
        r"(?is)-----BEGIN [A-Z ]*PRIVATE KEY-----.*?"
        r"-----END [A-Z ]*PRIVATE KEY-----"
    ),
    re.compile(r"(?i)(\bauthorization\s*[:=]\s*)[^\r\n,;]+"),
    re.compile(r"(?i)(\bbearer\s+)[A-Za-z0-9._~+/=-]+"),
    re.compile(
        r"(?i)(\b(?:api[_-]?key|access[_-]?token|auth[_-]?token|password|passwd|"
        r"client[_-]?secret|secret)\b\s*[:=]\s*)"
        r"([\"']?)[^\s,;\"']+([\"']?)"
    ),
    re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{16,})\b"),
    re.compile(r"(?i)(https?://[^\s/:@]+:)[^\s/@]+(@)"),
)


@dataclass(frozen=True, slots=True)
class Mission:
    mission_id: str
    objective: str


@dataclass(frozen=True, slots=True)
class Baseline:
    revision: str
    summary: str


@dataclass(frozen=True, slots=True)
class OriginalInvariant:
    statement: str


@dataclass(frozen=True, slots=True)
class AgentRecord:
    agent_id: str
    role: str
    outcome: str


@dataclass(frozen=True, slots=True)
class TimelineEvent:
    timestamp: str
    event_id: str
    description: str


@dataclass(frozen=True, slots=True)
class KnowledgeDelivery:
    delivery_id: str
    source_agent: str
    recipient_agent: str
    knowledge: str
    causal_uses: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "causal_uses", tuple(self.causal_uses))


@dataclass(frozen=True, slots=True)
class ArtifactRecord:
    path: str
    sha256: str
    application_order: int
    description: str = ""


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    source: str
    summary: str
    log: str = ""


@dataclass(frozen=True, slots=True)
class VerificationRecord:
    name: str
    executable: str
    args: tuple[str, ...]
    cwd: str
    timeout_seconds: float
    required: bool
    status: str
    exit_code: int | None
    duration_seconds: float
    stdout: str
    stderr: str
    command_sha256: str
    stdout_sha256: str
    stderr_sha256: str
    stdout_truncated: bool = False
    stderr_truncated: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "args", tuple(self.args))

    @classmethod
    def from_command_result(cls, result: CommandResult) -> VerificationRecord:
        return cls(
            name=result.spec.name or result.spec.executable,
            executable=result.spec.executable,
            args=result.spec.args,
            cwd=str(result.spec.cwd),
            timeout_seconds=result.spec.timeout_seconds,
            required=result.spec.required,
            status=result.status.value,
            exit_code=result.exit_code,
            duration_seconds=result.duration_seconds,
            stdout=result.stdout,
            stderr=result.stderr,
            command_sha256=result.command_sha256,
            stdout_sha256=result.stdout_sha256,
            stderr_sha256=result.stderr_sha256,
            stdout_truncated=result.stdout_truncated,
            stderr_truncated=result.stderr_truncated,
        )


@dataclass(frozen=True, slots=True)
class CoordinatorVerification:
    terminal_state: VerificationTerminalState
    commands: tuple[VerificationRecord, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "terminal_state", VerificationTerminalState(self.terminal_state)
        )
        object.__setattr__(self, "commands", tuple(self.commands))

    @classmethod
    def from_summary(cls, summary: VerificationSummary) -> CoordinatorVerification:
        return cls(
            terminal_state=summary.terminal_state,
            commands=tuple(
                VerificationRecord.from_command_result(result)
                for result in summary.results
            ),
        )


@dataclass(frozen=True, slots=True)
class ScopeViolation:
    path: str
    description: str


@dataclass(frozen=True, slots=True)
class UnresolvedRisk:
    risk_id: str
    description: str
    mitigation: str = ""


@dataclass(frozen=True, slots=True)
class EvidenceReport:
    """The sole typed source for both report representations."""

    mission: Mission
    baseline: Baseline
    original_invariant: OriginalInvariant
    agents: tuple[AgentRecord, ...]
    timeline: tuple[TimelineEvent, ...]
    knowledge_deliveries: tuple[KnowledgeDelivery, ...]
    artifacts: tuple[ArtifactRecord, ...]
    diff_hash: str
    review_evidence: tuple[EvidenceRecord, ...]
    tester_evidence: tuple[EvidenceRecord, ...]
    coordinator_verification: CoordinatorVerification
    scope_violations: tuple[ScopeViolation, ...] = ()
    unresolved_risks: tuple[UnresolvedRisk, ...] = ()
    log_limit_bytes: int = DEFAULT_LOG_LIMIT_BYTES

    def __post_init__(self) -> None:
        for field_name in (
            "agents",
            "timeline",
            "knowledge_deliveries",
            "artifacts",
            "review_evidence",
            "tester_evidence",
            "scope_violations",
            "unresolved_risks",
        ):
            object.__setattr__(self, field_name, tuple(getattr(self, field_name)))
        if self.log_limit_bytes < 0:
            raise ValueError("log_limit_bytes cannot be negative")

    @property
    def terminal_state(self) -> VerificationTerminalState:
        return self.coordinator_verification.terminal_state

    def to_dict(self) -> dict[str, Any]:
        return render_report(self)

    def to_markdown(self) -> str:
        return render_markdown(self)

    def to_json(self, *, indent: int | None = 2) -> str:
        return render_json(self, indent=indent)


def redact_text(value: str) -> str:
    """Remove common credential forms without requiring secret configuration."""
    redacted = value
    for index, pattern in enumerate(_SECRET_PATTERNS):
        if index == 0:
            redacted = pattern.sub(_REDACTED, redacted)
        elif index in {1, 2, 3}:
            redacted = pattern.sub(rf"\1{_REDACTED}", redacted)
        elif index == 5:
            redacted = pattern.sub(rf"\1{_REDACTED}\2", redacted)
        else:
            redacted = pattern.sub(_REDACTED, redacted)
    return redacted


def _bounded(value: str, limit: int) -> tuple[str, bool]:
    encoded = value.encode("utf-8")
    if len(encoded) <= limit:
        return value, False
    clipped = encoded[:limit].decode("utf-8", errors="ignore")
    return clipped, True


def _text(value: str) -> str:
    return redact_text(value)


def _log(value: str, limit: int) -> tuple[str, bool]:
    return _bounded(redact_text(value), limit)


def _evidence(record: EvidenceRecord, limit: int) -> dict[str, Any]:
    log, truncated = _log(record.log, limit)
    return {
        "source": _text(record.source),
        "summary": _text(record.summary),
        "log": log,
        "log_truncated": truncated,
    }


def _verification(record: VerificationRecord, limit: int) -> dict[str, Any]:
    stdout, stdout_capped = _log(record.stdout, limit)
    stderr, stderr_capped = _log(record.stderr, limit)
    return {
        "name": _text(record.name),
        "executable": _text(record.executable),
        "args": [_text(arg) for arg in record.args],
        "cwd": _text(record.cwd),
        "timeout_seconds": record.timeout_seconds,
        "required": record.required,
        "status": _text(record.status),
        "exit_code": record.exit_code,
        "duration_seconds": round(record.duration_seconds, 6),
        "stdout": stdout,
        "stderr": stderr,
        "command_sha256": _text(record.command_sha256),
        "stdout_sha256": _text(record.stdout_sha256),
        "stderr_sha256": _text(record.stderr_sha256),
        "stdout_truncated": record.stdout_truncated or stdout_capped,
        "stderr_truncated": record.stderr_truncated or stderr_capped,
    }


def render_report(report: EvidenceReport) -> dict[str, Any]:
    """Return a JSON-compatible report with stable ordering and redaction."""
    limit = report.log_limit_bytes
    agents = sorted(report.agents, key=lambda item: (item.agent_id, item.role))
    timeline = sorted(report.timeline, key=lambda item: (item.timestamp, item.event_id))
    deliveries = sorted(report.knowledge_deliveries, key=lambda item: item.delivery_id)
    artifacts = sorted(
        report.artifacts, key=lambda item: (item.application_order, item.path)
    )
    reviews = sorted(
        report.review_evidence, key=lambda item: (item.source, item.summary)
    )
    testers = sorted(
        report.tester_evidence, key=lambda item: (item.source, item.summary)
    )
    commands = sorted(
        report.coordinator_verification.commands,
        key=lambda item: (item.name, item.required, item.command_sha256),
    )
    violations = sorted(
        report.scope_violations, key=lambda item: (item.path, item.description)
    )
    risks = sorted(report.unresolved_risks, key=lambda item: item.risk_id)

    return {
        "mission": {
            "mission_id": _text(report.mission.mission_id),
            "objective": _text(report.mission.objective),
        },
        "baseline": {
            "revision": _text(report.baseline.revision),
            "summary": _text(report.baseline.summary),
        },
        "original_invariant": {"statement": _text(report.original_invariant.statement)},
        "agents": [
            {
                "agent_id": _text(item.agent_id),
                "role": _text(item.role),
                "outcome": _text(item.outcome),
            }
            for item in agents
        ],
        "timeline": [
            {
                "timestamp": _text(item.timestamp),
                "event_id": _text(item.event_id),
                "description": _text(item.description),
            }
            for item in timeline
        ],
        "knowledge_deliveries": [
            {
                "delivery_id": _text(item.delivery_id),
                "source_agent": _text(item.source_agent),
                "recipient_agent": _text(item.recipient_agent),
                "knowledge": _text(item.knowledge),
                "causal_uses": sorted(_text(use) for use in item.causal_uses),
            }
            for item in deliveries
        ],
        "artifacts": [
            {
                "path": _text(item.path),
                "sha256": _text(item.sha256),
                "application_order": item.application_order,
                "description": _text(item.description),
            }
            for item in artifacts
        ],
        "diff_hash": _text(report.diff_hash),
        "review_evidence": [_evidence(item, limit) for item in reviews],
        "tester_evidence": [_evidence(item, limit) for item in testers],
        "coordinator_verification": {
            "terminal_state": report.terminal_state.value,
            "commands": [_verification(item, limit) for item in commands],
        },
        "scope_violations": [
            {"path": _text(item.path), "description": _text(item.description)}
            for item in violations
        ],
        "terminal_state": report.terminal_state.value,
        "unresolved_risks": [
            {
                "risk_id": _text(item.risk_id),
                "description": _text(item.description),
                "mitigation": _text(item.mitigation),
            }
            for item in risks
        ],
    }


def render_json(report: EvidenceReport, *, indent: int | None = 2) -> str:
    """Render stable JSON (the JSON-compatible representation serialized)."""
    return json.dumps(
        render_report(report),
        ensure_ascii=False,
        indent=indent,
        separators=(",", ":") if indent is None else None,
    )


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, list):
        value = "; ".join(str(item) for item in value)
    return str(value).replace("|", "\\|").replace("\r", "").replace("\n", "<br>")


def _table(headers: tuple[str, ...], rows: list[tuple[Any, ...]]) -> list[str]:
    if not rows:
        return ["_None._"]
    return [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
        *("| " + " | ".join(_cell(value) for value in row) + " |" for row in rows),
    ]


def render_markdown(report: EvidenceReport) -> str:
    """Render Markdown exclusively from the canonical dict representation."""
    data = render_report(report)
    lines = [
        "# Evidence Report",
        "",
        "## Mission",
        f"- **ID:** {_cell(data['mission']['mission_id'])}",
        f"- **Objective:** {_cell(data['mission']['objective'])}",
        "",
        "## Baseline",
        f"- **Revision:** {_cell(data['baseline']['revision'])}",
        f"- **Summary:** {_cell(data['baseline']['summary'])}",
        "",
        "## Original Invariant",
        _cell(data["original_invariant"]["statement"]),
        "",
        "## Agents",
        *_table(
            ("Agent", "Role", "Outcome"),
            [
                (item["agent_id"], item["role"], item["outcome"])
                for item in data["agents"]
            ],
        ),
        "",
        "## Timeline",
        *_table(
            ("Timestamp", "Event", "Description"),
            [
                (item["timestamp"], item["event_id"], item["description"])
                for item in data["timeline"]
            ],
        ),
        "",
        "## Knowledge Deliveries and Causal Uses",
        *_table(
            ("Delivery", "Source", "Recipient", "Knowledge", "Causal uses"),
            [
                (
                    item["delivery_id"],
                    item["source_agent"],
                    item["recipient_agent"],
                    item["knowledge"],
                    item["causal_uses"],
                )
                for item in data["knowledge_deliveries"]
            ],
        ),
        "",
        "## Artifacts and Application Order",
        *_table(
            ("Order", "Path", "SHA-256", "Description"),
            [
                (
                    item["application_order"],
                    item["path"],
                    item["sha256"],
                    item["description"],
                )
                for item in data["artifacts"]
            ],
        ),
        "",
        "## Diff Hash",
        _cell(data["diff_hash"]),
        "",
        "## Review Evidence",
        *_table(
            ("Source", "Summary", "Log", "Truncated"),
            [
                (item["source"], item["summary"], item["log"], item["log_truncated"])
                for item in data["review_evidence"]
            ],
        ),
        "",
        "## Tester Evidence",
        *_table(
            ("Source", "Summary", "Log", "Truncated"),
            [
                (item["source"], item["summary"], item["log"], item["log_truncated"])
                for item in data["tester_evidence"]
            ],
        ),
        "",
        "## Coordinator Verification",
        "- **Terminal state:** "
        f"{_cell(data['coordinator_verification']['terminal_state'])}",
        *_table(
            (
                "Command",
                "Executable",
                "Arguments",
                "Working directory",
                "Timeout (s)",
                "Required",
                "Status",
                "Exit",
                "Duration (s)",
                "stdout",
                "stderr",
                "Command SHA-256",
                "stdout SHA-256",
                "stderr SHA-256",
                "stdout truncated",
                "stderr truncated",
            ),
            [
                (
                    item["name"],
                    item["executable"],
                    item["args"],
                    item["cwd"],
                    item["timeout_seconds"],
                    item["required"],
                    item["status"],
                    item["exit_code"],
                    item["duration_seconds"],
                    item["stdout"],
                    item["stderr"],
                    item["command_sha256"],
                    item["stdout_sha256"],
                    item["stderr_sha256"],
                    item["stdout_truncated"],
                    item["stderr_truncated"],
                )
                for item in data["coordinator_verification"]["commands"]
            ],
        ),
        "",
        "## Scope Violations",
        *_table(
            ("Path", "Description"),
            [(item["path"], item["description"]) for item in data["scope_violations"]],
        ),
        "",
        "## Terminal State",
        _cell(data["terminal_state"]),
        "",
        "## Unresolved Risks",
        *_table(
            ("Risk", "Description", "Mitigation"),
            [
                (item["risk_id"], item["description"], item["mitigation"])
                for item in data["unresolved_risks"]
            ],
        ),
        "",
    ]
    return "\n".join(lines)
