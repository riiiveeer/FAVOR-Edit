"""E1 SQLite judge request cache."""

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS judge_results (
  judge_key TEXT PRIMARY KEY,
  request_id TEXT NOT NULL,
  status TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  error TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


class JudgeCache:
    def __init__(self, path: Path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(SCHEMA)

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "JudgeCache":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def get(self, judge_key: str) -> Optional[Dict[str, Any]]:
        row = self.connection.execute(
            "SELECT payload_json FROM judge_results WHERE judge_key = ?", (judge_key,)
        ).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def put(self, judge_key: str, request_id: str, status: str, payload: Dict[str, Any], error: Optional[str] = None) -> None:
        self.connection.execute(
            """INSERT INTO judge_results(judge_key,request_id,status,payload_json,error)
               VALUES(?,?,?,?,?)
               ON CONFLICT(judge_key) DO UPDATE SET status=excluded.status,
               payload_json=excluded.payload_json,error=excluded.error,updated_at=CURRENT_TIMESTAMP""",
            (judge_key, request_id, status, json.dumps(payload, ensure_ascii=False, sort_keys=True), error),
        )
        self.connection.commit()

    def list_results(self) -> List[Dict[str, Any]]:
        rows = self.connection.execute("SELECT payload_json FROM judge_results ORDER BY request_id").fetchall()
        return [json.loads(row["payload_json"]) for row in rows]
