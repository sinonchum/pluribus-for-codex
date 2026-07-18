import pytest

from backend.app.prompts import AgentRole, PromptKnowledge, PromptRequest, render_prompt


def prompt_request(role):
    return PromptRequest(
        mission_id="mission_1",
        agent_id=f"{role.value}_1",
        role=role,
        mission_objective="Add health details.",
        assigned_task="Handle health behavior.",
        repository_baseline="abc123",
        working_directory="/work/repo",
        hive_knowledge=(
            PromptKnowledge("kp_verified", "execution_verified", "Tests pass."),
            PromptKnowledge(
                "kp_018",
                "source_linked",
                "HealthService exists.",
                ("src/health.py:4-8",),
            ),
        ),
        active_constraints=("No dependencies.",),
        relevant_risks=("Do not leak errors.",),
        allowed_paths=("src/health.py",),
        protected_paths=("src/auth/**",),
        delivered_patch_ids=("kp_018",),
    )


@pytest.mark.parametrize("role", list(AgentRole))
def test_all_role_prompts_are_deterministic_and_structured(role):
    request = prompt_request(role)
    first = render_prompt(request)
    assert first == render_prompt(request)
    for heading in (
        "Mission",
        "Agent identity",
        "Role",
        "Assigned task",
        "Repository baseline",
        "Working directory",
        "Verified Hive knowledge",
        "Source-linked Hive knowledge",
        "Active constraints",
        "Relevant risks",
        "Allowed paths",
        "Protected paths",
        "Delivered patch IDs",
        "Role-specific instructions",
        "Expected output contract",
    ):
        assert f"## {heading}" in first
    assert "[execution_verified] kp_verified" in first
    assert "[source_linked] kp_018" in first
    assert "src/health.py:4-8" in first


def test_builder_receives_explicit_causal_consumption_rules():
    rendered = render_prompt(prompt_request(AgentRole.BUILDER))
    assert "merely because it was delivered" in rendered
    assert "Every knowledge_usage.patch_id must appear in consumed_patch_ids" in rendered
    assert "src/health.py" in rendered
    assert "src/auth/**" in rendered
