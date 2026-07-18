"""Evidence validation without coupling to Git orchestration internals."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Protocol

from backend.app.adapters.codex.models import EvidenceType, validate_relative_path

from .models import KnowledgePatch, KnowledgeStatus, KnowledgeValidationResult


class EvidenceResolver(Protocol):
    async def file_exists_at_baseline(
        self, repository_path: Path, baseline_commit: str, relative_path: str
    ) -> bool: ...

    async def read_file_at_baseline(
        self, repository_path: Path, baseline_commit: str, relative_path: str
    ) -> str | None: ...


class FilesystemEvidenceResolver:
    """Validate against a checked-out tree supplied as the recorded baseline."""

    @staticmethod
    def _safe_target(repository_path: Path, relative_path: str) -> Path:
        normalized = validate_relative_path(relative_path, "evidence.path")
        root = repository_path.resolve()
        target = (root / normalized).resolve()
        if target != root and root not in target.parents:
            raise ValueError("Evidence path escapes the repository.")
        return target

    async def file_exists_at_baseline(
        self, repository_path: Path, baseline_commit: str, relative_path: str
    ) -> bool:
        del baseline_commit
        return self._safe_target(repository_path, relative_path).is_file()

    async def read_file_at_baseline(
        self, repository_path: Path, baseline_commit: str, relative_path: str
    ) -> str | None:
        del baseline_commit
        target = self._safe_target(repository_path, relative_path)
        if not target.is_file():
            return None
        return target.read_text(encoding="utf-8", errors="replace")


async def validate_knowledge_patch(
    patch: KnowledgePatch,
    repository_path: Path,
    resolver: EvidenceResolver,
    *,
    source_linking_requested: bool = True,
    coordinator_execution_verified: bool = False,
) -> KnowledgeValidationResult:
    """Validate evidence and return a legitimate trust-state transition."""

    errors: list[str] = []
    warnings: list[str] = []
    resulting_status = patch.status
    if patch.status is KnowledgeStatus.EXECUTION_VERIFIED and not coordinator_execution_verified:
        errors.append("Agent output cannot mark a patch execution_verified.")
        resulting_status = KnowledgeStatus.PROPOSED
    if patch.status in (KnowledgeStatus.REJECTED, KnowledgeStatus.SUPERSEDED):
        if source_linking_requested:
            errors.append(f"Cannot source-link a {patch.status.value} patch.")
        return KnowledgeValidationResult(False, patch.status, tuple(errors), tuple(warnings))
    if not source_linking_requested:
        return KnowledgeValidationResult(not errors, resulting_status, tuple(errors), tuple(warnings))
    if not patch.baseline_commit:
        errors.append("baseline_commit is required for source-linked evidence.")
    if not patch.evidence:
        warnings.append("Patch has no file evidence and remains proposed.")
        return KnowledgeValidationResult(not errors, KnowledgeStatus.PROPOSED, tuple(errors), tuple(warnings))

    for index, evidence in enumerate(patch.evidence):
        prefix = f"evidence[{index}]"
        if evidence.type != EvidenceType.FILE_REFERENCE:
            errors.append(f"{prefix} has unsupported evidence type {evidence.type!r}.")
            continue
        try:
            relative_path = validate_relative_path(evidence.path, f"{prefix}.path")
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if evidence.line_start <= 0 or evidence.line_end < evidence.line_start:
            errors.append(f"{prefix} has an invalid line range.")
            continue
        if not patch.baseline_commit:
            continue
        if not await resolver.file_exists_at_baseline(
            repository_path, patch.baseline_commit, relative_path
        ):
            errors.append(f"{prefix} file does not exist at the recorded baseline: {relative_path}.")
            continue
        content = await resolver.read_file_at_baseline(
            repository_path, patch.baseline_commit, relative_path
        )
        if content is None:
            errors.append(f"{prefix} file could not be read at the recorded baseline: {relative_path}.")
            continue
        line_count = len(content.splitlines())
        if evidence.line_end > line_count:
            errors.append(
                f"{prefix} line range ends at {evidence.line_end}, but {relative_path} has {line_count} lines."
            )

    if errors:
        return KnowledgeValidationResult(False, KnowledgeStatus.PROPOSED, tuple(errors), tuple(warnings))
    if patch.status is KnowledgeStatus.DISPUTED:
        warnings.append("Evidence is valid, but a disputed patch is not promoted automatically.")
        return KnowledgeValidationResult(True, KnowledgeStatus.DISPUTED, (), tuple(warnings))
    if coordinator_execution_verified:
        return KnowledgeValidationResult(True, KnowledgeStatus.EXECUTION_VERIFIED, (), tuple(warnings))
    # This links the claim to source; it does not certify the agent's interpretation.
    return KnowledgeValidationResult(True, KnowledgeStatus.SOURCE_LINKED, (), tuple(warnings))


def with_validation_status(
    patch: KnowledgePatch, validation: KnowledgeValidationResult
) -> KnowledgePatch:
    return replace(patch, status=validation.resulting_status)
