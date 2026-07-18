from __future__ import annotations

from app.db import Database
from app.schemas.memories import MemoryCapsule

SEEDED_MEMORY = MemoryCapsule.model_validate(
    {
        "id": "mem_pytest_importlib_v1",
        "slug": "fix-pytest-module-collisions",
        "title": "Fix duplicate pytest module collisions",
        "summary": "Use pytest importlib mode when duplicate test module names collide.",
        "problem": "Pytest raises import file mismatch during collection.",
        "triggers": [
            "import file mismatch",
            "duplicate test module",
            "test_runner.py collision",
        ],
        "steps": [
            "Confirm the collision is caused by duplicate test module basenames.",
            "Set pytest addopts to --import-mode=importlib.",
            "Run the full suite and preserve the output as evidence.",
        ],
        "tags": ["python", "pytest", "debugging", "codex"],
        "author": {"id": "dev_alice", "display_name": "Alice Chen"},
        "version": "1.0.0",
        "compatibility": ["python>=3.11", "pytest>=8"],
        "status": "verified",
        "verification": {
            "command": ["pytest", "-q"],
            "exit_code": 0,
            "passed": 4,
            "evidence_excerpt": "4 passed",
        },
        "stars": 128,
        "installs": 1402,
        "fork_of": None,
        "created_at": "2026-07-18T10:00:00Z",
    }
)


def seed_registry(database: Database) -> None:
    database.create_memory(
        SEEDED_MEMORY.model_dump(mode="json"),
        ignore_existing=True,
    )
