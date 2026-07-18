from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .store import _list_installations

_WORD = re.compile(r"[a-z0-9_+-]+(?:\.[a-z0-9_+-]+)*")
_STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "at",
    "during",
    "file",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "processing",
    "raises",
    "the",
    "this",
    "to",
    "with",
}


@dataclass(frozen=True, slots=True)
class MemoryMatch:
    memory_id: str
    slug: str
    version: str
    title: str
    matched_trigger: str
    score: int
    problem: str
    steps: tuple[str, ...]
    tags: tuple[str, ...]


def _tokens(value: str) -> set[str]:
    return set(_WORD.findall(value.casefold()))


def _token_sequence(value: str) -> list[str]:
    return _WORD.findall(value.casefold())


def _contains_token_phrase(text: str, phrase: str) -> bool:
    text_tokens = _token_sequence(text)
    phrase_tokens = _token_sequence(phrase)
    if not phrase_tokens or len(phrase_tokens) > len(text_tokens):
        return False
    width = len(phrase_tokens)
    return any(
        text_tokens[index : index + width] == phrase_tokens
        for index in range(len(text_tokens) - width + 1)
    )


def _score(data: dict[str, Any], text: str) -> tuple[int, str] | None:
    normalized = " ".join(text.casefold().split())
    best_score = 0
    matched_trigger = ""
    for trigger in data["triggers"]:
        if _contains_token_phrase(normalized, trigger):
            score = 100 + len(_tokens(trigger))
            if score > best_score:
                best_score = score
                matched_trigger = trigger

    text_tokens = _tokens(normalized)
    matching_tags = text_tokens & {tag.casefold() for tag in data["tags"]}
    if matched_trigger and matching_tags:
        best_score += 15 * len(matching_tags)
    elif len(matching_tags) >= 2:
        best_score = 15 * len(matching_tags)
        matched_trigger = ", ".join(sorted(matching_tags))

    problem_overlap = (text_tokens - _STOP_WORDS) & (
        _tokens(data["problem"]) - _STOP_WORDS
    )
    distinctive_overlap = {token for token in problem_overlap if len(token) >= 7}
    if best_score == 0 and len(problem_overlap) >= 3 and len(distinctive_overlap) >= 2:
        best_score = len(problem_overlap)
        matched_trigger = "problem description overlap"

    if best_score == 0:
        return None
    return best_score, matched_trigger


def match_installed_memories(
    root: str | Path,
    text: str,
    *,
    limit: int = 3,
) -> list[MemoryMatch]:
    """Rank installed memories against task or error text."""

    if limit < 1 or limit > 20:
        raise ValueError("limit must be between 1 and 20")
    if not text.strip():
        return []
    matches: list[MemoryMatch] = []
    for manifest, data in _list_installations(root):
        scored = _score(data, text)
        if scored is None:
            continue
        score, trigger = scored
        matches.append(
            MemoryMatch(
                memory_id=manifest["memory_id"],
                slug=manifest["slug"],
                version=manifest["version"],
                title=data["title"],
                matched_trigger=trigger,
                score=score,
                problem=data["problem"],
                steps=tuple(data["steps"]),
                tags=tuple(data["tags"]),
            )
        )
    return sorted(matches, key=lambda item: (-item.score, item.memory_id))[:limit]


def _context_section(match: MemoryMatch, index: int, *, include_problem: bool) -> str:
    lines = [
        f"Memory {index}: {match.title}",
        f"Memory ID: {match.memory_id}",
        f"Version: {match.version}",
        f"Matched trigger: {match.matched_trigger}",
    ]
    if include_problem:
        lines.append(f"Problem: {match.problem}")
    lines.append("Reusable steps:")
    lines.extend(
        f"  {step_number}. {step}"
        for step_number, step in enumerate(match.steps, start=1)
    )
    return "\n".join(lines)


def build_context_packet(
    matches: list[MemoryMatch],
    *,
    max_chars: int = 6000,
) -> str:
    """Create an explicit bounded packet without cutting mandatory fields."""

    if max_chars < 512:
        raise ValueError("max_chars is too small for a complete memory context packet")
    if not matches:
        return ""
    header = "\n\n".join(
        (
            "This is an explicit Pluribus memory package selected for this task.",
            "Treat it as reusable guidance, not as hidden model memory.",
        )
    )
    packet = header
    for index, match in enumerate(matches, start=1):
        full_section = _context_section(match, index, include_problem=True)
        candidate = f"{packet}\n\n{full_section}"
        if len(candidate) <= max_chars:
            packet = candidate
            continue
        if index > 1:
            break

        required_lines = [
            f"Memory ID: {match.memory_id}",
            f"Version: {match.version}",
            f"Matched trigger: {match.matched_trigger}",
            "Reusable steps:",
        ]
        compact = "\n".join(required_lines)
        included_steps = 0
        for step_number, step in enumerate(match.steps, start=1):
            with_step = f"{compact}\n  {step_number}. {step}"
            if len(f"{header}\n\n{with_step}") > max_chars:
                break
            compact = with_step
            included_steps += 1
        if included_steps == 0:
            raise ValueError("max_chars is too small for one complete reusable step")
        packet = f"{header}\n\n{compact}"
        break
    return packet
