import json

from backend.app.adapters.codex import parse_handoff


def valid_payload(**overrides):
    payload = {
        "status": "completed",
        "summary": "done",
        "changed_files": ["src/health.py"],
        "self_reported_commands": [],
        "consumed_patch_ids": ["kp_1"],
        "knowledge_usage": [
            {
                "patch_id": "kp_1",
                "effect": "Reused the service.",
                "changed_files": ["src/health.py"],
            }
        ],
        "knowledge_patches": [],
        "risks": [],
    }
    payload.update(overrides)
    return payload


def test_parses_marker_delimited_handoff_and_preserves_raw_output():
    raw = "prose\n<PLURIBUS_HANDOFF>\n" + json.dumps(valid_payload()) + "\n</PLURIBUS_HANDOFF>"

    result = parse_handoff(raw)

    assert result.parsed
    assert result.handoff is not None
    assert result.handoff.consumed_patch_ids == ("kp_1",)
    assert result.raw_output == raw
    assert result.extraction_method == "marker-delimited"


def test_parses_final_fenced_json():
    result = parse_handoff("Result:\n```json\n" + json.dumps(valid_payload()) + "\n```")
    assert result.parsed
    assert result.extraction_method == "fenced-json"


def test_malformed_json_is_safe_and_preserved():
    raw = "<PLURIBUS_HANDOFF>{bad}</PLURIBUS_HANDOFF>"
    result = parse_handoff(raw)
    assert not result.parsed
    assert result.raw_output == raw
    assert "Invalid structured handoff" in result.error


def test_rejects_unsafe_paths_invalid_confidence_and_line_ranges():
    unsafe = parse_handoff(
        "<PLURIBUS_HANDOFF>"
        + json.dumps(valid_payload(changed_files=["../secret"]))
        + "</PLURIBUS_HANDOFF>"
    )
    assert not unsafe.parsed
    patch = {
        "type": "repository_fact",
        "summary": "fact",
        "details": "details",
        "confidence": 1.1,
        "evidence": [],
        "tags": [],
        "relevant_to": [],
    }
    confidence = parse_handoff(
        "<PLURIBUS_HANDOFF>"
        + json.dumps(valid_payload(knowledge_patches=[patch]))
        + "</PLURIBUS_HANDOFF>"
    )
    assert not confidence.parsed
    patch["confidence"] = 0.8
    patch["evidence"] = [
        {"type": "file_reference", "path": "a.py", "line_start": 3, "line_end": 2}
    ]
    lines = parse_handoff(
        "<PLURIBUS_HANDOFF>"
        + json.dumps(valid_payload(knowledge_patches=[patch]))
        + "</PLURIBUS_HANDOFF>"
    )
    assert not lines.parsed


def test_rejects_usage_without_consumed_flag_and_ambiguous_markers():
    inconsistent = parse_handoff(
        "<PLURIBUS_HANDOFF>"
        + json.dumps(valid_payload(consumed_patch_ids=[]))
        + "</PLURIBUS_HANDOFF>"
    )
    assert not inconsistent.parsed
    one = "<PLURIBUS_HANDOFF>" + json.dumps(valid_payload()) + "</PLURIBUS_HANDOFF>"
    ambiguous = parse_handoff(one + one)
    assert not ambiguous.parsed
    assert "Ambiguous" in ambiguous.error


def test_top_level_fallback_handles_nested_objects_and_rejects_multiple_roots():
    raw = "final result: " + json.dumps(valid_payload())
    result = parse_handoff(raw)
    assert result.parsed
    assert result.extraction_method == "top-level-json"
    ambiguous = parse_handoff(raw + " " + json.dumps(valid_payload()))
    assert not ambiguous.parsed
    assert "Ambiguous" in ambiguous.error


def test_missing_fields_unknown_enum_absolute_path_and_bad_patch_id_are_clear():
    missing = parse_handoff("<PLURIBUS_HANDOFF>{}</PLURIBUS_HANDOFF>")
    assert not missing.parsed
    unknown = parse_handoff(
        "<PLURIBUS_HANDOFF>"
        + json.dumps(valid_payload(status="mystery"))
        + "</PLURIBUS_HANDOFF>"
    )
    assert not unknown.parsed and "Unknown handoff status" in unknown.error
    absolute = parse_handoff(
        "<PLURIBUS_HANDOFF>"
        + json.dumps(valid_payload(changed_files=["C:\\secret.txt"]))
        + "</PLURIBUS_HANDOFF>"
    )
    assert not absolute.parsed and "repository-relative" in absolute.error
    bad_id = parse_handoff(
        "<PLURIBUS_HANDOFF>"
        + json.dumps(valid_payload(consumed_patch_ids=["bad id"], knowledge_usage=[]))
        + "</PLURIBUS_HANDOFF>"
    )
    assert not bad_id.parsed and "lowercase" in bad_id.error


def test_duplicate_consumed_patch_ids_are_removed_in_first_seen_order():
    result = parse_handoff(
        "<PLURIBUS_HANDOFF>"
        + json.dumps(valid_payload(consumed_patch_ids=["kp_1", "KP_1", "kp_2"], knowledge_usage=[]))
        + "</PLURIBUS_HANDOFF>"
    )
    assert result.parsed
    assert result.handoff.consumed_patch_ids == ("kp_1", "kp_2")
