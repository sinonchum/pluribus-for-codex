"""Public role-aware prompt renderer."""

from __future__ import annotations

from .base import render_base_prompt
from .builder import INSTRUCTIONS as BUILDER_INSTRUCTIONS
from .models import AgentRole, PromptRequest
from .reviewer import INSTRUCTIONS as REVIEWER_INSTRUCTIONS
from .scout import INSTRUCTIONS as SCOUT_INSTRUCTIONS
from .tester import INSTRUCTIONS as TESTER_INSTRUCTIONS

_INSTRUCTIONS = {
    AgentRole.SCOUT: SCOUT_INSTRUCTIONS,
    AgentRole.BUILDER: BUILDER_INSTRUCTIONS,
    AgentRole.TESTER: TESTER_INSTRUCTIONS,
    AgentRole.REVIEWER: REVIEWER_INSTRUCTIONS,
}


def render_prompt(request: PromptRequest) -> str:
    """Render a deterministic prompt for the selected role."""

    return render_base_prompt(request, _INSTRUCTIONS[request.role])
