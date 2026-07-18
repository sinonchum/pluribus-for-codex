from pathlib import Path

from app.adapters.codex import EvidenceReference, EvidenceType, KnowledgePatchType
from app.hive import (
    ContextPacketRequest,
    KnowledgePatch,
    KnowledgeStatus,
    compile_context_packet,
)
from app.prompts import AgentRole


def patch(patch_id, patch_type, status, relevant_to=("builder",)):
    return KnowledgePatch(
        id=patch_id,
        mission_id="m1",
        agent_id="scout_1",
        type=patch_type,
        summary=f"Summary {patch_id}",
        details="Details",
        evidence=(EvidenceReference(EvidenceType.FILE_REFERENCE, "src/a.py", 1, 2),),
        tags=("task",),
        relevant_to=relevant_to,
        confidence=0.9,
        status=status,
        baseline_commit="abc",
    )


def request(patches, role=AgentRole.BUILDER, max_patches=2):
    return ContextPacketRequest(
        mission_id="m1",
        agent_id="worker_1",
        role=role,
        mission_objective="Objective",
        assigned_task="Task",
        baseline_commit="abc",
        working_directory=Path("/repo"),
        allowed_paths=("src/a.py",),
        protected_paths=("auth/**",),
        active_constraints=("No dependencies",),
        patches=tuple(patches),
        max_patches=max_patches,
    )


def test_active_constraints_mandatory_patch_and_delivery_ids_are_recorded():
    constraint = patch(
        "kp_constraint", KnowledgePatchType.CONSTRAINT, KnowledgeStatus.PROPOSED, ()
    )
    fact = patch(
        "kp_fact", KnowledgePatchType.REPOSITORY_FACT, KnowledgeStatus.SOURCE_LINKED
    )
    packet = compile_context_packet(request((fact, constraint), max_patches=1))
    assert "No dependencies" in packet.rendered_text
    assert "kp_constraint" in packet.delivered_patch_ids
    assert (
        "source-linked; the interpretation is not independently verified"
        not in packet.rendered_text
    )


def test_source_linked_and_disputed_are_labeled_and_rejected_excluded():
    linked = patch(
        "kp_linked", KnowledgePatchType.REPOSITORY_FACT, KnowledgeStatus.SOURCE_LINKED
    )
    disputed = patch("kp_disputed", KnowledgePatchType.RISK, KnowledgeStatus.DISPUTED)
    rejected = patch(
        "kp_rejected", KnowledgePatchType.TEST_RESULT, KnowledgeStatus.REJECTED
    )
    packet = compile_context_packet(
        request((disputed, rejected, linked), max_patches=3)
    )
    assert "[source_linked] kp_linked" in packet.rendered_text
    assert "not independently verified" in packet.rendered_text
    assert "[disputed] kp_disputed" in packet.rendered_text
    assert "kp_rejected" not in packet.rendered_text
    assert packet.delivered_patch_ids == tuple(p.id for p in packet.included_patches)


def test_reviewer_receives_risk_and_test_result_deterministically():
    risk = patch(
        "kp_risk", KnowledgePatchType.RISK, KnowledgeStatus.SOURCE_LINKED, ("reviewer",)
    )
    test = patch(
        "kp_test",
        KnowledgePatchType.TEST_RESULT,
        KnowledgeStatus.EXECUTION_VERIFIED,
        ("reviewer",),
    )
    first = compile_context_packet(request((test, risk), AgentRole.REVIEWER))
    second = compile_context_packet(request((test, risk), AgentRole.REVIEWER))
    assert first == second
    assert set(first.delivered_patch_ids) == {"kp_risk", "kp_test"}
