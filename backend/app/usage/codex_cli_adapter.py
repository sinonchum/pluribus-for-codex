from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from app.memory_runtime.matching import build_context_packet, match_installed_memories

MEMORY_ID = "mem_billing_audit_handoff_v1"
TASK_TEXT = (
    "Add a new CANCELLED invoice status and implement cancel_invoice in Northstar "
    "Billing Service without breaking the append-only financial audit trail."
)
EXPECTED_CHANGED_FILES = ["billing/invoices.py"]
_RESULT_KEYS = {
    "memory_id",
    "matched_trigger",
    "injected_into_codex",
    "codex_reported_use",
    "effect",
    "changed_files",
}
_RESULT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": sorted(_RESULT_KEYS),
    "properties": {
        "memory_id": {"type": "string"},
        "matched_trigger": {"type": "string"},
        "injected_into_codex": {"type": "boolean"},
        "codex_reported_use": {"type": "boolean"},
        "effect": {"type": "string"},
        "changed_files": {"type": "array", "items": {"type": "string"}},
    },
}


def _prompt(installed_memory_root: Path) -> str:
    matches = match_installed_memories(installed_memory_root, TASK_TEXT, limit=1)
    if not matches:
        raise ValueError("no installed Pluribus handoff memory matched the live task")
    packet = build_context_packet(matches, max_chars=6000)
    return f"""You are Bob, the successor engineer taking over Northstar Billing Service after
Alice Chen, its four-year maintainer, left the team.

Complete this bounded task in the current workspace:

{TASK_TEXT}

## Explicit installed Pluribus handoff memory
{packet}

Use Alice's company-specific rule. Modify exactly billing/invoices.py. Add CANCELLED to
InvoiceStatus and implement cancel_invoice(invoice, ledger). The function must call the
existing transition_invoice() primitive with reason \"customer_request\"; never assign
invoice.status directly. Do not modify tests, pyproject.toml, or any other file.

You may inspect files and run tests. When finished, return the required JSON proof. Set
injected_into_codex and codex_reported_use to true only because the explicit handoff memory
above was present and used. Report changed_files as [\"billing/invoices.py\"].
"""


def _validate_result(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict) or set(payload) != _RESULT_KEYS:
        raise ValueError("Codex CLI returned an invalid usage proof shape")
    if payload["memory_id"] != MEMORY_ID:
        raise ValueError("Codex CLI reported an unexpected memory")
    if payload["injected_into_codex"] is not True:
        raise ValueError("Codex CLI did not confirm explicit memory injection")
    if payload["codex_reported_use"] is not True:
        raise ValueError("Codex CLI did not confirm memory use")
    if payload["changed_files"] != EXPECTED_CHANGED_FILES:
        raise ValueError("Codex CLI reported an unexpected workspace delta")
    for key in ("matched_trigger", "effect"):
        if not isinstance(payload[key], str) or not payload[key].strip():
            raise ValueError(f"Codex CLI returned an invalid {key}")
    return payload


def run_codex_cli_usage(
    installed_memory_root: str | Path,
    workspace: str | Path,
    *,
    codex_executable: str = "codex",
    timeout_seconds: float = 150,
) -> dict[str, Any]:
    root = Path(installed_memory_root).resolve()
    workdir = Path(workspace).resolve()
    if not root.is_dir() or not workdir.is_dir():
        raise NotADirectoryError("installed memory root and workspace must exist")

    prompt = _prompt(root)
    with tempfile.TemporaryDirectory(prefix="pluribus-codex-") as temp_dir:
        temp = Path(temp_dir)
        schema_path = temp / "usage-proof.schema.json"
        output_path = temp / "usage-proof.json"
        schema_path.write_text(json.dumps(_RESULT_SCHEMA), encoding="utf-8")
        command = (
            codex_executable,
            "exec",
            "--ephemeral",
            "--sandbox",
            "workspace-write",
            "--skip-git-repo-check",
            "--color",
            "never",
            "-C",
            str(workdir),
            "--output-schema",
            str(schema_path),
            "-o",
            str(output_path),
            "-",
        )
        completed = subprocess.run(
            command,
            input=prompt,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"Codex CLI failed with exit code {completed.returncode}: "
                f"{completed.stderr[-1000:]}"
            )
        try:
            payload = json.loads(output_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError("Codex CLI did not produce valid JSON proof") from error
    return _validate_result(payload)
