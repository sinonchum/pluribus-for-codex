"""Transparent deterministic Knowledge Patch relevance ranking."""

from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatch
import re

from backend.app.adapters.codex.models import KnowledgePatchType
from backend.app.prompts.models import AgentRole

from .models import ContextPacketRequest, KnowledgePatch, KnowledgeStatus

_TOKEN = re.compile(r"[a-z0-9_./-]+")
_EVIDENCE_STRENGTH = {
    KnowledgeStatus.EXECUTION_VERIFIED: 30,
    KnowledgeStatus.SOURCE_LINKED: 20,
    KnowledgeStatus.PROPOSED: 5,
    KnowledgeStatus.DISPUTED: -5,
    KnowledgeStatus.SUPERSEDED: -20,
    KnowledgeStatus.REJECTED: -1000,
}


def _tokens(*values: str) -> set[str]:
    return {token for value in values for token in _TOKEN.findall(value.lower())}


@dataclass(frozen=True, slots=True)
class RelevanceScore:
    patch_id: str
    role_relevance: int
    tag_overlap: int
    assigned_file_overlap: int
    task_dependency: int
    evidence_strength: int
    disputed_penalty: int

    @property
    def total(self) -> int:
        return (
            self.role_relevance
            + self.tag_overlap
            + self.assigned_file_overlap
            + self.task_dependency
            + self.evidence_strength
            + self.disputed_penalty
        )


@dataclass(frozen=True, slots=True)
class RankedPatch:
    patch: KnowledgePatch
    score: RelevanceScore


def score_patch(patch: KnowledgePatch, request: ContextPacketRequest) -> RelevanceScore:
    role_relevance = 40 if request.role.value in patch.relevant_to else 0
    requested_tags = _tokens(*request.task_tags, request.assigned_task)
    patch_tags = _tokens(*patch.tags)
    tag_overlap = 5 * len(requested_tags & patch_tags)
    evidence_paths = tuple(evidence.path for evidence in patch.evidence)
    assigned_file_overlap = 0
    for evidence_path in evidence_paths:
        if any(
            evidence_path == allowed.rstrip("/")
            or evidence_path.startswith(allowed.rstrip("/") + "/")
            or fnmatch(evidence_path, allowed)
            for allowed in request.allowed_paths
        ):
            assigned_file_overlap = 20
            break
    task_words = _tokens(request.assigned_task)
    patch_words = _tokens(patch.summary, patch.details)
    task_dependency = min(15, 3 * len(task_words & patch_words))
    return RelevanceScore(
        patch_id=patch.id,
        role_relevance=role_relevance,
        tag_overlap=tag_overlap,
        assigned_file_overlap=assigned_file_overlap,
        task_dependency=task_dependency,
        evidence_strength=_EVIDENCE_STRENGTH[patch.status],
        disputed_penalty=-25 if patch.status is KnowledgeStatus.DISPUTED else 0,
    )


def rank_patches(request: ContextPacketRequest) -> tuple[RankedPatch, ...]:
    eligible = (
        patch
        for patch in request.patches
        if patch.status is not KnowledgeStatus.REJECTED
        and (request.include_superseded or patch.status is not KnowledgeStatus.SUPERSEDED)
    )
    ranked = tuple(RankedPatch(patch, score_patch(patch, request)) for patch in eligible)
    return tuple(
        sorted(
            ranked,
            key=lambda item: (
                -item.score.total,
                -item.patch.confidence,
                item.patch.creation_sequence,
                item.patch.id,
            ),
        )
    )


def is_mandatory(patch: KnowledgePatch, role: AgentRole) -> bool:
    if patch.type is KnowledgePatchType.CONSTRAINT:
        return True
    if patch.type is KnowledgePatchType.DECISION and patch.status in (
        KnowledgeStatus.SOURCE_LINKED,
        KnowledgeStatus.EXECUTION_VERIFIED,
    ):
        return True
    if patch.type is KnowledgePatchType.RISK and (
        role.value in patch.relevant_to or not patch.relevant_to
    ):
        return True
    return False
