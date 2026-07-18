"""Local Hive contracts at the persistence and orchestration boundary."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from app.adapters.codex.models import (
    EvidenceReference,
    KnowledgePatchType,
    normalize_patch_id,
)
from app.prompts.models import AgentRole


class KnowledgeStatus(str, Enum):
    PROPOSED = "proposed"
    SOURCE_LINKED = "source_linked"
    EXECUTION_VERIFIED = "execution_verified"
    DISPUTED = "disputed"
    SUPERSEDED = "superseded"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class KnowledgePatch:
    id: str
    mission_id: str
    agent_id: str
    type: KnowledgePatchType
    summary: str
    details: str
    evidence: tuple[EvidenceReference, ...]
    tags: tuple[str, ...]
    relevant_to: tuple[str, ...]
    confidence: float
    status: KnowledgeStatus = KnowledgeStatus.PROPOSED
    baseline_commit: str | None = None
    creation_sequence: int = 0

    def __post_init__(self) -> None:
        normalized = normalize_patch_id(self.id, "KnowledgePatch.id")
        if normalized != self.id:
            raise ValueError("KnowledgePatch.id must already be normalized.")
        if not self.mission_id.strip() or not self.agent_id.strip():
            raise ValueError(
                "KnowledgePatch mission_id and agent_id must not be empty."
            )
        if not self.summary.strip():
            raise ValueError("KnowledgePatch summary must not be empty.")
        if not 0 <= self.confidence <= 1:
            raise ValueError("KnowledgePatch confidence must be between 0 and 1.")


@dataclass(frozen=True, slots=True)
class KnowledgeValidationResult:
    valid: bool
    resulting_status: KnowledgeStatus
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ValidatedKnowledgePatch:
    patch: KnowledgePatch
    validation: KnowledgeValidationResult


@dataclass(frozen=True, slots=True)
class ContextPacketRequest:
    mission_id: str
    agent_id: str
    role: AgentRole
    mission_objective: str
    assigned_task: str
    baseline_commit: str
    working_directory: Path
    allowed_paths: tuple[str, ...]
    protected_paths: tuple[str, ...]
    active_constraints: tuple[str, ...]
    patches: tuple[KnowledgePatch, ...]
    max_patches: int = 20
    task_tags: tuple[str, ...] = ()
    include_superseded: bool = False


@dataclass(frozen=True, slots=True)
class ContextPacket:
    mission_id: str
    agent_id: str
    role: AgentRole
    rendered_text: str
    delivered_patch_ids: tuple[str, ...]
    included_patches: tuple[KnowledgePatch, ...]
