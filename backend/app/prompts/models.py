"""Inputs shared by deterministic role prompt renderers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AgentRole(str, Enum):
    SCOUT = "scout"
    BUILDER = "builder"
    TESTER = "tester"
    REVIEWER = "reviewer"


@dataclass(frozen=True, slots=True)
class PromptKnowledge:
    patch_id: str
    status: str
    summary: str
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PromptRequest:
    mission_id: str
    agent_id: str
    role: AgentRole
    mission_objective: str
    assigned_task: str
    repository_baseline: str
    working_directory: str
    hive_knowledge: tuple[PromptKnowledge, ...] = ()
    active_constraints: tuple[str, ...] = ()
    relevant_risks: tuple[str, ...] = ()
    allowed_paths: tuple[str, ...] = ()
    protected_paths: tuple[str, ...] = ()
    delivered_patch_ids: tuple[str, ...] = ()
