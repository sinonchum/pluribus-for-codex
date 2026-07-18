"""High-level Codex facade for future orchestration callers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.hive.consumption import (
    ConsumptionValidationResult,
    KnowledgeConsumptionTracker,
)
from app.hive.models import ValidatedKnowledgePatch
from app.hive.service import HiveService
from app.prompts.models import AgentRole

from .config import CodexConfig
from .models import AgentHandoff, CodexPreflightResult, CodexRunRequest, CodexRunResult
from .preflight import run_preflight
from .runner import CodexRunner


@dataclass(frozen=True, slots=True)
class AgentRunRequest:
    mission_id: str
    agent_id: str
    role: AgentRole
    rendered_prompt: str
    working_directory: Path
    delivered_patch_ids: tuple[str, ...] = ()
    timeout_seconds: float | None = None
    baseline_commit: str = ""
    extra_args: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AgentRunOutcome:
    process_result: CodexRunResult
    parsed_handoff: AgentHandoff | None
    parsed: bool
    validated_new_patches: tuple[ValidatedKnowledgePatch, ...]
    consumption_validation: ConsumptionValidationResult | None
    errors: tuple[str, ...]

    @property
    def stdout(self) -> str:
        return self.process_result.stdout

    @property
    def stderr(self) -> str:
        return self.process_result.stderr


class CodexAdapter:
    """Run preflight/agent turns while leaving storage and Git truth to callers."""

    def __init__(
        self,
        config: CodexConfig | None = None,
        *,
        runner: CodexRunner | None = None,
        hive_service: HiveService | None = None,
        consumption_tracker: KnowledgeConsumptionTracker | None = None,
    ) -> None:
        self.config = config or CodexConfig.from_environment()
        self._runner = runner or CodexRunner(self.config)
        self._hive_service = hive_service
        self._consumption_tracker = consumption_tracker or KnowledgeConsumptionTracker()

    async def preflight(self) -> CodexPreflightResult:
        return await run_preflight(self.config)

    async def run_agent(self, request: AgentRunRequest) -> AgentRunOutcome:
        result = await self._runner.run(
            CodexRunRequest(
                prompt=request.rendered_prompt,
                working_directory=request.working_directory,
                timeout_seconds=request.timeout_seconds
                if request.timeout_seconds is not None
                else self.config.default_timeout_seconds,
                role=request.role.value,
                mission_id=request.mission_id,
                agent_id=request.agent_id,
                extra_args=request.extra_args,
            )
        )
        errors: list[str] = []
        if result.start_error:
            errors.append(result.start_error)
        if result.timed_out:
            errors.append("Codex turn timed out before completion.")
        if result.cancelled:
            errors.append("Codex turn was cancelled.")
        if result.exit_code not in (None, 0):
            errors.append(f"Codex turn exited with code {result.exit_code}.")
        if result.parse_error:
            errors.append(result.parse_error)

        validated: list[ValidatedKnowledgePatch] = []
        handoff = result.structured_handoff
        if handoff is not None and self._hive_service is not None:
            for patch_input in handoff.knowledge_patches:
                item = await self._hive_service.validate_patch_input(
                    patch_input,
                    mission_id=request.mission_id,
                    agent_id=request.agent_id,
                    repository_path=request.working_directory,
                    baseline_commit=request.baseline_commit,
                    source_linking_requested=not result.timed_out
                    and not result.cancelled,
                )
                validated.append(item)
                errors.extend(item.validation.errors)

        consumption = None
        if handoff is not None:
            consumption = self._consumption_tracker.validate_handoff_consumption(
                request.delivered_patch_ids,
                handoff,
                mission_id=request.mission_id,
                agent_id=request.agent_id,
                role=request.role,
            )
            errors.extend(consumption.errors)
        return AgentRunOutcome(
            process_result=result,
            parsed_handoff=handoff,
            parsed=handoff is not None,
            validated_new_patches=tuple(validated),
            consumption_validation=consumption,
            errors=tuple(errors),
        )
