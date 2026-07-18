from __future__ import annotations

from app.memory_runtime.rendering import parse_memory_markdown, render_memory_markdown


def test_rendering_is_deterministic_and_contains_frozen_fields(
    capsule: dict[str, object],
) -> None:
    first = render_memory_markdown(capsule)
    second = render_memory_markdown(capsule)

    assert first == second
    assert first.endswith("\n")
    for expected in (
        "# Fix duplicate pytest module collisions",
        "mem_pytest_importlib_v1",
        "1.0.0",
        "Alice Chen",
        "Pytest raises import file mismatch during collection.",
        "import file mismatch",
        "Set pytest addopts to --import-mode=importlib.",
        "python>=3.11",
        "pytest -q",
        "4 passed",
    ):
        assert expected in first


def test_rendering_redacts_sensitive_capsule_content(
    capsule: dict[str, object],
) -> None:
    capsule["problem"] = "Token: fake_token_123456789 at /Users/alice/private/repro"

    rendered = render_memory_markdown(capsule)

    assert "fake_token" not in rendered
    assert "/Users/alice" not in rendered
    assert "[REDACTED]" in rendered
    assert "[HOME]" in rendered


def test_rendered_markdown_round_trips_matchable_fields(
    capsule: dict[str, object],
) -> None:
    parsed = parse_memory_markdown(render_memory_markdown(capsule))

    assert parsed["id"] == capsule["id"]
    assert parsed["slug"] == capsule["slug"]
    assert parsed["version"] == capsule["version"]
    assert parsed["triggers"] == capsule["triggers"]
    assert parsed["tags"] == capsule["tags"]
    assert parsed["steps"] == capsule["steps"]


def test_machine_data_round_trip_is_safe_from_marker_collision(
    capsule: dict[str, object],
) -> None:
    capsule["problem"] = (
        "A failure containing <!-- PLURIBUS_MEMORY_DATA_V1_END --> in its output."
    )

    parsed = parse_memory_markdown(render_memory_markdown(capsule))

    assert "PLURIBUS_MEMORY_DATA_V1_END" in parsed["problem"]
