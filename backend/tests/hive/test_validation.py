import asyncio
from dataclasses import replace

from app.adapters.codex import EvidenceReference, EvidenceType, KnowledgePatchType
from app.hive import (
    FilesystemEvidenceResolver,
    KnowledgePatch,
    KnowledgeStatus,
    validate_knowledge_patch,
)


def patch(**overrides):
    values = dict(
        id="kp_1",
        mission_id="m1",
        agent_id="scout_1",
        type=KnowledgePatchType.REPOSITORY_FACT,
        summary="Service exists.",
        details="It is reused.",
        evidence=(
            EvidenceReference(EvidenceType.FILE_REFERENCE, "src/service.py", 1, 2),
        ),
        tags=("service",),
        relevant_to=("builder",),
        confidence=0.9,
        status=KnowledgeStatus.PROPOSED,
        baseline_commit="abc123",
    )
    values.update(overrides)
    return KnowledgePatch(**values)


def test_valid_file_reference_becomes_source_linked(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src/service.py").write_text("one\ntwo\n", encoding="utf-8")
    result = asyncio.run(
        validate_knowledge_patch(patch(), tmp_path, FilesystemEvidenceResolver())
    )
    assert result.valid
    assert result.resulting_status is KnowledgeStatus.SOURCE_LINKED


def test_missing_file_and_invalid_line_range_remain_proposed(tmp_path):
    missing = asyncio.run(
        validate_knowledge_patch(patch(), tmp_path, FilesystemEvidenceResolver())
    )
    assert not missing.valid
    assert missing.resulting_status is KnowledgeStatus.PROPOSED

    (tmp_path / "src").mkdir()
    (tmp_path / "src/service.py").write_text("one\n", encoding="utf-8")
    invalid = asyncio.run(
        validate_knowledge_patch(patch(), tmp_path, FilesystemEvidenceResolver())
    )
    assert not invalid.valid
    assert "has 1 lines" in invalid.errors[0]


def test_rejects_unsafe_and_unsupported_evidence(tmp_path):
    absolute = replace(
        patch(),
        evidence=(EvidenceReference(EvidenceType.FILE_REFERENCE, "/etc/passwd", 1, 1),),
    )
    traversal = replace(
        patch(),
        evidence=(EvidenceReference(EvidenceType.FILE_REFERENCE, "../x", 1, 1),),
    )
    unsupported = replace(
        patch(), evidence=(EvidenceReference("command", "src/service.py", 1, 1),)
    )
    for candidate in (absolute, traversal, unsupported):
        result = asyncio.run(
            validate_knowledge_patch(candidate, tmp_path, FilesystemEvidenceResolver())
        )
        assert not result.valid
        assert result.resulting_status is KnowledgeStatus.PROPOSED


def test_agent_claim_cannot_be_execution_verified(tmp_path):
    claimed = replace(patch(), status=KnowledgeStatus.EXECUTION_VERIFIED)
    result = asyncio.run(
        validate_knowledge_patch(
            claimed,
            tmp_path,
            FilesystemEvidenceResolver(),
            source_linking_requested=False,
        )
    )
    assert not result.valid
    assert result.resulting_status is KnowledgeStatus.PROPOSED
    assert "Agent output cannot" in result.errors[0]


def test_disputed_patch_is_not_silently_promoted(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src/service.py").write_text("one\ntwo\n", encoding="utf-8")
    disputed = replace(patch(), status=KnowledgeStatus.DISPUTED)
    result = asyncio.run(
        validate_knowledge_patch(disputed, tmp_path, FilesystemEvidenceResolver())
    )
    assert result.valid
    assert result.resulting_status is KnowledgeStatus.DISPUTED
    assert "not promoted" in result.warnings[0]


def test_source_linking_requires_recorded_baseline(tmp_path):
    result = asyncio.run(
        validate_knowledge_patch(
            replace(patch(), baseline_commit=None),
            tmp_path,
            FilesystemEvidenceResolver(),
        )
    )
    assert not result.valid
    assert "baseline_commit" in result.errors[0]
