#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.usage.codex_cli_adapter import run_codex_cli_usage  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        print(
            "usage: codex_usage_adapter.py INSTALLED_MEMORY_ROOT WORKSPACE",
            file=sys.stderr,
        )
        return 2
    try:
        proof = run_codex_cli_usage(
            args[0],
            args[1],
            codex_executable=os.getenv("CODEX_EXECUTABLE", "codex"),
        )
    except (OSError, ValueError, RuntimeError) as error:
        print(f"codex usage adapter failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(proof, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
