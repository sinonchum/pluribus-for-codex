from __future__ import annotations

from typing import Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MemoryAuthor(FrozenModel):
    id: str = Field(min_length=1, max_length=128)
    display_name: str = Field(min_length=1, max_length=256)


class MemoryVerification(FrozenModel):
    command: list[str] = Field(min_length=1, max_length=64)
    exit_code: int
    passed: int = Field(ge=0)
    evidence_excerpt: str = Field(min_length=1, max_length=4000)

    @field_validator("command")
    @classmethod
    def command_parts_must_not_be_blank(cls, value: list[str]) -> list[str]:
        if any(not part.strip() for part in value):
            raise ValueError("verification command parts must not be blank")
        if any(len(part) > 512 for part in value):
            raise ValueError(
                "verification command parts must be at most 512 characters"
            )
        return value


class MemoryCapsule(FrozenModel):
    id: str = Field(min_length=1, max_length=128)
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=128)
    title: str = Field(min_length=1, max_length=256)
    summary: str = Field(min_length=1, max_length=1000)
    problem: str = Field(min_length=1, max_length=4000)
    triggers: list[str] = Field(min_length=1, max_length=32)
    steps: list[str] = Field(min_length=1, max_length=64)
    tags: list[str] = Field(min_length=1, max_length=32)
    author: MemoryAuthor
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$", max_length=64)
    compatibility: list[str] = Field(default_factory=list, max_length=32)
    status: Literal["draft", "verified"]
    verification: MemoryVerification
    stars: int = Field(ge=0)
    installs: int = Field(ge=0)
    fork_of: str | None = Field(default=None, max_length=128)
    created_at: AwareDatetime

    @field_validator(
        "id",
        "title",
        "summary",
        "problem",
        "version",
    )
    @classmethod
    def scalar_text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be blank")
        return value

    @field_validator("triggers", "tags", "compatibility")
    @classmethod
    def short_list_text_must_be_bounded(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("list entries must not be blank")
        if any(len(item) > 500 for item in value):
            raise ValueError("list entries must be at most 500 characters")
        return value

    @field_validator("steps")
    @classmethod
    def steps_must_be_bounded(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("steps must not be blank")
        if any(len(item) > 4000 for item in value):
            raise ValueError("steps must be at most 4000 characters")
        return value

    @model_validator(mode="after")
    def verified_memory_requires_passing_evidence(self) -> MemoryCapsule:
        if self.status == "verified" and (
            self.verification.exit_code != 0 or self.verification.passed < 1
        ):
            raise ValueError("verified memories require passing verification evidence")
        return self


class MemoryStar(FrozenModel):
    memory_id: str
    slug: str
    starred: bool
    stars: int = Field(ge=0)


class MemoryInstall(FrozenModel):
    id: str
    memory_id: str
    slug: str
    version: str
    consumer: str
    installed_at: str


class UsageReceiptVerification(FrozenModel):
    command: list[str] = Field(min_length=1, max_length=64)
    exit_code: int
    output_excerpt: str


class UsageReceiptSummary(FrozenModel):
    id: str
    memory_id: str
    consumer: str
    matched_trigger: str
    injected_into_codex: bool
    codex_reported_use: bool
    effect: str
    changed_files: list[str]
    verification: UsageReceiptVerification
    created_at: str


class RegistryStats(FrozenModel):
    published: int = Field(ge=0)
    verified: int = Field(ge=0)
    installs: int = Field(ge=0)
    successful_uses: int = Field(ge=0)


class DemoSnapshot(FrozenModel):
    featured_memories: list[MemoryCapsule]
    installed_memories: list[MemoryCapsule]
    latest_receipt: UsageReceiptSummary | None = None
    stats: RegistryStats
