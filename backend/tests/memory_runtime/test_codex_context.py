from __future__ import annotations

import asyncio
from pathlib import Path

from app.adapters.codex import AgentRunRequest
from app.adapters.codex.memory_context import (
    augment_agent_run_request,
    build_memory_augmented_prompt,
    inject_memory_context,
    run_agent_with_memory,
)
from app.memory_runtime.store import install_memory
from app.prompts import AgentRole


def test_inject_memory_context_appends_explicit_bounded_section() -> None:
    prompt = "Fix the failing tests."
    packet = "Memory ID: mem_example_v1\nSteps:\n1. Run the suite."

    rendered = inject_memory_context(prompt, packet)

    assert rendered.startswith(prompt)
    assert "## Installed Pluribus memory context" in rendered
    assert packet in rendered
    assert "does not modify hidden Codex memory" in rendered


def test_empty_memory_packet_leaves_prompt_unchanged() -> None:
    assert inject_memory_context("Original prompt", "") == "Original prompt"


def test_build_memory_augmented_prompt_matches_installed_memory(
    tmp_path: Path, capsule: dict[str, object]
) -> None:
    install_memory(tmp_path, capsule)

    rendered = build_memory_augmented_prompt(
        "Fix this test failure.",
        task_text="pytest reports import file mismatch",
        project_root=tmp_path,
    )

    assert "Fix this test failure." in rendered
    assert "mem_pytest_importlib_v1" in rendered
    assert "--import-mode=importlib" in rendered


def test_augment_agent_run_request_connects_memory_to_codex_execution_contract(
    tmp_path: Path, capsule: dict[str, object]
) -> None:
    install_memory(tmp_path, capsule)
    request = AgentRunRequest(
        mission_id="memory_demo",
        agent_id="builder_1",
        role=AgentRole.BUILDER,
        rendered_prompt="Fix this test failure.",
        working_directory=tmp_path,
    )

    augmented = augment_agent_run_request(
        request,
        task_text="pytest reports import file mismatch",
        project_root=tmp_path,
    )

    assert augmented is not request
    assert augmented.mission_id == request.mission_id
    assert augmented.working_directory == request.working_directory
    assert "mem_pytest_importlib_v1" in augmented.rendered_prompt
    assert "--import-mode=importlib" in augmented.rendered_prompt
    assert request.rendered_prompt == "Fix this test failure."


def test_run_agent_with_memory_passes_augmented_prompt_to_real_adapter_contract(
    tmp_path: Path, capsule: dict[str, object]
) -> None:
    class RecordingAdapter:
        def __init__(self) -> None:
            self.request: AgentRunRequest | None = None

        async def run_agent(self, request: AgentRunRequest) -> str:
            self.request = request
            return "completed"

    install_memory(tmp_path, capsule)
    request = AgentRunRequest(
        mission_id="memory_demo",
        agent_id="builder_1",
        role=AgentRole.BUILDER,
        rendered_prompt="Fix this test failure.",
        working_directory=tmp_path,
    )
    adapter = RecordingAdapter()

    result = asyncio.run(
        run_agent_with_memory(
            adapter,
            request,
            task_text="pytest reports import file mismatch",
            project_root=tmp_path,
        )
    )

    assert result == "completed"
    assert adapter.request is not None
    assert "mem_pytest_importlib_v1" in adapter.request.rendered_prompt
