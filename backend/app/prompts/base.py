"""Common deterministic prompt layout."""

from __future__ import annotations

from collections.abc import Iterable

from .models import PromptKnowledge, PromptRequest

OUTPUT_CONTRACT = """Return exactly one final JSON object between <PLURIBUS_HANDOFF> and </PLURIBUS_HANDOFF>.
Required keys: status, summary, changed_files, self_reported_commands, consumed_patch_ids,
knowledge_usage, knowledge_patches, and risks. Use only repository-relative paths.
Use this shape (empty arrays are valid):
{"status":"completed|failed|blocked|partial","summary":"...","changed_files":["path"],
"self_reported_commands":[{"command":"...","exit_code":0}],
"consumed_patch_ids":["kp_001"],
"knowledge_usage":[{"patch_id":"kp_001","effect":"causal explanation","changed_files":["path"]}],
"knowledge_patches":[{"type":"repository_fact","summary":"...","details":"...",
"evidence":[{"type":"file_reference","path":"path","line_start":1,"line_end":2}],
"tags":["tag"],"relevant_to":["builder"],"confidence":0.9}],"risks":["..."]}
Agent self-reported commands are claims, not Coordinator verification."""


def _lines(items: Iterable[str], *, empty: str = "(none)") -> str:
    values = tuple(items)
    return "\n".join(f"- {item}" for item in values) if values else empty


def _knowledge(items: Iterable[PromptKnowledge]) -> str:
    values = tuple(items)
    if not values:
        return "(none)"
    rendered: list[str] = []
    for item in values:
        rendered.append(f"- [{item.status}] {item.patch_id}: {item.summary}")
        rendered.extend(f"  Evidence: {reference}" for reference in item.evidence)
    return "\n".join(rendered)


def render_base_prompt(request: PromptRequest, role_instructions: str) -> str:
    """Render all common sections in a stable order."""

    execution_verified = tuple(
        item for item in request.hive_knowledge if item.status == "execution_verified"
    )
    source_linked = tuple(
        item for item in request.hive_knowledge if item.status != "execution_verified"
    )
    return f"""## Mission
{request.mission_objective}

## Agent identity
Mission ID: {request.mission_id}
Agent ID: {request.agent_id}

## Role
{request.role.value}

## Assigned task
{request.assigned_task}

## Repository baseline
{request.repository_baseline}

## Working directory
{request.working_directory}

## Verified Hive knowledge
{_knowledge(execution_verified)}

## Source-linked Hive knowledge
{_knowledge(source_linked)}

## Active constraints
{_lines(request.active_constraints)}

## Relevant risks
{_lines(request.relevant_risks)}

## Allowed paths
{_lines(request.allowed_paths)}

## Protected paths
{_lines(request.protected_paths)}

## Delivered patch IDs
{_lines(request.delivered_patch_ids)}

## Role-specific instructions
{role_instructions}

## Expected output contract
{OUTPUT_CONTRACT}
"""
