from __future__ import annotations

from typing import Any, Protocol


class MissionController(Protocol):
    """Boundary implemented by the orchestration workstream."""

    async def start(self, mission_id: str) -> dict[str, Any]: ...

    async def stop(self, mission_id: str) -> None: ...
