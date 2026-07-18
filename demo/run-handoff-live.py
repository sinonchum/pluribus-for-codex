#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"
FIXTURE_ROOT = REPOSITORY_ROOT / "demo" / "memory-fixture"
CODEX_ADAPTER = REPOSITORY_ROOT / "tools" / "codex_usage_adapter.py"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.memory_runtime import install_memory  # noqa: E402
from app.registry.seed import SEEDED_MEMORY  # noqa: E402
from app.usage.live import CommandCodexUsageAdapter, run_live_usage  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Alice-to-Bob knowledge handoff through the real Codex CLI."
    )
    parser.add_argument(
        "--api-base",
        help="Optional Live API base; publishes the verified receipt when provided.",
    )
    return parser.parse_args()


def _prepare_workspace() -> tuple[Path, Path]:
    demo_root = Path(tempfile.mkdtemp(prefix="pluribus-handoff-"))
    workspace = demo_root / "northstar-billing-service"
    shutil.copytree(
        FIXTURE_ROOT,
        workspace,
        ignore=shutil.ignore_patterns(
            ".venv", ".pytest_cache", "__pycache__", "*.pyc"
        ),
    )
    consumer_root = demo_root / "bob-codex"
    consumer_root.mkdir()
    install_memory(consumer_root, SEEDED_MEMORY.model_dump(mode="json"))
    return workspace, consumer_root


def _run_baseline(workspace: Path) -> str:
    result = subprocess.run(
        ("uv", "run", "pytest", "-q"),
        cwd=workspace,
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )
    output = f"{result.stdout}\n{result.stderr}".strip()
    if result.returncode == 0 or "cancel_invoice" not in output:
        raise RuntimeError("billing fixture did not reproduce the expected knowledge gap")
    return output


def _publish_receipt(api_base: str, receipt: dict[str, object]) -> None:
    request = urllib.request.Request(
        f"{api_base.rstrip('/')}/api/usage-receipts",
        data=json.dumps(receipt).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status != 201:
                raise RuntimeError(f"Live API returned HTTP {response.status}")
    except urllib.error.URLError as error:
        raise RuntimeError(f"could not publish receipt to {api_base}") from error


async def _run() -> tuple[dict[str, object], Path, str]:
    workspace, consumer_root = _prepare_workspace()
    baseline = _run_baseline(workspace)
    receipt = await run_live_usage(
        adapter=CommandCodexUsageAdapter((sys.executable, str(CODEX_ADAPTER))),
        installed_memory_root=consumer_root,
        workspace=workspace,
        receipt_id=f"use_handoff_{uuid4().hex}",
        consumer="Bob · Successor Engineer",
        created_at=datetime.now(UTC),
        verification_command=("uv", "run", "pytest", "-q"),
    )
    return receipt.to_dict(), workspace, baseline


def main() -> int:
    args = _parse_args()
    # The runner creates an isolated fixture environment. Inheriting the backend
    # VIRTUAL_ENV makes uv emit a distracting mismatch warning into evidence.
    os.environ.pop("VIRTUAL_ENV", None)
    try:
        receipt, workspace, baseline = asyncio.run(_run())
        if args.api_base:
            _publish_receipt(args.api_base, receipt)
    except (OSError, RuntimeError, ValueError) as error:
        print(f"handoff demo failed: {error}", file=sys.stderr)
        return 1

    excerpt = "\n".join(baseline.splitlines()[-8:])
    print("BASELINE — KNOWLEDGE GAP")
    print(excerpt)
    print(f"\nWorkspace retained for inspection: {workspace}")
    if args.api_base:
        print(f"Receipt published to: {args.api_base.rstrip('/')}")
    print("\nLIVE — KNOWLEDGE HANDOFF")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
