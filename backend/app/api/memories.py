from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.db import Database
from app.schemas.memories import (
    DemoSnapshot,
    MemoryCapsule,
    MemoryInstall,
    MemoryStar,
)

router = APIRouter(tags=["memories"])
DEMO_USER = "dev_bob"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _database(request: Request) -> Database:
    return request.app.state.database


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail={"code": "memory_not_found"})


@router.get("/api/memories", response_model=list[MemoryCapsule])
def list_memories(
    request: Request,
    query: str | None = Query(default=None, max_length=500),
    tag: str | None = Query(default=None, max_length=128),
    sort: Literal["featured", "stars", "installs", "newest"] = "featured",
) -> list[dict[str, object]]:
    return _database(request).list_memories(query=query, tag=tag, sort=sort)


@router.post(
    "/api/memories",
    response_model=MemoryCapsule,
    status_code=status.HTTP_201_CREATED,
)
def create_memory(payload: MemoryCapsule, request: Request) -> dict[str, object]:
    capsule = payload.model_dump(mode="json")
    try:
        _database(request).create_memory(capsule)
    except sqlite3.IntegrityError as error:
        raise HTTPException(
            status_code=409,
            detail={"code": "memory_already_exists"},
        ) from error
    return capsule


@router.get("/api/memories/{slug}", response_model=MemoryCapsule)
def get_memory(slug: str, request: Request) -> dict[str, object]:
    memory = _database(request).get_memory(slug)
    if memory is None:
        raise _not_found()
    return memory


@router.post("/api/memories/{slug}/star", response_model=MemoryStar)
def star_memory(slug: str, request: Request) -> dict[str, object]:
    result = _database(request).star_memory(
        slug=slug,
        user_id=DEMO_USER,
        created_at=_now(),
    )
    if result is None:
        raise _not_found()
    return result


@router.post("/api/memories/{slug}/install", response_model=MemoryInstall)
def install_memory(slug: str, request: Request) -> dict[str, object]:
    result = _database(request).install_memory(
        slug=slug,
        install_id=f"install_{uuid4().hex[:12]}",
        consumer=DEMO_USER,
        installed_at=_now(),
    )
    if result is None:
        raise _not_found()
    return result


@router.get("/api/installed", response_model=list[MemoryCapsule])
def list_installed_memories(request: Request) -> list[dict[str, object]]:
    return _database(request).list_installed_memories(DEMO_USER)


@router.get("/api/demo/snapshot", response_model=DemoSnapshot)
def get_demo_snapshot(request: Request) -> dict[str, object]:
    database = _database(request)
    return {
        "featured_memories": database.list_memories(sort="featured"),
        "installed_memories": database.list_installed_memories(DEMO_USER),
        "latest_receipt": None,
        "stats": database.registry_stats(),
    }
