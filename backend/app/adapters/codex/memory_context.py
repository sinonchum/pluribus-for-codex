from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any, Protocol

from app.memory_runtime.matching import (
    build_context_packet,
    match_installed_memories,
)

from .adapter import AgentRunRequest


class AgentRunner(Protocol):
    async def run_agent(self, request: AgentRunRequest) -> Any: ...


def inject_memory_context(prompt: str, context_packet: str) -> str:
    """Append explicit installed-memory guidance to a rendered Codex prompt."""

    if not context_packet.strip():
        return prompt
    return "\n\n".join(
        (
            prompt.rstrip(),
            "## Installed Pluribus memory context",
            "Pluribus injects this explicit package for this task; it does not modify hidden Codex memory.",
            context_packet.strip(),
        )
    )


def augment_agent_run_request(
    request: AgentRunRequest,
    *,
    task_text: str,
    project_root: str | Path,
    max_context_chars: int = 6000,
    match_limit: int = 3,
) -> AgentRunRequest:
    """Return the real Codex execution request with matched memory injected."""

    rendered_prompt = build_memory_augmented_prompt(
        request.rendered_prompt,
        task_text=task_text,
        project_root=project_root,
        max_context_chars=max_context_chars,
        match_limit=match_limit,
    )
    return replace(request, rendered_prompt=rendered_prompt)


async def run_agent_with_memory(
    adapter: AgentRunner,
    request: AgentRunRequest,
    *,
    task_text: str,
    project_root: str | Path,
    max_context_chars: int = 6000,
    match_limit: int = 3,
) -> Any:
    """Run the existing adapter with an explicitly augmented request."""

    augmented = augment_agent_run_request(
        request,
        task_text=task_text,
        project_root=project_root,
        max_context_chars=max_context_chars,
        match_limit=match_limit,
    )
    return await adapter.run_agent(augmented)


def build_memory_augmented_prompt(
    prompt: str,
    *,
    task_text: str,
    project_root: str | Path,
    max_context_chars: int = 6000,
    match_limit: int = 3,
) -> str:
    """Match installed packages and append their bounded context to a prompt."""

    matches = match_installed_memories(
        project_root,
        task_text,
        limit=match_limit,
    )
    packet = build_context_packet(matches, max_chars=max_context_chars)
    return inject_memory_context(prompt, packet)
