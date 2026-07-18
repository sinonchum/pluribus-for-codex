"""Tests for deterministic, consistent evidence report rendering."""

from __future__ import annotations

import json

from app.reporting import (
    AgentRecord,
    ArtifactRecord,
    Baseline,
    CoordinatorVerification,
    EvidenceRecord,
    EvidenceReport,
    KnowledgeDelivery,
    Mission,
    OriginalInvariant,
    ScopeViolation,
    TimelineEvent,
    UnresolvedRisk,
    VerificationRecord,
    render_json,
    render_markdown,
)
from app.verification import VerificationTerminalState


def _report(*, reverse: bool = False) -> EvidenceReport:
    agents = [
        AgentRecord("agent-b", "tester", "tests passed"),
        AgentRecord("agent-a", "implementer", "change produced"),
    ]
    timeline = [
        TimelineEvent("2026-01-02T00:00:00Z", "event-b", "verified"),
        TimelineEvent("2026-01-01T00:00:00Z", "event-a", "started"),
    ]
    deliveries = [
        KnowledgeDelivery("delivery-b", "agent-b", "agent-a", "result", ("use-z",)),
        KnowledgeDelivery(
            "delivery-a", "agent-a", "agent-b", "contract", ("use-b", "use-a")
        ),
    ]
    artifacts = [
        ArtifactRecord("z.py", "z" * 64, 2, "second"),
        ArtifactRecord("a.py", "a" * 64, 1, "first"),
    ]
    if reverse:
        agents.reverse()
        timeline.reverse()
        deliveries.reverse()
        artifacts.reverse()
    command = VerificationRecord(
        name="pytest",
        executable="python",
        args=("-m", "pytest"),
        cwd="workspace path",
        timeout_seconds=60,
        required=True,
        status="passed",
        exit_code=0,
        duration_seconds=1.23456789,
        stdout="2 passed\n",
        stderr="",
        command_sha256="c" * 64,
        stdout_sha256="o" * 64,
        stderr_sha256="e" * 64,
    )
    return EvidenceReport(
        mission=Mission("mission-1", "Ship deterministic evidence"),
        baseline=Baseline("abc123", "clean baseline"),
        original_invariant=OriginalInvariant("Never execute through a shell"),
        agents=tuple(agents),
        timeline=tuple(timeline),
        knowledge_deliveries=tuple(deliveries),
        artifacts=tuple(artifacts),
        diff_hash="d" * 64,
        review_evidence=(EvidenceRecord("reviewer", "approved", "looks good"),),
        tester_evidence=(EvidenceRecord("pytest", "passed", "2 passed"),),
        coordinator_verification=CoordinatorVerification(
            VerificationTerminalState.VERIFIED, (command,)
        ),
        scope_violations=(ScopeViolation("outside.txt", "reverted"),),
        unresolved_risks=(UnresolvedRisk("risk-1", "platform variance", "CI"),),
    )


def test_report_contains_every_required_section_and_is_json_compatible() -> None:
    report = _report()
    data = report.to_dict()
    required = {
        "mission",
        "baseline",
        "original_invariant",
        "agents",
        "timeline",
        "knowledge_deliveries",
        "artifacts",
        "diff_hash",
        "review_evidence",
        "tester_evidence",
        "coordinator_verification",
        "scope_violations",
        "terminal_state",
        "unresolved_risks",
    }

    assert set(data) == required
    assert json.loads(report.to_json()) == data
    assert json.loads(render_json(report)) == data
    assert data["terminal_state"] == "verified"
    assert data["coordinator_verification"]["terminal_state"] == "verified"


def test_sorting_is_stable_without_mutating_source_order() -> None:
    original = _report()
    reversed_report = _report(reverse=True)

    assert original.to_dict() == reversed_report.to_dict()
    assert [item.agent_id for item in original.agents] == ["agent-b", "agent-a"]
    assert [item["agent_id"] for item in original.to_dict()["agents"]] == [
        "agent-a",
        "agent-b",
    ]
    assert [item["application_order"] for item in original.to_dict()["artifacts"]] == [
        1,
        2,
    ]
    assert original.to_dict()["knowledge_deliveries"][0]["causal_uses"] == [
        "use-a",
        "use-b",
    ]


def test_markdown_is_rendered_from_same_canonical_values() -> None:
    report = _report()
    data = report.to_dict()
    markdown = report.to_markdown()

    assert markdown == render_markdown(report)
    for heading in (
        "Mission",
        "Baseline",
        "Original Invariant",
        "Agents",
        "Timeline",
        "Knowledge Deliveries and Causal Uses",
        "Artifacts and Application Order",
        "Diff Hash",
        "Review Evidence",
        "Tester Evidence",
        "Coordinator Verification",
        "Scope Violations",
        "Terminal State",
        "Unresolved Risks",
    ):
        assert f"## {heading}" in markdown
    for value in (
        data["mission"]["mission_id"],
        data["mission"]["objective"],
        data["diff_hash"],
        data["agents"][0]["agent_id"],
        data["knowledge_deliveries"][0]["causal_uses"][0],
        data["artifacts"][0]["sha256"],
        data["coordinator_verification"]["commands"][0]["stdout_sha256"],
        data["terminal_state"],
    ):
        assert value in markdown


def test_secrets_are_redacted_in_both_formats_and_logs_are_bounded() -> None:
    secret = "sk-1234567890abcdefghijklmnop"
    long_log = f"api_key={secret} " + "é" * 100
    base = _report()
    report = EvidenceReport(
        mission=Mission("mission-secret", f"Bearer {secret}"),
        baseline=base.baseline,
        original_invariant=base.original_invariant,
        agents=base.agents,
        timeline=base.timeline,
        knowledge_deliveries=base.knowledge_deliveries,
        artifacts=base.artifacts,
        diff_hash=base.diff_hash,
        review_evidence=(EvidenceRecord("review", "password=hunter2", long_log),),
        tester_evidence=base.tester_evidence,
        coordinator_verification=CoordinatorVerification(
            VerificationTerminalState.VERIFIED,
            (
                VerificationRecord(
                    name="test",
                    executable="python",
                    args=("-m", "pytest"),
                    cwd="workspace",
                    timeout_seconds=30,
                    required=True,
                    status="passed",
                    exit_code=0,
                    duration_seconds=0.1,
                    stdout=f"Authorization: Bearer {secret}",
                    stderr=(
                        "-----BEGIN PRIVATE KEY-----\n"
                        "private\n"
                        "-----END PRIVATE KEY-----"
                    ),
                    command_sha256="c" * 64,
                    stdout_sha256="o" * 64,
                    stderr_sha256="e" * 64,
                ),
            ),
        ),
        log_limit_bytes=24,
    )

    data = report.to_dict()
    serialized = json.dumps(data)
    markdown = report.to_markdown()
    assert secret not in serialized
    assert secret not in markdown
    assert "hunter2" not in serialized
    assert "private" not in serialized.lower()
    assert "[REDACTED]" in serialized
    assert len(data["review_evidence"][0]["log"].encode()) <= 24
    assert data["review_evidence"][0]["log_truncated"] is True
    command = data["coordinator_verification"]["commands"][0]
    assert len(command["stdout"].encode()) <= 24
    assert command["stdout_truncated"] is True


def test_empty_collections_render_explicitly() -> None:
    base = _report()
    report = EvidenceReport(
        mission=base.mission,
        baseline=base.baseline,
        original_invariant=base.original_invariant,
        agents=(),
        timeline=(),
        knowledge_deliveries=(),
        artifacts=(),
        diff_hash=base.diff_hash,
        review_evidence=(),
        tester_evidence=(),
        coordinator_verification=CoordinatorVerification(
            VerificationTerminalState.VERIFIED
        ),
    )

    assert report.to_markdown().count("_None._") == 9
