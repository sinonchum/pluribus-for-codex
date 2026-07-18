"""Typed process and agent-handoff contracts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any


class AgentStatus(str, Enum):
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    PARTIAL = "partial"


class EvidenceType(str, Enum):
    FILE_REFERENCE = "file_reference"


class KnowledgePatchType(str, Enum):
    REPOSITORY_FACT = "repository_fact"
    CONSTRAINT = "constraint"
    DECISION = "decision"
    HYPOTHESIS = "hypothesis"
    RISK = "risk"
    TEST_RESULT = "test_result"
    CANDIDATE_PATCH = "candidate_patch"
    CONFLICT = "conflict"
    TASK_UPDATE = "task_update"


_PATCH_ID = re.compile(r"[a-z][a-z0-9_-]*\Z")


def normalize_patch_id(value: Any, field_name: str = "patch_id") -> str:
    """Normalize and validate a stable Knowledge Patch identifier."""

    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")
    normalized = value.strip().lower()
    if not _PATCH_ID.fullmatch(normalized):
        raise ValueError(
            f"{field_name} must contain only lowercase letters, digits, underscores, or hyphens."
        )
    return normalized


def validate_relative_path(value: Any, field_name: str = "path") -> str:
    """Return a normalized repository-relative path or raise ``ValueError``."""

    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")
    candidate = value.replace("\\", "/")
    posix = PurePosixPath(candidate)
    if posix.is_absolute() or PureWindowsPath(value).is_absolute():
        raise ValueError(f"{field_name} must be repository-relative: {value!r}.")
    if any(part == ".." for part in posix.parts):
        raise ValueError(f"{field_name} must not contain path traversal: {value!r}.")
    if any(part in ("", ".") for part in posix.parts):
        raise ValueError(f"{field_name} must be normalized: {value!r}.")
    return posix.as_posix()


def _required_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string.")
    return value.strip()


def _string_tuple(data: dict[str, Any], key: str) -> tuple[str, ...]:
    value = data.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{key} must be an array of strings.")
    return tuple(item for item in value if item)


def _role_tuple(data: dict[str, Any], key: str) -> tuple[str, ...]:
    values = _string_tuple(data, key)
    allowed = {"scout", "builder", "tester", "reviewer"}
    unknown = sorted(set(values) - allowed)
    if unknown:
        raise ValueError(f"{key} contains unknown agent roles: {', '.join(unknown)}.")
    return values


@dataclass(frozen=True, slots=True)
class EvidenceReference:
    type: EvidenceType | str
    path: str
    line_start: int
    line_end: int

    @classmethod
    def from_dict(cls, data: Any) -> EvidenceReference:
        if not isinstance(data, dict):
            raise ValueError("Evidence must be an object.")
        try:
            evidence_type = EvidenceType(data.get("type"))
        except ValueError as exc:
            raise ValueError(f"Unknown evidence type: {data.get('type')!r}.") from exc
        path = validate_relative_path(data.get("path"), "evidence.path")
        line_start = data.get("line_start")
        line_end = data.get("line_end")
        if (
            isinstance(line_start, bool)
            or not isinstance(line_start, int)
            or line_start <= 0
        ):
            raise ValueError("evidence.line_start must be a positive integer.")
        if isinstance(line_end, bool) or not isinstance(line_end, int) or line_end <= 0:
            raise ValueError("evidence.line_end must be a positive integer.")
        if line_end < line_start:
            raise ValueError(
                "evidence.line_end must be greater than or equal to line_start."
            )
        return cls(evidence_type, path, line_start, line_end)


@dataclass(frozen=True, slots=True)
class KnowledgePatchInput:
    type: KnowledgePatchType
    summary: str
    details: str
    evidence: tuple[EvidenceReference, ...]
    tags: tuple[str, ...]
    relevant_to: tuple[str, ...]
    confidence: float

    @classmethod
    def from_dict(cls, data: Any) -> KnowledgePatchInput:
        if not isinstance(data, dict):
            raise ValueError("Knowledge patch must be an object.")
        try:
            patch_type = KnowledgePatchType(data.get("type"))
        except ValueError as exc:
            raise ValueError(
                f"Unknown knowledge patch type: {data.get('type')!r}."
            ) from exc
        confidence = data.get("confidence")
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            raise ValueError("confidence must be a number between 0 and 1.")
        if not 0 <= float(confidence) <= 1:
            raise ValueError("confidence must be between 0 and 1.")
        details = data.get("details", "")
        if not isinstance(details, str):
            raise ValueError("details must be a string.")
        evidence = data.get("evidence", [])
        if not isinstance(evidence, list):
            raise ValueError("evidence must be an array.")
        return cls(
            type=patch_type,
            summary=_required_string(data, "summary"),
            details=details,
            evidence=tuple(EvidenceReference.from_dict(item) for item in evidence),
            tags=_string_tuple(data, "tags"),
            relevant_to=_role_tuple(data, "relevant_to"),
            confidence=float(confidence),
        )


@dataclass(frozen=True, slots=True)
class SelfReportedCommand:
    command: str
    exit_code: int | None

    @classmethod
    def from_dict(cls, data: Any) -> SelfReportedCommand:
        if not isinstance(data, dict):
            raise ValueError("Self-reported command must be an object.")
        command = _required_string(data, "command")
        exit_code = data.get("exit_code")
        if exit_code is not None and (
            isinstance(exit_code, bool) or not isinstance(exit_code, int)
        ):
            raise ValueError(
                "self_reported_commands.exit_code must be an integer or null."
            )
        return cls(command, exit_code)


@dataclass(frozen=True, slots=True)
class KnowledgeUsage:
    patch_id: str
    effect: str
    changed_files: tuple[str, ...]

    @classmethod
    def from_dict(cls, data: Any) -> KnowledgeUsage:
        if not isinstance(data, dict):
            raise ValueError("Knowledge usage must be an object.")
        changed_files = _string_tuple(data, "changed_files")
        return cls(
            patch_id=normalize_patch_id(data.get("patch_id")),
            effect=_required_string(data, "effect"),
            changed_files=tuple(
                validate_relative_path(path, "knowledge_usage.changed_files")
                for path in changed_files
            ),
        )


@dataclass(frozen=True, slots=True)
class AgentHandoff:
    status: AgentStatus
    summary: str
    changed_files: tuple[str, ...] = ()
    self_reported_commands: tuple[SelfReportedCommand, ...] = ()
    consumed_patch_ids: tuple[str, ...] = ()
    knowledge_usage: tuple[KnowledgeUsage, ...] = ()
    knowledge_patches: tuple[KnowledgePatchInput, ...] = ()
    risks: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, data: Any) -> AgentHandoff:
        if not isinstance(data, dict):
            raise ValueError("Agent handoff must be a JSON object.")
        try:
            status = AgentStatus(data.get("status"))
        except ValueError as exc:
            raise ValueError(
                f"Unknown handoff status: {data.get('status')!r}."
            ) from exc
        changed_files = tuple(
            validate_relative_path(path, "changed_files")
            for path in _string_tuple(data, "changed_files")
        )
        command_data = data.get("self_reported_commands", data.get("commands_run", []))
        if not isinstance(command_data, list):
            raise ValueError("self_reported_commands must be an array.")
        patch_data = data.get("knowledge_patches", [])
        usage_data = data.get("knowledge_usage", [])
        if not isinstance(patch_data, list) or not isinstance(usage_data, list):
            raise ValueError("knowledge_patches and knowledge_usage must be arrays.")
        consumed = _string_tuple(data, "consumed_patch_ids")
        normalized_consumed = tuple(
            dict.fromkeys(
                normalize_patch_id(item, "consumed_patch_ids") for item in consumed
            )
        )
        usage = tuple(KnowledgeUsage.from_dict(item) for item in usage_data)
        missing_flags = sorted(
            {item.patch_id for item in usage} - set(normalized_consumed)
        )
        if missing_flags:
            raise ValueError(
                "knowledge_usage patch IDs must appear in consumed_patch_ids: "
                + ", ".join(missing_flags)
            )
        return cls(
            status=status,
            summary=_required_string(data, "summary"),
            changed_files=changed_files,
            self_reported_commands=tuple(
                SelfReportedCommand.from_dict(item) for item in command_data
            ),
            consumed_patch_ids=normalized_consumed,
            knowledge_usage=usage,
            knowledge_patches=tuple(
                KnowledgePatchInput.from_dict(item) for item in patch_data
            ),
            risks=_string_tuple(data, "risks"),
        )


@dataclass(frozen=True, slots=True)
class HandoffParseResult:
    handoff: AgentHandoff | None
    parsed: bool
    raw_output: str
    raw_payload: str | None = None
    extraction_method: str | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class CodexPreflightResult:
    available: bool
    executable: str | None
    version: str | None
    probe_succeeded: bool
    exit_code: int | None
    duration_seconds: float
    stdout: str
    stderr: str
    error_code: str | None
    error_message: str | None


@dataclass(frozen=True, slots=True)
class CodexRunRequest:
    prompt: str
    working_directory: Path
    timeout_seconds: float
    role: str
    mission_id: str
    agent_id: str
    extra_args: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CodexRunResult:
    command: tuple[str, ...]
    working_directory: str
    role: str
    mission_id: str
    agent_id: str
    started_at: datetime
    finished_at: datetime
    duration_seconds: float
    exit_code: int | None
    timed_out: bool
    cancelled: bool
    stdout: str
    stderr: str
    stdout_truncated: bool
    stderr_truncated: bool
    structured_handoff: AgentHandoff | None
    parse_error: str | None
    start_error: str | None = None
