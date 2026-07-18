#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.memory_runtime import (  # noqa: E402
    build_context_packet,
    match_installed_memories,
)


def _read_hook_input() -> dict[str, Any]:
    value = json.load(sys.stdin)
    if not isinstance(value, dict):
        raise ValueError("Codex hook input must be a JSON object")
    if value.get("hook_event_name") != "UserPromptSubmit":
        raise ValueError("unsupported Codex hook event")
    prompt = value.get("prompt")
    cwd = value.get("cwd")
    if not isinstance(prompt, str) or not isinstance(cwd, str):
        raise ValueError("Codex hook input requires string prompt and cwd fields")
    return value


def build_hook_output(value: dict[str, Any]) -> dict[str, Any] | None:
    matches = match_installed_memories(Path(value["cwd"]), value["prompt"], limit=3)
    if not matches:
        return None
    packet = build_context_packet(matches)
    context = (
        "Pluribus injected this memory for the current Codex action. "
        "When asked which memory was used, report its exact Memory ID and matched trigger.\n\n"
        f"{packet}"
    )
    return {
        "continue": True,
        "suppressOutput": False,
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": context,
        },
    }


def main() -> int:
    try:
        output = build_hook_output(_read_hook_input())
    except (json.JSONDecodeError, OSError, ValueError) as error:
        print(f"Pluribus Codex hook error: {error}", file=sys.stderr)
        return 1
    if output is not None:
        print(json.dumps(output, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
