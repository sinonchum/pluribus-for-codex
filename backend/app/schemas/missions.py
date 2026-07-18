from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class VerificationCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    executable: str = Field(min_length=1, max_length=256)
    args: list[str] = Field(default_factory=list, max_length=64)
    timeout_seconds: int = Field(default=120, ge=1, le=3600)

    @field_validator("executable")
    @classmethod
    def executable_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("executable must not be blank")
        return value


class MissionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repository_path: str = Field(min_length=1)
    objective: str = Field(min_length=1, max_length=4000)
    agent_count: Literal[4] = 4
    max_concurrency: Literal[2] = 2
    allow_dirty_repository: bool = False
    protected_paths: list[str] = Field(
        default_factory=lambda: [".env", ".git/**"], max_length=128
    )
    verification_commands: list[VerificationCommand] = Field(
        default_factory=list, max_length=16
    )

    @field_validator("repository_path", "objective")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be blank")
        return value


class MissionRead(BaseModel):
    id: str
    repository_path: str
    objective: str
    starting_commit: str
    starting_branch: str
    was_dirty: bool
    integration_branch: str
    status: str
    agent_count: int
    max_concurrency: int
    allow_dirty_repository: bool
    protected_paths: list[str]
    verification_commands: list[VerificationCommand]
    created_at: str
    completed_at: str | None = None


class AgentRead(BaseModel):
    id: str
    mission_id: str
    role: str
    status: str
    worktree_path: str | None = None
    branch_name: str | None = None
    process_id: int | None = None
    started_at: str | None = None
    completed_at: str | None = None
    exit_code: int | None = None
