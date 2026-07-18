"""Public Codex adapter contracts."""

from .adapter import AgentRunOutcome, AgentRunRequest, CodexAdapter
from .config import CodexConfig
from .errors import (
    CodexAuthenticationError,
    CodexCancelledError,
    CodexError,
    CodexExecutableNotFoundError,
    CodexMalformedOutputError,
    CodexNonZeroExitError,
    CodexProbeError,
    CodexStartError,
    CodexTimeoutError,
)
from .models import (
    AgentHandoff,
    AgentStatus,
    CodexPreflightResult,
    CodexRunRequest,
    CodexRunResult,
    EvidenceReference,
    EvidenceType,
    HandoffParseResult,
    KnowledgePatchInput,
    KnowledgePatchType,
    KnowledgeUsage,
    SelfReportedCommand,
)
from .parser import parse_handoff
from .preflight import build_preflight_args, run_preflight
from .runner import CodexRunner, build_agent_args

__all__ = [
    "AgentHandoff",
    "AgentRunOutcome",
    "AgentRunRequest",
    "AgentStatus",
    "CodexAdapter",
    "CodexAuthenticationError",
    "CodexCancelledError",
    "CodexConfig",
    "CodexError",
    "CodexExecutableNotFoundError",
    "CodexMalformedOutputError",
    "CodexNonZeroExitError",
    "CodexPreflightResult",
    "CodexRunRequest",
    "CodexRunResult",
    "CodexRunner",
    "CodexProbeError",
    "CodexStartError",
    "CodexTimeoutError",
    "EvidenceReference",
    "EvidenceType",
    "HandoffParseResult",
    "KnowledgePatchInput",
    "KnowledgePatchType",
    "KnowledgeUsage",
    "SelfReportedCommand",
    "build_agent_args",
    "build_preflight_args",
    "parse_handoff",
    "run_preflight",
]
