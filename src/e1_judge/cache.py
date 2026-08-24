"""SQLite cache with retryable failures for E1 schema-v2 results."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS judge_results (
  judge_key TEXT PRIMARY KEY,
  request_id TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('succeeded','failed')),
  payload_json TEXT NOT NULL,
  error TEXT,
  runtime_seconds REAL NOT NULL DEFAULT 0,
  peak_vram_mb REAL NOT NULL DEFAULT 0,
  attempt_count INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


class JudgeCache:
    def __init__(self, path: Path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
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

    def get_record(self, judge_key: str) -> Optional[Dict[str, Any]]:
        row = self.connection.execute(
            "SELECT * FROM judge_results WHERE judge_key = ?", (judge_key,)
        ).fetchone()
        if row is None:
            return None
        record = dict(row)
        record["payload"] = json.loads(record.pop("payload_json"))
        return record

    def get_succeeded(self, judge_key: str) -> Optional[Dict[str, Any]]:
        record = self.get_record(judge_key)
        if record is None or record["status"] != "succeeded":
            return None
        return record["payload"]

    def put(
        self,
        judge_key: str,
        request_id: str,
        status: str,
        payload: Dict[str, Any],
        error: Optional[str] = None,
        runtime_seconds: float = 0.0,
        peak_vram_mb: float = 0.0,
    ) -> None:
        self.connection.execute(
            """INSERT INTO judge_results(
                   judge_key,request_id,status,payload_json,error,runtime_seconds,peak_vram_mb
               ) VALUES(?,?,?,?,?,?,?)
               ON CONFLICT(judge_key) DO UPDATE SET
                   request_id=excluded.request_id,status=excluded.status,
                   payload_json=excluded.payload_json,error=excluded.error,
                   runtime_seconds=excluded.runtime_seconds,peak_vram_mb=excluded.peak_vram_mb,
                   attempt_count=judge_results.attempt_count+1,updated_at=CURRENT_TIMESTAMP""",
            (
                judge_key, request_id, status,
                json.dumps(payload, ensure_ascii=False, sort_keys=True), error,
                float(runtime_seconds), float(peak_vram_mb),
            ),
        )
        self.connection.commit()

    def succeeded_payloads(self, judge_keys: List[str]) -> Dict[str, Dict[str, Any]]:
        if not judge_keys:
            return {}
        rows = self.connection.execute(
            "SELECT judge_key,payload_json FROM judge_results WHERE status='succeeded'"
        ).fetchall()
        wanted = set(judge_keys)
        return {
            row["judge_key"]: json.loads(row["payload_json"])
            for row in rows if row["judge_key"] in wanted
        }

    def list_records(self) -> List[Dict[str, Any]]:
        rows = self.connection.execute("SELECT * FROM judge_results ORDER BY request_id").fetchall()
        records = []
        for row in rows:
            record = dict(row)
            record["payload"] = json.loads(record.pop("payload_json"))
            records.append(record)
        return records
