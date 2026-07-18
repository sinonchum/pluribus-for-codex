import asyncio
import json

from backend.app.adapters.codex import parse_handoff
from backend.app.hive import (
    ContextPacketRequest,
    FilesystemEvidenceResolver,
    HiveService,
    KnowledgeConsumptionTracker,
    KnowledgeStatus,
    compile_context_packet,
    packet_prompt_knowledge,
)
from backend.app.prompts import AgentRole, PromptRequest, render_prompt


def marked(payload):
    return "<PLURIBUS_HANDOFF>\n" + json.dumps(payload) + "\n</PLURIBUS_HANDOFF>"


def test_scout_patch_flows_causally_to_builder(tmp_path):
    source = tmp_path / "src/health.py"
    source.parent.mkdir()
    source.write_text("class HealthService:\n    pass\n", encoding="utf-8")
    scout_output = marked(
        {
            "status": "completed",
            "summary": "Mapped health architecture.",
            "changed_files": [],
            "self_reported_commands": [],
            "consumed_patch_ids": [],
            "knowledge_usage": [],
            "knowledge_patches": [
                {
                    "type": "repository_fact",
                    "summary": "HealthService is the existing health abstraction.",
                    "details": "Builders should reuse it.",
                    "evidence": [
                        {
                            "type": "file_reference",
                            "path": "src/health.py",
                            "line_start": 1,
                            "line_end": 2,
                        }
                    ],
                    "tags": ["health", "architecture"],
                    "relevant_to": ["builder", "tester"],
                    "confidence": 0.98,
                }
            ],
            "risks": [],
        }
    )
    scout = parse_handoff(scout_output)
    assert scout.parsed and scout.handoff is not None

    service = HiveService(
        FilesystemEvidenceResolver(), patch_id_factory=lambda: "kp_018"
    )
    validated = asyncio.run(
        service.validate_patch_input(
            scout.handoff.knowledge_patches[0],
            mission_id="mission_001",
            agent_id="scout_1",
            repository_path=tmp_path,
            baseline_commit="abc123",
        )
    )
    assert validated.validation.valid
    assert validated.patch.status is KnowledgeStatus.SOURCE_LINKED

    packet = compile_context_packet(
        ContextPacketRequest(
            mission_id="mission_001",
            agent_id="builder_1",
            role=AgentRole.BUILDER,
            mission_objective="Add a detailed health endpoint.",
            assigned_task="Implement endpoint by reusing health architecture.",
            baseline_commit="abc123",
            working_directory=tmp_path,
            allowed_paths=("src/routes.py",),
            protected_paths=("src/auth/**",),
            active_constraints=("Do not add dependencies.",),
            patches=(validated.patch,),
            max_patches=5,
            task_tags=("health",),
        )
    )
    assert packet.delivered_patch_ids == ("kp_018",)
    builder_prompt = render_prompt(
        PromptRequest(
            mission_id="mission_001",
            agent_id="builder_1",
            role=AgentRole.BUILDER,
            mission_objective="Add a detailed health endpoint.",
            assigned_task="Implement it.",
            repository_baseline="abc123",
            working_directory=str(tmp_path),
            hive_knowledge=packet_prompt_knowledge(packet),
            allowed_paths=("src/routes.py",),
            protected_paths=("src/auth/**",),
            delivered_patch_ids=packet.delivered_patch_ids,
        )
    )
    assert "kp_018" in builder_prompt
    assert "src/health.py:1-2" in builder_prompt

    builder = parse_handoff(
        marked(
            {
                "status": "completed",
                "summary": "Reused HealthService.",
                "changed_files": ["src/routes.py"],
                "self_reported_commands": [],
                "consumed_patch_ids": ["kp_018"],
                "knowledge_usage": [
                    {
                        "patch_id": "kp_018",
                        "effect": "Reused HealthService instead of creating a duplicate abstraction.",
                        "changed_files": ["src/routes.py"],
                    }
                ],
                "knowledge_patches": [],
                "risks": [],
            }
        )
    )
    assert builder.parsed and builder.handoff is not None
    assert builder.handoff.consumed_patch_ids == ("kp_018",)
    consumption = KnowledgeConsumptionTracker().validate_handoff_consumption(
        packet.delivered_patch_ids,
        builder.handoff,
        mission_id="mission_001",
        agent_id="builder_1",
        role=AgentRole.BUILDER,
    )
    assert consumption.valid
    assert consumption.consumptions[0].patch_id == "kp_018"
    assert "Reused HealthService" in consumption.consumptions[0].effect
    assert consumption.consumptions[0].changed_files == ("src/routes.py",)
