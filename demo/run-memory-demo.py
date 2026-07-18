from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPLAY_LABEL = "REPLAY — RECORDED EVIDENCE"
LIVE_LABEL = "LIVE — CODEX EVIDENCE"
EVIDENCE_ROOT = Path(__file__).resolve().parent / "memory-evidence"
SNAPSHOT_PATH = EVIDENCE_ROOT / "demo_snapshot.json"
REPOSITORY_ROOT = Path(__file__).resolve().parent.parent

SNAPSHOT_KEYS = {
    "featured_memories",
    "installed_memories",
    "latest_receipt",
    "stats",
}
RECEIPT_KEYS = {
    "id",
    "memory_id",
    "consumer",
    "matched_trigger",
    "injected_into_codex",
    "codex_reported_use",
    "effect",
    "changed_files",
    "verification",
    "created_at",
}
VERIFICATION_KEYS = {"command", "exit_code", "output_excerpt"}
REQUIRED_RECEIPT_TEXT_FIELDS = (
    "id",
    "memory_id",
    "consumer",
    "matched_trigger",
    "effect",
    "created_at",
)


def _require_replay_text(value: object) -> str:
    if type(value) is not str or not value.strip():
        raise ValueError("Replay receipt required proof is missing")
    return value


def _validate_snapshot(snapshot: Any) -> dict[str, Any]:
    if not isinstance(snapshot, dict) or set(snapshot) != SNAPSHOT_KEYS:
        raise ValueError("Replay snapshot does not match the frozen top-level contract")

    receipt = snapshot["latest_receipt"]
    if not isinstance(receipt, dict) or set(receipt) != RECEIPT_KEYS:
        raise ValueError("Replay receipt does not match the frozen Usage Receipt")
    for field in REQUIRED_RECEIPT_TEXT_FIELDS:
        _require_replay_text(receipt[field])
    try:
        created_at = datetime.fromisoformat(
            receipt["created_at"].replace("Z", "+00:00")
        )
    except ValueError as error:
        raise ValueError("Replay receipt required proof is invalid") from error
    if created_at.tzinfo is None:
        raise ValueError("Replay receipt required proof is invalid")
    if receipt["injected_into_codex"] is not True:
        raise ValueError("Replay receipt must prove Codex context injection")
    if receipt["codex_reported_use"] is not True:
        raise ValueError("Replay receipt must prove Codex-reported use")
    if receipt["changed_files"] != ["pyproject.toml"]:
        raise ValueError("Replay receipt must identify pyproject.toml")

    verification = receipt["verification"]
    if not isinstance(verification, dict) or set(verification) != VERIFICATION_KEYS:
        raise ValueError("Replay verification does not match the frozen contract")
    if verification["command"] != ["pytest", "-q"]:
        raise ValueError("Replay verification command must be pytest -q")
    if type(verification["exit_code"]) is not int or verification["exit_code"] != 0:
        raise ValueError("Replay verification does not match the frozen contract")
    _require_replay_text(verification["output_excerpt"])
    return snapshot


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Pluribus memory demo")
    parser.add_argument("--mode", choices=("live", "replay"), required=True)
    parser.add_argument("--installed-memory-root", type=Path)
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--adapter-command", nargs=argparse.REMAINDER)
    return parser.parse_args()


def _run_live(args: argparse.Namespace) -> int:
    if (
        args.installed_memory_root is None
        or args.workspace is None
        or not args.adapter_command
    ):
        print("live adapter required", file=sys.stderr)
        return 2

    backend_root = REPOSITORY_ROOT / "backend"
    sys.path.insert(0, str(backend_root))
    try:
        from app.usage.live import CommandCodexUsageAdapter, run_live_usage

        receipt = asyncio.run(
            run_live_usage(
                adapter=CommandCodexUsageAdapter(tuple(args.adapter_command)),
                installed_memory_root=args.installed_memory_root,
                workspace=args.workspace,
                receipt_id=f"use_live_{uuid.uuid4().hex}",
                consumer="demo_consumer",
                created_at=datetime.now(UTC),
                verification_command=("pytest", "-q"),
            )
        )
    except Exception:
        print("live usage failed", file=sys.stderr)
        return 1
    finally:
        if sys.path and sys.path[0] == str(backend_root):
            sys.path.pop(0)

    print(LIVE_LABEL)
    print(json.dumps(receipt.to_dict(), ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    args = _parse_args()
    if args.mode == "live":
        return _run_live(args)

    try:
        snapshot = _validate_snapshot(
            json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"invalid replay evidence: {error}", file=sys.stderr)
        return 1

    print(REPLAY_LABEL)
    print(json.dumps(snapshot, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
