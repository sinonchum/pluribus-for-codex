from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI

from app.api.missions import router as missions_router
from app.db import Database
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

    application = FastAPI(title="Pluribus for Codex API", version="0.1.0")
    application.state.database = database
    application.state.mission_controller = mission_controller
    application.include_router(missions_router)

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
