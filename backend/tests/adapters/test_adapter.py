import asyncio
from datetime import datetime, timezone
import json

from backend.app.adapters.codex import (
    AgentRunRequest,
    CodexAdapter,
    CodexConfig,
    CodexRunResult,
    parse_handoff,
)
from backend.app.hive import FilesystemEvidenceResolver, HiveService
from backend.app.prompts import AgentRole


class FakeRunner:
    def __init__(self, result):
        self.result = result
        self.request = None

    async def run(self, request):
        self.request = request
        return self.result


def process_result(stdout, *, exit_code=0, timed_out=False):
    parsed = parse_handoff(stdout)
    now = datetime.now(timezone.utc)
    return CodexRunResult(
        command=("codex", "exec", "-"),
        working_directory="/repo",
        role="builder",
        mission_id="m1",
        agent_id="builder_1",
        started_at=now,
        finished_at=now,
        duration_seconds=0.1,
        exit_code=exit_code,
        timed_out=timed_out,
        cancelled=False,
        stdout=stdout,
        stderr="",
        stdout_truncated=False,
        stderr_truncated=False,
        structured_handoff=parsed.handoff,
        parse_error=parsed.error,
    )


def test_facade_returns_raw_parsed_validated_and_consumption_state(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src/service.py").write_text("one\ntwo\n", encoding="utf-8")
    payload = {
        "status": "completed",
        "summary": "done",
        "changed_files": ["src/route.py"],
        "self_reported_commands": [],
        "consumed_patch_ids": ["kp_old"],
        "knowledge_usage": [
            {
                "patch_id": "kp_old",
                "effect": "Reused the old service.",
                "changed_files": ["src/route.py"],
            }
        ],
        "knowledge_patches": [
            {
                "type": "repository_fact",
                "summary": "Service has two lines.",
                "details": "Source-linked only.",
                "evidence": [
                    {
                        "type": "file_reference",
                        "path": "src/service.py",
                        "line_start": 1,
                        "line_end": 2,
                    }
                ],
                "tags": ["service"],
                "relevant_to": ["tester"],
                "confidence": 0.9,
            }
        ],
        "risks": [],
    }
    raw = "<PLURIBUS_HANDOFF>" + json.dumps(payload) + "</PLURIBUS_HANDOFF>"
    runner = FakeRunner(process_result(raw))
    adapter = CodexAdapter(
        CodexConfig(),
        runner=runner,
        hive_service=HiveService(
            FilesystemEvidenceResolver(), patch_id_factory=lambda: "kp_new"
        ),
    )
    outcome = asyncio.run(
        adapter.run_agent(
            AgentRunRequest(
                mission_id="m1",
                agent_id="builder_1",
                role=AgentRole.BUILDER,
                rendered_prompt="prompt",
                working_directory=tmp_path,
                delivered_patch_ids=("kp_old",),
                baseline_commit="abc",
            )
        )
    )
    assert outcome.parsed
    assert outcome.stdout == raw
    assert outcome.validated_new_patches[0].patch.id == "kp_new"
    assert outcome.validated_new_patches[0].patch.status.value == "source_linked"
    assert outcome.consumption_validation.valid
    assert not outcome.errors
    assert runner.request.prompt == "prompt"


def test_facade_surfaces_process_and_parse_failures(tmp_path):
    runner = FakeRunner(process_result("unstructured", exit_code=5, timed_out=True))
    outcome = asyncio.run(
        CodexAdapter(CodexConfig(), runner=runner).run_agent(
            AgentRunRequest(
                mission_id="m1",
                agent_id="scout_1",
                role=AgentRole.SCOUT,
                rendered_prompt="prompt",
                working_directory=tmp_path,
            )
        )
    )
    assert not outcome.parsed
    assert any("timed out" in error for error in outcome.errors)
    assert any("code 5" in error for error in outcome.errors)
    assert any("No structured" in error for error in outcome.errors)


def test_timed_out_agent_patch_remains_proposed(tmp_path):
    (tmp_path / "src.py").write_text("one\n", encoding="utf-8")
    payload = {
        "status": "partial",
        "summary": "partial",
        "changed_files": [],
        "self_reported_commands": [],
        "consumed_patch_ids": [],
        "knowledge_usage": [],
        "knowledge_patches": [
            {
                "type": "repository_fact",
                "summary": "A partial claim.",
                "details": "Not trusted after timeout.",
                "evidence": [
                    {
                        "type": "file_reference",
                        "path": "src.py",
                        "line_start": 1,
                        "line_end": 1,
                    }
                ],
                "tags": [],
                "relevant_to": ["builder"],
                "confidence": 0.8,
            }
        ],
        "risks": [],
    }
    raw = "<PLURIBUS_HANDOFF>" + json.dumps(payload) + "</PLURIBUS_HANDOFF>"
    adapter = CodexAdapter(
        CodexConfig(),
        runner=FakeRunner(process_result(raw, timed_out=True)),
        hive_service=HiveService(FilesystemEvidenceResolver()),
    )
    outcome = asyncio.run(
        adapter.run_agent(
            AgentRunRequest(
                mission_id="m1",
                agent_id="scout_1",
                role=AgentRole.SCOUT,
                rendered_prompt="prompt",
                working_directory=tmp_path,
                baseline_commit="abc",
            )
        )
    )
    assert outcome.validated_new_patches[0].patch.status.value == "proposed"
