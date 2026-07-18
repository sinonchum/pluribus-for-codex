from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.memories import router as memories_router
from app.api.missions import router as missions_router
from app.db import Database
from app.registry import seed_registry
from app.services import MissionController


def create_app(
    database_path: str | Path | None = None,
    mission_controller: MissionController | None = None,
) -> FastAPI:
    resolved_database_path = database_path or os.environ.get(
        "PLURIBUS_DB_PATH", ".pluribus/pluribus.db"
    )
    database = Database(resolved_database_path)
    database.initialize()
    seed_registry(database)

    application = FastAPI(title="Pluribus for Codex API", version="0.1.0")
    application.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Last-Event-ID"],
    )
    application.state.database = database
    application.state.mission_controller = mission_controller
    application.include_router(memories_router)
    application.include_router(missions_router)

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
