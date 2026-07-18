"""Small validation facade designed for later persistence integration."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from backend.app.adapters.codex.models import KnowledgePatchInput

from .models import KnowledgePatch, KnowledgeStatus, ValidatedKnowledgePatch
from .validation import EvidenceResolver, validate_knowledge_patch, with_validation_status


class HiveService:
    """Assign IDs and validate agent-proposed patches without storing them."""

    def __init__(
        self,
        resolver: EvidenceResolver,
        *,
        patch_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._resolver = resolver
        self._sequence = 0
        self._patch_id_factory = patch_id_factory

    def _next_id(self) -> str:
        self._sequence += 1
        return (
            self._patch_id_factory()
            if self._patch_id_factory is not None
            else f"kp_{self._sequence:03d}"
        )

    async def validate_patch_input(
        self,
        patch_input: KnowledgePatchInput,
        *,
        mission_id: str,
        agent_id: str,
        repository_path: Path,
        baseline_commit: str,
        source_linking_requested: bool = True,
    ) -> ValidatedKnowledgePatch:
        patch = KnowledgePatch(
            id=self._next_id(),
            mission_id=mission_id,
            agent_id=agent_id,
            type=patch_input.type,
            summary=patch_input.summary,
            details=patch_input.details,
            evidence=patch_input.evidence,
            tags=patch_input.tags,
            relevant_to=patch_input.relevant_to,
            confidence=patch_input.confidence,
            status=KnowledgeStatus.PROPOSED,
            baseline_commit=baseline_commit,
            creation_sequence=self._sequence,
        )
        validation = await validate_knowledge_patch(
            patch,
            repository_path,
            self._resolver,
            source_linking_requested=source_linking_requested,
        )
        return ValidatedKnowledgePatch(with_validation_status(patch, validation), validation)
