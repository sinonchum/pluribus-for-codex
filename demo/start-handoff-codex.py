#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"
FIXTURE_ROOT = REPOSITORY_ROOT / "demo" / "memory-fixture"
HOOK_SCRIPT = REPOSITORY_ROOT / "tools" / "pluribus_codex_hook.py"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.memory_runtime import install_memory  # noqa: E402
from app.registry.seed import SEEDED_MEMORY  # noqa: E402


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Launch interactive Codex with Pluribus memory matching on every action."
    )
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--prompt")
    return parser


def _prepare_workspace(destination: Path) -> None:
    if destination.exists():
        if any(destination.iterdir()):
            raise ValueError(f"workspace must not already contain files: {destination}")
        destination.rmdir()
    shutil.copytree(
        FIXTURE_ROOT,
        destination,
        ignore=shutil.ignore_patterns(
            ".venv", ".pytest_cache", "__pycache__", ".pluribus", ".codex"
        ),
    )
    install_memory(destination, SEEDED_MEMORY.model_dump(mode="json"))

    hook_command = " ".join(
        (shlex.quote(sys.executable), shlex.quote(str(HOOK_SCRIPT)))
    )
    hook_config = {
        "description": "Inject matching verified Pluribus memories into Codex actions.",
        "hooks": {
            "UserPromptSubmit": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": hook_command,
                            "timeout": 10,
                            "statusMessage": "Matching verified Pluribus memories",
                        }
                    ]
                }
            ]
        },
    }
    codex_dir = destination / ".codex"
    codex_dir.mkdir()
    (codex_dir / "hooks.json").write_text(
        json.dumps(hook_config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    subprocess.run(["git", "init", "-q"], cwd=destination, check=True)
    subprocess.run(["git", "add", "."], cwd=destination, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Pluribus Demo",
            "-c",
            "user.email=demo@pluribus.local",
            "commit",
            "-qm",
            "baseline: Bob receives Billing Service",
        ],
        cwd=destination,
        check=True,
    )


def main() -> int:
    args = _parser().parse_args()
    workspace = args.workspace
    if workspace is None:
        parent = Path(tempfile.mkdtemp(prefix="pluribus-interactive-"))
        workspace = parent / "northstar-billing-service"
    workspace = workspace.expanduser().resolve()
    try:
        _prepare_workspace(workspace)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    print("PLURIBUS → CODEX INTERACTIVE HANDOFF", flush=True)
    print(f"Workspace: {workspace}", flush=True)
    print("Installed Memory: mem_billing_audit_handoff_v1", flush=True)
    if args.prepare_only:
        return 0

    codex = os.environ.get("CODEX_EXECUTABLE") or shutil.which("codex")
    if not codex:
        print("error: codex executable not found", file=sys.stderr)
        return 2
    command = [codex, "--dangerously-bypass-hook-trust", "-C", str(workspace)]
    if args.prompt:
        command.append(args.prompt)
    os.execv(codex, command)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
