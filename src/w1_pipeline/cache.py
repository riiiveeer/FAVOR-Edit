"""SQLite-backed idempotency and result cache."""

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional


SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS generations (
  cache_key TEXT PRIMARY KEY,
  candidate_id TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  error TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS rewards (
  cache_key TEXT PRIMARY KEY,
  request_id TEXT NOT NULL,
  status TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  error TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


class Cache:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(SCHEMA)

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "Cache":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def get_generation(self, cache_key: str) -> Optional[Dict[str, Any]]:
        row = self.connection.execute("SELECT payload_json FROM generations WHERE cache_key = ?", (cache_key,)).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def put_generation(self, cache_key: str, candidate_id: str, status: str, payload: Dict[str, Any], error: Optional[str] = None) -> None:
        self.connection.execute(
            """INSERT INTO generations(cache_key,candidate_id,status,payload_json,error)
               VALUES(?,?,?,?,?)
               ON CONFLICT(cache_key) DO UPDATE SET status=excluded.status,
               payload_json=excluded.payload_json,error=excluded.error,updated_at=CURRENT_TIMESTAMP""",
            (cache_key, candidate_id, status, json.dumps(payload, ensure_ascii=False, sort_keys=True), error),
        )
        self.connection.commit()

    def list_generations(self) -> List[Dict[str, Any]]:
        rows = self.connection.execute("SELECT payload_json FROM generations ORDER BY candidate_id").fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def get_reward(self, cache_key: str) -> Optional[Dict[str, Any]]:
        row = self.connection.execute("SELECT payload_json FROM rewards WHERE cache_key = ?", (cache_key,)).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def put_reward(self, cache_key: str, request_id: str, status: str, payload: Dict[str, Any], error: Optional[str] = None) -> None:
        self.connection.execute(
            """INSERT INTO rewards(cache_key,request_id,status,payload_json,error)
               VALUES(?,?,?,?,?)
               ON CONFLICT(cache_key) DO UPDATE SET status=excluded.status,
               payload_json=excluded.payload_json,error=excluded.error,updated_at=CURRENT_TIMESTAMP""",
            (cache_key, request_id, status, json.dumps(payload, ensure_ascii=False, sort_keys=True), error),
        )
        self.connection.commit()

    def list_rewards(self) -> List[Dict[str, Any]]:
        rows = self.connection.execute("SELECT payload_json FROM rewards ORDER BY request_id").fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

