from __future__ import annotations

from pathlib import Path

import pytest

from app.memory_runtime.matching import build_context_packet, match_installed_memories
from app.memory_runtime.store import install_memory


def test_pytest_error_selects_seeded_memory(
    tmp_path: Path, capsule: dict[str, object]
) -> None:
    install_memory(tmp_path, capsule)

    matches = match_installed_memories(
        tmp_path,
        "pytest import file mismatch in duplicate test_runner.py",
    )

    assert len(matches) == 1
    assert matches[0].memory_id == "mem_pytest_importlib_v1"
    assert matches[0].version == "1.0.0"
    assert matches[0].matched_trigger == "import file mismatch"
    assert matches[0].score > 0


def test_unrelated_task_does_not_select_memory(
    tmp_path: Path, capsule: dict[str, object]
) -> None:
    install_memory(tmp_path, capsule)

    assert match_installed_memories(tmp_path, "change the landing page color") == []


def test_context_packet_is_bounded_and_contains_causal_fields(
    tmp_path: Path, capsule: dict[str, object]
) -> None:
    install_memory(tmp_path, capsule)
    matches = match_installed_memories(
        tmp_path, "duplicate test module caused an import file mismatch"
    )

    packet = build_context_packet(matches, max_chars=2000)

    assert len(packet) <= 2000
    assert "mem_pytest_importlib_v1" in packet
    assert "Version: 1.0.0" in packet
    assert "Matched trigger: import file mismatch" in packet
    assert "--import-mode=importlib" in packet
    assert "explicit Pluribus memory package" in packet


def test_context_packet_respects_tight_character_limit(
    tmp_path: Path, capsule: dict[str, object]
) -> None:
    install_memory(tmp_path, capsule)
    matches = match_installed_memories(tmp_path, "import file mismatch")

    with pytest.raises(ValueError, match="too small"):
        build_context_packet(matches, max_chars=180)


def test_single_broad_tag_does_not_match_unrelated_task(
    tmp_path: Path, capsule: dict[str, object]
) -> None:
    install_memory(tmp_path, capsule)

    assert match_installed_memories(tmp_path, "Update a Python class") == []


def test_multiple_specific_tags_can_match_without_exact_trigger(
    tmp_path: Path, capsule: dict[str, object]
) -> None:
    install_memory(tmp_path, capsule)

    matches = match_installed_memories(
        tmp_path, "Investigate a pytest debugging problem"
    )

    assert matches[0].memory_id == "mem_pytest_importlib_v1"
    assert matches[0].matched_trigger == "debugging, pytest"


def test_generic_problem_words_do_not_create_false_positive(
    tmp_path: Path, capsule: dict[str, object]
) -> None:
    install_memory(tmp_path, capsule)

    assert (
        match_installed_memories(tmp_path, "It raises a file during processing") == []
    )


def test_trigger_matching_respects_token_boundaries(
    tmp_path: Path, capsule: dict[str, object]
) -> None:
    capsule["triggers"] = ["go"]
    install_memory(tmp_path, capsule)

    assert match_installed_memories(tmp_path, "Upgrade the Django application") == []


def test_two_generic_problem_words_do_not_match(
    tmp_path: Path, capsule: dict[str, object]
) -> None:
    capsule["problem"] = "A software application crashes unexpectedly."
    capsule["triggers"] = ["specific crash signature"]
    install_memory(tmp_path, capsule)

    assert match_installed_memories(tmp_path, "Review the software application") == []


def test_three_distinctive_problem_terms_can_match(
    tmp_path: Path, capsule: dict[str, object]
) -> None:
    install_memory(tmp_path, capsule)

    matches = match_installed_memories(tmp_path, "pytest collection mismatch")

    assert matches[0].memory_id == "mem_pytest_importlib_v1"
    assert matches[0].matched_trigger == "problem description overlap"
