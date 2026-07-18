"""Deterministic extraction and validation of final agent handoffs."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable

from .models import AgentHandoff, HandoffParseResult

START_MARKER = "<PLURIBUS_HANDOFF>"
END_MARKER = "</PLURIBUS_HANDOFF>"
_FENCED_JSON = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)


def _marked_candidates(output: str) -> list[str]:
    candidates: list[str] = []
    position = 0
    while True:
        start = output.find(START_MARKER, position)
        if start < 0:
            return candidates
        end = output.find(END_MARKER, start + len(START_MARKER))
        if end < 0:
            candidates.append(output[start + len(START_MARKER) :])
            return candidates
        candidates.append(output[start + len(START_MARKER) : end].strip())
        position = end + len(END_MARKER)


def _top_level_json_candidates(output: str) -> list[str]:
    candidates: list[str] = []
    start: int | None = None
    depth = 0
    in_string = False
    escaped = False
    for index, character in enumerate(output):
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"' and depth:
            in_string = True
        elif character == "{":
            if depth == 0:
                start = index
            depth += 1
        elif character == "}" and depth:
            depth -= 1
            if depth == 0 and start is not None:
                payload = output[start : index + 1]
                try:
                    if isinstance(json.loads(payload), dict):
                        candidates.append(payload)
                except json.JSONDecodeError:
                    pass
                start = None
    return candidates


def _parse_candidate(raw_output: str, payload: str, method: str) -> HandoffParseResult:
    try:
        decoded = json.loads(payload)
        handoff = AgentHandoff.from_dict(decoded)
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        return HandoffParseResult(
            handoff=None,
            parsed=False,
            raw_output=raw_output,
            raw_payload=payload,
            extraction_method=method,
            error=f"Invalid structured handoff: {exc}",
        )
    return HandoffParseResult(
        handoff=handoff,
        parsed=True,
        raw_output=raw_output,
        raw_payload=payload,
        extraction_method=method,
    )


def _ambiguous(
    raw_output: str, candidates: Iterable[str], method: str
) -> HandoffParseResult:
    count = len(tuple(candidates))
    return HandoffParseResult(
        handoff=None,
        parsed=False,
        raw_output=raw_output,
        extraction_method=method,
        error=f"Ambiguous structured output: found {count} {method} payloads.",
    )


def parse_handoff(raw_output: str) -> HandoffParseResult:
    """Prefer exact markers, then fenced JSON, then one top-level object."""

    marked = _marked_candidates(raw_output)
    if len(marked) > 1:
        return _ambiguous(raw_output, marked, "marker-delimited")
    if len(marked) == 1:
        if END_MARKER not in raw_output:
            return HandoffParseResult(
                None,
                False,
                raw_output,
                marked[0],
                "marker-delimited",
                f"Missing closing marker {END_MARKER}.",
            )
        return _parse_candidate(raw_output, marked[0], "marker-delimited")

    fenced = [match.group(1).strip() for match in _FENCED_JSON.finditer(raw_output)]
    if len(fenced) > 1:
        return _ambiguous(raw_output, fenced, "fenced-json")
    if len(fenced) == 1:
        return _parse_candidate(raw_output, fenced[0], "fenced-json")

    top_level = _top_level_json_candidates(raw_output)
    if len(top_level) > 1:
        return _ambiguous(raw_output, top_level, "top-level-json")
    if len(top_level) == 1:
        return _parse_candidate(raw_output, top_level[0], "top-level-json")
    return HandoffParseResult(
        handoff=None,
        parsed=False,
        raw_output=raw_output,
        error="No structured handoff payload was found.",
    )
