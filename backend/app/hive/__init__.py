"""Public Hive memory, context, and consumption interfaces."""

from .consumption import (
    ConsumptionValidationResult,
    KnowledgeConsumptionTracker,
    PatchConsumption,
    PatchDelivery,
)
from .context_packet import compile_context_packet, packet_prompt_knowledge
from .models import (
    ContextPacket,
    ContextPacketRequest,
    KnowledgePatch,
    KnowledgeStatus,
    KnowledgeValidationResult,
    ValidatedKnowledgePatch,
)
from .relevance import RankedPatch, RelevanceScore, rank_patches, score_patch
from .service import HiveService
from .validation import (
    EvidenceResolver,
    FilesystemEvidenceResolver,
    validate_knowledge_patch,
)

__all__ = [
    "ConsumptionValidationResult",
    "ContextPacket",
    "ContextPacketRequest",
    "EvidenceResolver",
    "FilesystemEvidenceResolver",
    "HiveService",
    "KnowledgeConsumptionTracker",
    "KnowledgePatch",
    "KnowledgeStatus",
    "KnowledgeValidationResult",
    "PatchConsumption",
    "PatchDelivery",
    "RankedPatch",
    "RelevanceScore",
    "ValidatedKnowledgePatch",
    "compile_context_packet",
    "packet_prompt_knowledge",
    "rank_patches",
    "score_patch",
    "validate_knowledge_patch",
]
