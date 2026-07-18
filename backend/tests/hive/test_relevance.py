from app.adapters.codex import EvidenceReference, EvidenceType, KnowledgePatchType
from app.hive import (
    ContextPacketRequest,
    KnowledgePatch,
    KnowledgeStatus,
    rank_patches,
)
from app.prompts import AgentRole


def patch(patch_id, status, *, relevant_to=("builder",), confidence=0.8):
    return KnowledgePatch(
        id=patch_id,
        mission_id="m1",
        agent_id="a1",
        type=KnowledgePatchType.REPOSITORY_FACT,
        summary="Reuse health service",
        details="Health implementation dependency",
        evidence=(
            EvidenceReference(EvidenceType.FILE_REFERENCE, "src/health.py", 1, 2),
        ),
        tags=("health",),
        relevant_to=relevant_to,
        confidence=confidence,
        status=status,
        baseline_commit="abc",
    )


def request(patches):
    return ContextPacketRequest(
        mission_id="m1",
        agent_id="builder_1",
        role=AgentRole.BUILDER,
        mission_objective="health",
        assigned_task="Implement health service",
        baseline_commit="abc",
        working_directory=".",
        allowed_paths=("src/health.py",),
        protected_paths=(),
        active_constraints=(),
        task_tags=("health",),
        patches=tuple(patches),
    )


def test_builder_relevance_evidence_strength_and_determinism():
    linked = patch("kp_linked", KnowledgeStatus.SOURCE_LINKED)
    disputed = patch("kp_disputed", KnowledgeStatus.DISPUTED)
    first = rank_patches(request((disputed, linked)))
    second = rank_patches(request((disputed, linked)))
    assert first == second
    assert first[0].patch.id == "kp_linked"
    assert first[0].score.role_relevance == 40
    assert first[0].score.assigned_file_overlap == 20
    assert first[1].score.disputed_penalty < 0


def test_rejected_is_excluded_and_ties_break_by_id():
    a = patch("kp_a", KnowledgeStatus.PROPOSED)
    b = patch("kp_b", KnowledgeStatus.PROPOSED)
    rejected = patch("kp_0", KnowledgeStatus.REJECTED, confidence=1)
    ranked = rank_patches(request((b, rejected, a)))
    assert [item.patch.id for item in ranked] == ["kp_a", "kp_b"]
