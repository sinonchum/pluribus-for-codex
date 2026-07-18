from backend.app.adapters.codex import AgentHandoff, AgentStatus, KnowledgeUsage
from backend.app.hive import KnowledgeConsumptionTracker
from backend.app.prompts import AgentRole


def handoff(consumed=(), usage=(), changed_files=("src/a.py",)):
    return AgentHandoff(
        status=AgentStatus.COMPLETED,
        summary="done",
        changed_files=changed_files,
        consumed_patch_ids=consumed,
        knowledge_usage=usage,
    )


def test_delivered_and_causally_used_patch_is_accepted():
    usage = KnowledgeUsage("kp_1", "Reused the service.", ("src/a.py",))
    result = KnowledgeConsumptionTracker().validate_handoff_consumption(
        ("kp_1",),
        handoff(("kp_1",), (usage,)),
        mission_id="m1",
        agent_id="builder_1",
        role=AgentRole.BUILDER,
    )
    assert result.valid
    assert result.consumptions[0].changed_files == ("src/a.py",)


def test_delivery_alone_does_not_count_as_consumption():
    result = KnowledgeConsumptionTracker().validate_handoff_consumption(
        ("kp_1",), handoff()
    )
    assert result.valid
    assert not result.consumptions


def test_undelivered_consumed_and_consumed_without_usage_are_rejected():
    result = KnowledgeConsumptionTracker().validate_handoff_consumption(
        ("kp_1",), handoff(("kp_unknown",))
    )
    assert not result.valid
    assert result.unknown_patch_ids == ("kp_unknown",)
    assert result.consumed_without_usage == ("kp_unknown",)


def test_usage_without_consumed_flag_is_rejected_and_duplicate_is_deterministic():
    usage = KnowledgeUsage("kp_1", "First", ("src/a.py",))
    duplicate = KnowledgeUsage("kp_1", "Second", ("src/b.py",))
    result = KnowledgeConsumptionTracker().validate_handoff_consumption(
        ("kp_1",), handoff((), (usage, duplicate))
    )
    assert not result.valid
    assert result.usage_without_consumed_flag == ("kp_1",)
    assert "Duplicate" in result.warnings[0]
