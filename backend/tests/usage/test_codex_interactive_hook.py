from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from app.memory_runtime import install_memory, list_installed_memories
from app.registry.seed import SEEDED_MEMORY

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
HOOK = REPOSITORY_ROOT / "tools" / "pluribus_codex_hook.py"
LAUNCHER = REPOSITORY_ROOT / "demo" / "start-handoff-codex.py"


def test_user_prompt_hook_injects_matching_memory_context(tmp_path: Path) -> None:
    workspace = tmp_path / "billing-service"
    workspace.mkdir()
    install_memory(workspace, SEEDED_MEMORY.model_dump(mode="json"))
    hook_input = {
        "session_id": "session-1",
        "turn_id": "turn-1",
        "cwd": str(workspace),
        "hook_event_name": "UserPromptSubmit",
        "model": "gpt-5.6-codex",
        "permission_mode": "default",
        "prompt": "Fix the failing tests by implementing cancel an invoice support.",
        "transcript_path": None,
    }

    result = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(hook_input),
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    context = output["hookSpecificOutput"]["additionalContext"]
    assert "mem_billing_audit_handoff_v1" in context
    assert "Matched trigger: cancel an invoice" in context
    assert "transition_invoice()" in context
    assert "Pluribus injected this memory for the current Codex action" in context


def test_user_prompt_hook_is_silent_when_no_memory_matches(tmp_path: Path) -> None:
    workspace = tmp_path / "billing-service"
    workspace.mkdir()
    install_memory(workspace, SEEDED_MEMORY.model_dump(mode="json"))
    hook_input = {
        "session_id": "session-1",
        "turn_id": "turn-2",
        "cwd": str(workspace),
        "hook_event_name": "UserPromptSubmit",
        "model": "gpt-5.6-codex",
        "permission_mode": "default",
        "prompt": "Explain how Python dataclasses work.",
        "transcript_path": None,
    }

    result = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(hook_input),
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == ""


def test_launcher_prepares_hook_enabled_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "northstar-billing-service"

    result = subprocess.run(
        [
            sys.executable,
            str(LAUNCHER),
            "--prepare-only",
            "--workspace",
            str(workspace),
        ],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert workspace.as_posix() in result.stdout
    hooks = json.loads(
        (workspace / ".codex" / "hooks.json").read_text(encoding="utf-8")
    )
    handler = hooks["hooks"]["UserPromptSubmit"][0]["hooks"][0]
    assert handler["type"] == "command"
    assert "pluribus_codex_hook.py" in handler["command"]
    installed = list_installed_memories(workspace)
    assert [item["memory_id"] for item in installed] == ["mem_billing_audit_handoff_v1"]
