"""Validation of causal, cross-agent knowledge consumption."""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass

from app.adapters.codex.models import AgentHandoff
from app.prompts.models import AgentRole


@dataclass(frozen=True, slots=True)
class PatchDelivery:
    mission_id: str
    agent_id: str
    patch_id: str
    role: AgentRole


@dataclass(frozen=True, slots=True)
class PatchConsumption:
    mission_id: str
    agent_id: str
    patch_id: str
    effect: str
    changed_files: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ConsumptionValidationResult:
    valid: bool
    consumptions: tuple[PatchConsumption, ...]
    unknown_patch_ids: tuple[str, ...]
    consumed_without_usage: tuple[str, ...]
    usage_without_consumed_flag: tuple[str, ...]
    errors: tuple[str, ...]
    warnings: tuple[str, ...]


class KnowledgeConsumptionTracker:
    """Turn delivered IDs and a handoff into persistence-ready causal records."""

    def validate_handoff_consumption(
        self,
        delivered_patch_ids: Collection[str],
        handoff: AgentHandoff,
        *,
        mission_id: str = "",
        agent_id: str = "",
        role: AgentRole | None = None,
    ) -> ConsumptionValidationResult:
        delivered = set(delivered_patch_ids)
        consumed = tuple(dict.fromkeys(handoff.consumed_patch_ids))
        consumed_set = set(consumed)
        unknown = tuple(sorted(consumed_set - delivered))
        usage_by_id = {}
        duplicate_usage: list[str] = []
        for usage in handoff.knowledge_usage:
            if usage.patch_id in usage_by_id:
                duplicate_usage.append(usage.patch_id)
                continue
            usage_by_id[usage.patch_id] = usage
        usage_without_flag = tuple(sorted(set(usage_by_id) - consumed_set))
        consumed_without_usage = tuple(sorted(consumed_set - set(usage_by_id)))
        errors: list[str] = []
        warnings: list[str] = []
        if unknown:
            errors.append(
                "Consumed patch IDs were not delivered: " + ", ".join(unknown)
            )
        if usage_without_flag:
            errors.append(
                "knowledge_usage IDs are missing consumed flags: "
                + ", ".join(usage_without_flag)
            )
        if consumed_without_usage:
            errors.append(
                "Consumed patch IDs lack causal usage: "
                + ", ".join(consumed_without_usage)
            )
        if duplicate_usage:
            warnings.append(
                "Duplicate knowledge_usage records ignored after the first: "
                + ", ".join(sorted(set(duplicate_usage)))
            )
        records: list[PatchConsumption] = []
        for patch_id in consumed:
            usage = usage_by_id.get(patch_id)
            if usage is None or patch_id not in delivered:
                continue
            if not usage.effect.strip():
                errors.append(
                    f"Knowledge usage for {patch_id} has no causal explanation."
                )
                continue
            if (
                role is AgentRole.BUILDER
                and handoff.changed_files
                and not usage.changed_files
            ):
                warnings.append(
                    f"Builder usage for {patch_id} does not name an affected changed file."
                )
            unrelated_files = tuple(
                path
                for path in usage.changed_files
                if path not in handoff.changed_files
            )
            if unrelated_files:
                warnings.append(
                    f"Knowledge usage for {patch_id} names files outside changed_files: "
                    + ", ".join(unrelated_files)
                )
            records.append(
                PatchConsumption(
                    mission_id=mission_id,
                    agent_id=agent_id,
                    patch_id=patch_id,
                    effect=usage.effect,
                    changed_files=usage.changed_files,
                )
            )
        return ConsumptionValidationResult(
            valid=not errors,
            consumptions=tuple(records),
            unknown_patch_ids=unknown,
            consumed_without_usage=consumed_without_usage,
            usage_without_consumed_flag=usage_without_flag,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )
