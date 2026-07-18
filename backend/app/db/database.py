from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS missions (
  id TEXT PRIMARY KEY,
  repository_path TEXT NOT NULL,
  objective TEXT NOT NULL,
  starting_commit TEXT NOT NULL,
  starting_branch TEXT NOT NULL,
  was_dirty INTEGER NOT NULL CHECK (was_dirty IN (0, 1)),
  integration_branch TEXT NOT NULL,
  status TEXT NOT NULL,
  agent_count INTEGER NOT NULL,
  max_concurrency INTEGER NOT NULL,
  allow_dirty_repository INTEGER NOT NULL CHECK (allow_dirty_repository IN (0, 1)),
  protected_paths_json TEXT NOT NULL,
  verification_commands_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  completed_at TEXT
);

CREATE TABLE IF NOT EXISTS agents (
  id TEXT NOT NULL,
  mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
  role TEXT NOT NULL,
  status TEXT NOT NULL,
  worktree_path TEXT,
  branch_name TEXT,
  process_id INTEGER,
  started_at TEXT,
  completed_at TEXT,
  exit_code INTEGER,
  PRIMARY KEY (mission_id, id)
);

CREATE TABLE IF NOT EXISTS knowledge_patches (
  id TEXT PRIMARY KEY,
  mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
  agent_id TEXT NOT NULL,
  type TEXT NOT NULL,
  summary TEXT NOT NULL,
  details TEXT,
  evidence_json TEXT,
  tags_json TEXT,
  relevant_to_json TEXT,
  confidence REAL,
  status TEXT NOT NULL,
  baseline_commit TEXT NOT NULL,
  consumed_by_json TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
  agent_id TEXT,
  event_type TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_mission_id_id
  ON events(mission_id, id);
CREATE INDEX IF NOT EXISTS idx_patches_mission_id
  ON knowledge_patches(mission_id);

CREATE TABLE IF NOT EXISTS memories (
  id TEXT PRIMARY KEY,
  slug TEXT NOT NULL UNIQUE,
  capsule_json TEXT NOT NULL,
  searchable_text TEXT NOT NULL,
  status TEXT NOT NULL,
  stars INTEGER NOT NULL DEFAULT 0 CHECK (stars >= 0),
  installs INTEGER NOT NULL DEFAULT 0 CHECK (installs >= 0),
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS memory_stars (
  memory_id TEXT NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (memory_id, user_id)
);

CREATE TABLE IF NOT EXISTS memory_installs (
  id TEXT PRIMARY KEY,
  memory_id TEXT NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
  consumer TEXT NOT NULL,
  version TEXT NOT NULL,
  installed_at TEXT NOT NULL,
  UNIQUE (memory_id, consumer)
);

CREATE TABLE IF NOT EXISTS usage_receipts (
  id TEXT PRIMARY KEY,
  memory_id TEXT NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
  receipt_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_memories_slug ON memories(slug);
CREATE INDEX IF NOT EXISTS idx_memory_installs_consumer
  ON memory_installs(consumer);
CREATE INDEX IF NOT EXISTS idx_usage_receipts_created_at
  ON usage_receipts(created_at DESC, id DESC);
"""


class Database:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser().resolve()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(SCHEMA)

    def create_mission(
        self, mission: dict[str, Any], agents: list[dict[str, Any]]
    ) -> dict[str, Any]:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO missions (
                  id, repository_path, objective, starting_commit,
                  starting_branch, was_dirty, integration_branch, status,
                  agent_count, max_concurrency, allow_dirty_repository,
                  protected_paths_json, verification_commands_json,
                  created_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    mission["id"],
                    mission["repository_path"],
                    mission["objective"],
                    mission["starting_commit"],
                    mission["starting_branch"],
                    int(mission["was_dirty"]),
                    mission["integration_branch"],
                    mission["status"],
                    mission["agent_count"],
                    mission["max_concurrency"],
                    int(mission["allow_dirty_repository"]),
                    json.dumps(mission["protected_paths"]),
                    json.dumps(mission["verification_commands"]),
                    mission["created_at"],
                    mission.get("completed_at"),
                ),
            )
            connection.executemany(
                """
                INSERT INTO agents (id, mission_id, role, status)
                VALUES (:id, :mission_id, :role, :status)
                """,
                agents,
            )
            self._insert_event(
                connection,
                mission_id=mission["id"],
                event_type="mission.created",
                payload={"status": "created"},
                created_at=mission["created_at"],
            )
        result = self.get_mission(mission["id"])
        if result is None:  # pragma: no cover - defensive invariant
            raise RuntimeError("mission disappeared after insertion")
        return result

    def get_mission(self, mission_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM missions WHERE id = ?", (mission_id,)
            ).fetchone()
        return self._mission_from_row(row) if row else None

    def get_agent(self, mission_id: str, agent_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM agents WHERE mission_id = ? AND id = ?",
                (mission_id, agent_id),
            ).fetchone()
        return dict(row) if row else None

    def list_agents(self, mission_id: str) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM agents WHERE mission_id = ?
                ORDER BY CASE role
                  WHEN 'scout' THEN 1 WHEN 'builder' THEN 2
                  WHEN 'tester' THEN 3 WHEN 'reviewer' THEN 4 ELSE 5 END
                """,
                (mission_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_knowledge(self, mission_id: str) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM knowledge_patches
                WHERE mission_id = ? ORDER BY created_at, id
                """,
                (mission_id,),
            ).fetchall()
        return [self._knowledge_from_row(row) for row in rows]

    def list_events(self, mission_id: str, after_id: int = 0) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM events
                WHERE mission_id = ? AND id > ? ORDER BY id
                """,
                (mission_id, after_id),
            ).fetchall()
        return [self._event_from_row(row) for row in rows]

    def append_event(
        self,
        *,
        mission_id: str,
        event_type: str,
        payload: dict[str, Any],
        created_at: str,
        agent_id: str | None = None,
    ) -> dict[str, Any]:
        """Persist an orchestration event and return the stored event."""
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO events (
                  mission_id, agent_id, event_type, payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    mission_id,
                    agent_id,
                    event_type,
                    json.dumps(payload),
                    created_at,
                ),
            )
            row = connection.execute(
                "SELECT * FROM events WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
        if row is None:  # pragma: no cover - defensive invariant
            raise RuntimeError("event disappeared after insertion")
        return self._event_from_row(row)

    def transition_mission(
        self,
        *,
        mission_id: str,
        expected_statuses: set[str],
        new_status: str,
        event_type: str,
        payload: dict[str, Any],
        created_at: str,
        completed_at: str | None = None,
    ) -> dict[str, Any] | None:
        """Atomically change mission state and append its lifecycle event."""
        if not expected_statuses:
            raise ValueError("expected_statuses must not be empty")
        placeholders = ",".join("?" for _ in expected_statuses)
        with self.connect() as connection:
            cursor = connection.execute(
                f"""
                UPDATE missions
                SET status = ?, completed_at = COALESCE(?, completed_at)
                WHERE id = ? AND status IN ({placeholders})
                """,
                (
                    new_status,
                    completed_at,
                    mission_id,
                    *sorted(expected_statuses),
                ),
            )
            if cursor.rowcount == 0:
                return None
            self._insert_event(
                connection,
                mission_id=mission_id,
                event_type=event_type,
                payload=payload,
                created_at=created_at,
            )
        return self.get_mission(mission_id)

    def update_agent(
        self,
        *,
        mission_id: str,
        agent_id: str,
        status: str,
        created_at: str,
        worktree_path: str | None = None,
        branch_name: str | None = None,
        process_id: int | None = None,
        started_at: str | None = None,
        completed_at: str | None = None,
        exit_code: int | None = None,
    ) -> dict[str, Any] | None:
        """Update an agent and append the lifecycle event in one transaction."""
        with self.connect() as connection:
            cursor = connection.execute(
                """
                UPDATE agents SET
                  status = ?, worktree_path = COALESCE(?, worktree_path),
                  branch_name = COALESCE(?, branch_name),
                  process_id = COALESCE(?, process_id),
                  started_at = COALESCE(?, started_at),
                  completed_at = COALESCE(?, completed_at),
                  exit_code = COALESCE(?, exit_code)
                WHERE mission_id = ? AND id = ?
                """,
                (
                    status,
                    worktree_path,
                    branch_name,
                    process_id,
                    started_at,
                    completed_at,
                    exit_code,
                    mission_id,
                    agent_id,
                ),
            )
            if cursor.rowcount == 0:
                return None
            self._insert_event(
                connection,
                mission_id=mission_id,
                agent_id=agent_id,
                event_type=f"agent.{status}",
                payload={"agent_id": agent_id, "status": status},
                created_at=created_at,
            )
            row = connection.execute(
                "SELECT * FROM agents WHERE mission_id = ? AND id = ?",
                (mission_id, agent_id),
            ).fetchone()
        return dict(row) if row else None

    def stop_mission(self, mission_id: str, completed_at: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            cursor = connection.execute(
                """
                UPDATE missions SET status = 'stopped', completed_at = ?
                WHERE id = ?
                """,
                (completed_at, mission_id),
            )
            if cursor.rowcount == 0:
                return None
            self._insert_event(
                connection,
                mission_id=mission_id,
                event_type="mission.stopped",
                payload={"status": "stopped"},
                created_at=completed_at,
            )
        return self.get_mission(mission_id)

    def create_memory(
        self, capsule: dict[str, Any], *, ignore_existing: bool = False
    ) -> bool:
        searchable_text = " ".join(
            (
                capsule["title"],
                capsule["summary"],
                capsule["problem"],
                *capsule["triggers"],
                *capsule["tags"],
            )
        ).casefold()
        insert = "INSERT OR IGNORE" if ignore_existing else "INSERT"
        with self.connect() as connection:
            cursor = connection.execute(
                f"""
                {insert} INTO memories (
                  id, slug, capsule_json, searchable_text, status,
                  stars, installs, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    capsule["id"],
                    capsule["slug"],
                    json.dumps(capsule, separators=(",", ":")),
                    searchable_text,
                    capsule["status"],
                    capsule["stars"],
                    capsule["installs"],
                    capsule["created_at"],
                ),
            )
        return cursor.rowcount == 1

    def get_memory(self, slug: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM memories WHERE slug = ?", (slug,)
            ).fetchone()
        return self._memory_from_row(row) if row else None

    def list_memories(
        self,
        *,
        query: str | None = None,
        tag: str | None = None,
        sort: str = "featured",
    ) -> list[dict[str, Any]]:
        order_by = {
            "featured": "stars DESC, installs DESC, created_at DESC",
            "stars": "stars DESC, installs DESC, created_at DESC",
            "installs": "installs DESC, stars DESC, created_at DESC",
            "newest": "created_at DESC, stars DESC",
        }.get(sort, "stars DESC, installs DESC, created_at DESC")
        clauses: list[str] = []
        parameters: list[str] = []
        if query and query.strip():
            escaped_query = (
                query.strip()
                .casefold()
                .replace("\\", "\\\\")
                .replace("%", "\\%")
                .replace("_", "\\_")
            )
            clauses.append("searchable_text LIKE ? ESCAPE '\\'")
            parameters.append(f"%{escaped_query}%")
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self.connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM memories {where} ORDER BY {order_by}", parameters
            ).fetchall()
        memories = [self._memory_from_row(row) for row in rows]
        if tag and tag.strip():
            normalized_tag = tag.strip().casefold()
            memories = [
                memory
                for memory in memories
                if normalized_tag in {item.casefold() for item in memory["tags"]}
            ]
        return memories

    def star_memory(
        self, *, slug: str, user_id: str, created_at: str
    ) -> dict[str, Any] | None:
        with self.connect() as connection:
            memory = connection.execute(
                "SELECT id, slug FROM memories WHERE slug = ?", (slug,)
            ).fetchone()
            if memory is None:
                return None
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO memory_stars (memory_id, user_id, created_at)
                VALUES (?, ?, ?)
                """,
                (memory["id"], user_id, created_at),
            )
            if cursor.rowcount == 1:
                connection.execute(
                    "UPDATE memories SET stars = stars + 1 WHERE id = ?",
                    (memory["id"],),
                )
            stars = connection.execute(
                "SELECT stars FROM memories WHERE id = ?", (memory["id"],)
            ).fetchone()["stars"]
        return {
            "memory_id": memory["id"],
            "slug": memory["slug"],
            "starred": True,
            "stars": stars,
        }

    def install_memory(
        self,
        *,
        slug: str,
        install_id: str,
        consumer: str,
        installed_at: str,
    ) -> dict[str, Any] | None:
        with self.connect() as connection:
            memory = connection.execute(
                "SELECT id, slug, capsule_json FROM memories WHERE slug = ?", (slug,)
            ).fetchone()
            if memory is None:
                return None
            capsule = json.loads(memory["capsule_json"])
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO memory_installs (
                  id, memory_id, consumer, version, installed_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    install_id,
                    memory["id"],
                    consumer,
                    capsule["version"],
                    installed_at,
                ),
            )
            if cursor.rowcount == 1:
                connection.execute(
                    "UPDATE memories SET installs = installs + 1 WHERE id = ?",
                    (memory["id"],),
                )
            row = connection.execute(
                """
                SELECT * FROM memory_installs
                WHERE memory_id = ? AND consumer = ?
                """,
                (memory["id"], consumer),
            ).fetchone()
        if row is None:  # pragma: no cover - defensive invariant
            raise RuntimeError("install disappeared after insertion")
        result = dict(row)
        result["slug"] = memory["slug"]
        return result

    def list_installed_memories(self, consumer: str) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT memories.* FROM memories
                JOIN memory_installs ON memory_installs.memory_id = memories.id
                WHERE memory_installs.consumer = ?
                ORDER BY memory_installs.installed_at DESC
                """,
                (consumer,),
            ).fetchall()
        return [self._memory_from_row(row) for row in rows]

    def create_usage_receipt(self, receipt: dict[str, Any]) -> dict[str, Any] | None:
        with self.connect() as connection:
            memory = connection.execute(
                "SELECT id FROM memories WHERE id = ?", (receipt["memory_id"],)
            ).fetchone()
            if memory is None:
                return None
            connection.execute(
                """
                INSERT INTO usage_receipts (id, memory_id, receipt_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    receipt["id"],
                    receipt["memory_id"],
                    json.dumps(receipt, separators=(",", ":")),
                    receipt["created_at"],
                ),
            )
        return receipt

    def get_usage_receipt(self, receipt_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT receipt_json FROM usage_receipts WHERE id = ?", (receipt_id,)
            ).fetchone()
        return json.loads(row["receipt_json"]) if row else None

    def latest_usage_receipt(self) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT receipt_json FROM usage_receipts
                ORDER BY created_at DESC, id DESC LIMIT 1
                """
            ).fetchone()
        return json.loads(row["receipt_json"]) if row else None

    def registry_stats(self) -> dict[str, int]:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT
                  COUNT(*) AS published,
                  SUM(CASE WHEN status = 'verified' THEN 1 ELSE 0 END) AS verified,
                  COALESCE(SUM(installs), 0) AS installs
                FROM memories
                """
            ).fetchone()
            successful_uses = connection.execute(
                "SELECT COUNT(*) AS count FROM usage_receipts"
            ).fetchone()["count"]
        return {
            "published": row["published"],
            "verified": row["verified"],
            "installs": row["installs"],
            "successful_uses": successful_uses,
        }

    @staticmethod
    def _memory_from_row(row: sqlite3.Row) -> dict[str, Any]:
        capsule = json.loads(row["capsule_json"])
        capsule["stars"] = row["stars"]
        capsule["installs"] = row["installs"]
        return capsule

    @staticmethod
    def _insert_event(
        connection: sqlite3.Connection,
        *,
        mission_id: str,
        event_type: str,
        payload: dict[str, Any],
        created_at: str,
        agent_id: str | None = None,
    ) -> None:
        connection.execute(
            """
            INSERT INTO events (
              mission_id, agent_id, event_type, payload_json, created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (mission_id, agent_id, event_type, json.dumps(payload), created_at),
        )

    @staticmethod
    def _mission_from_row(row: sqlite3.Row) -> dict[str, Any]:
        result = dict(row)
        result["was_dirty"] = bool(result["was_dirty"])
        result["allow_dirty_repository"] = bool(result["allow_dirty_repository"])
        result["protected_paths"] = json.loads(result.pop("protected_paths_json"))
        result["verification_commands"] = json.loads(
            result.pop("verification_commands_json")
        )
        return result

    @staticmethod
    def _event_from_row(row: sqlite3.Row) -> dict[str, Any]:
        result = dict(row)
        result["payload"] = json.loads(result.pop("payload_json"))
        return result

    @staticmethod
    def _knowledge_from_row(row: sqlite3.Row) -> dict[str, Any]:
        result = dict(row)
        for source, target in (
            ("evidence_json", "evidence"),
            ("tags_json", "tags"),
            ("relevant_to_json", "relevant_to"),
            ("consumed_by_json", "consumed_by"),
        ):
            raw = result.pop(source)
            result[target] = json.loads(raw) if raw else []
        return result
