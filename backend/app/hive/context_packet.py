"""Role-specific, deterministic Context Packet compilation."""

from __future__ import annotations

from backend.app.prompts.models import PromptKnowledge

from .models import ContextPacket, ContextPacketRequest, KnowledgePatch
from .relevance import is_mandatory, rank_patches


def _render_patch(patch: KnowledgePatch) -> list[str]:
    lines = [f"- [{patch.status.value}] {patch.id} ({patch.type.value}): {patch.summary}"]
    if patch.details:
        lines.append(f"  Details: {patch.details}")
    for evidence in patch.evidence:
        lines.append(
            f"  Evidence: {evidence.path}:{evidence.line_start}-{evidence.line_end}"
        )
    if patch.status.value == "source_linked":
        lines.append("  Trust: source-linked; the interpretation is not independently verified.")
    return lines


def compile_context_packet(request: ContextPacketRequest) -> ContextPacket:
    """Select patches, record their exact IDs, and render trust labels."""

    if request.max_patches < 0:
        raise ValueError("max_patches must not be negative.")
    ranked = rank_patches(request)
    mandatory = [item.patch for item in ranked if is_mandatory(item.patch, request.role)]
    optional = [item.patch for item in ranked if item.patch not in mandatory]
    remaining = max(0, request.max_patches - len(mandatory))
    included = tuple(mandatory + optional[:remaining])
    knowledge_lines = [line for patch in included for line in _render_patch(patch)]
    rendered = "\n".join(
        (
            "## Mission",
            request.mission_objective,
            "",
            "## Assigned task",
            request.assigned_task,
            "",
            "## Repository baseline",
            request.baseline_commit,
            "",
            "## Working directory",
            str(request.working_directory),
            "",
            "## Active constraints",
            *(f"- {constraint}" for constraint in request.active_constraints),
            "",
            "## Hive knowledge",
            *(knowledge_lines or ["(none)"]),
            "",
            "## Allowed paths",
            *(f"- {path}" for path in request.allowed_paths),
            "",
            "## Protected paths",
            *(f"- {path}" for path in request.protected_paths),
        )
    )
    return ContextPacket(
        mission_id=request.mission_id,
        agent_id=request.agent_id,
        role=request.role,
        rendered_text=rendered,
        delivered_patch_ids=tuple(patch.id for patch in included),
        included_patches=included,
    )


def packet_prompt_knowledge(packet: ContextPacket) -> tuple[PromptKnowledge, ...]:
    """Adapt a packet to the prompt module without a shared persistence model."""

    return tuple(
        PromptKnowledge(
            patch_id=patch.id,
            status=patch.status.value,
            summary=patch.summary,
            evidence=tuple(
                f"{item.path}:{item.line_start}-{item.line_end}" for item in patch.evidence
            ),
        )
        for patch in packet.included_patches
    )
