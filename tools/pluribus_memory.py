#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.memory_runtime import (  # noqa: E402
    build_context_packet,
    install_memory,
    list_installed_memories,
    match_installed_memories,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Install and match explicit Pluribus memory packages."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    install = commands.add_parser("install", help="Install a Memory Capsule JSON file.")
    install.add_argument("--capsule", required=True, type=Path)
    install.add_argument("--root", required=True, type=Path)

    listing = commands.add_parser("list", help="List installed memory manifests.")
    listing.add_argument("--root", required=True, type=Path)

    match = commands.add_parser("match", help="Match installed memories to task text.")
    match.add_argument("--text", required=True)
    match.add_argument("--root", required=True, type=Path)
    match.add_argument("--limit", type=int, default=3)
    match.add_argument("--max-context-chars", type=int, default=6000)
    return parser


def _load_capsule(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"unable to read Memory Capsule JSON: {path}") from error
    if not isinstance(value, dict):
        raise ValueError("Memory Capsule JSON must contain an object")
    return value


def _print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "install":
            _print_json(install_memory(args.root, _load_capsule(args.capsule)))
            return 0
        if args.command == "list":
            _print_json(list_installed_memories(args.root))
            return 0
        matches = match_installed_memories(args.root, args.text, limit=args.limit)
        _print_json(
            {
                "matches": [asdict(match) for match in matches],
                "context_packet": build_context_packet(
                    matches,
                    max_chars=args.max_context_chars,
                ),
            }
        )
        return 0
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
