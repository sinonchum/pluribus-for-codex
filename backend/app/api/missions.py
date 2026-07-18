from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse

from app.db import Database
from app.schemas import AgentRead, MissionCreate, MissionRead
from app.services import inspect_repository
from app.services.repository_inspector import RepositoryInspectionError

router = APIRouter(prefix="/api/missions", tags=["missions"])
ROLES = ("scout", "builder", "tester", "reviewer")


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _database(request: Request) -> Database:
    return request.app.state.database


def _get_mission_or_404(database: Database, mission_id: str) -> dict[str, Any]:
    mission = database.get_mission(mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail={"code": "mission_not_found"})
    return mission


@router.post("", response_model=MissionRead, status_code=status.HTTP_201_CREATED)
def create_mission(payload: MissionCreate, request: Request) -> dict[str, Any]:
    try:
        baseline = inspect_repository(payload.repository_path)
    except RepositoryInspectionError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "not_a_git_repository", "message": str(error)},
        ) from error

    if baseline.is_dirty and not payload.allow_dirty_repository:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "dirty_repository",
                "message": "repository has uncommitted or untracked changes",
            },
        )

    mission_id = f"mission_{uuid4().hex[:12]}"
    mission = {
        "id": mission_id,
        "repository_path": str(baseline.root),
        "objective": payload.objective,
        "starting_commit": baseline.commit,
        "starting_branch": baseline.branch,
        "was_dirty": baseline.is_dirty,
        "integration_branch": f"pluribus/{mission_id}/integration",
        "status": "created",
        "agent_count": payload.agent_count,
        "max_concurrency": payload.max_concurrency,
        "allow_dirty_repository": payload.allow_dirty_repository,
        "protected_paths": payload.protected_paths,
        "verification_commands": [
            command.model_dump() for command in payload.verification_commands
        ],
        "created_at": _now(),
        "completed_at": None,
    }
    agents = [
        {
            "id": f"{role}_1",
            "mission_id": mission_id,
            "role": role,
            "status": "pending",
        }
        for role in ROLES
    ]
    return _database(request).create_mission(mission, agents)


@router.get("/{mission_id}", response_model=MissionRead)
def get_mission(mission_id: str, request: Request) -> dict[str, Any]:
    return _get_mission_or_404(_database(request), mission_id)


@router.post("/{mission_id}/start")
async def start_mission(mission_id: str, request: Request) -> dict[str, Any]:
    database = _database(request)
    _get_mission_or_404(database, mission_id)
    controller = getattr(request.app.state, "mission_controller", None)
    if controller is None:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "mission_controller_unavailable",
                "message": "orchestration service has not been configured",
            },
        )
    return await controller.start(mission_id)


@router.post("/{mission_id}/stop", response_model=MissionRead)
async def stop_mission(mission_id: str, request: Request) -> dict[str, Any]:
    database = _database(request)
    mission = _get_mission_or_404(database, mission_id)
    controller = getattr(request.app.state, "mission_controller", None)
    if controller is not None and mission["status"] in {"starting", "running"}:
        await controller.stop(mission_id)
    stopped = database.stop_mission(mission_id, _now())
    if stopped is None:  # pragma: no cover - guarded by lookup
        raise HTTPException(status_code=404, detail={"code": "mission_not_found"})
    return stopped


@router.get("/{mission_id}/agents/{agent_id}", response_model=AgentRead)
def get_agent(mission_id: str, agent_id: str, request: Request) -> dict[str, Any]:
    database = _database(request)
    _get_mission_or_404(database, mission_id)
    agent = database.get_agent(mission_id, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail={"code": "agent_not_found"})
    return agent


@router.get("/{mission_id}/knowledge")
def get_knowledge(mission_id: str, request: Request) -> list[dict[str, Any]]:
    database = _database(request)
    _get_mission_or_404(database, mission_id)
    return database.list_knowledge(mission_id)


@router.get("/{mission_id}/report")
def get_report(mission_id: str, request: Request) -> dict[str, Any]:
    database = _database(request)
    mission = _get_mission_or_404(database, mission_id)
    return {
        "mission": mission,
        "agents": database.list_agents(mission_id),
        "knowledge_patches": database.list_knowledge(mission_id),
        "events": database.list_events(mission_id),
    }


def _encode_sse(event: dict[str, Any]) -> str:
    return "".join(
        (
            f"id: {event['id']}\n",
            f"event: {event['event_type']}\n",
            f"data: {json.dumps(event['payload'], separators=(',', ':'))}\n\n",
        )
    )


@router.get("/{mission_id}/events")
async def get_events(
    mission_id: str,
    request: Request,
    follow: bool = Query(default=True),
) -> StreamingResponse:
    database = _database(request)
    _get_mission_or_404(database, mission_id)
    last_event_header = request.headers.get("last-event-id", "0")
    try:
        after_id = max(0, int(last_event_header))
    except ValueError:
        after_id = 0

    async def stream() -> AsyncIterator[str]:
        cursor = after_id
        while True:
            events = database.list_events(mission_id, cursor)
            for event in events:
                cursor = event["id"]
                yield _encode_sse(event)
            if not follow or await request.is_disconnected():
                break
            await asyncio.sleep(0.25)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
