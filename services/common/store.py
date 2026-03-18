from __future__ import annotations

import os
import sqlite3
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from services.common.task_catalog import DEFAULT_TASKS

STATUS_ORDER = [
    "backlog",
    "ready",
    "planning",
    "coding",
    "testing",
    "deploy",
    "done",
    "failed",
]

TRANSITION_FLOW = {
    "ready": "planning",
    "planning": "coding",
    "coding": "testing",
    "testing": "deploy",
    "deploy": "done",
}

def utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def get_db_path() -> Path:
    path = Path(os.getenv("DEMO_DB_PATH", "data/demo.db"))
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(get_db_path(), check_same_thread=False)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def initialize_store() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                kind TEXT NOT NULL,
                status TEXT NOT NULL,
                summary TEXT NOT NULL,
                acceptance_criteria TEXT NOT NULL,
                target_area TEXT NOT NULL,
                branch_name TEXT,
                repo_link TEXT,
                ci_link TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        task_count = connection.execute("SELECT COUNT(*) AS count FROM tasks").fetchone()["count"]
        if task_count == 0:
            timestamp = utc_now()
            for task in DEFAULT_TASKS:
                connection.execute(
                    """
                    INSERT INTO tasks (
                        id, title, kind, status, summary, acceptance_criteria,
                        target_area, branch_name, repo_link, ci_link, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        task["id"],
                        task["title"],
                        task["kind"],
                        task["status"],
                        task["summary"],
                        task["acceptance_criteria"],
                        task["target_area"],
                        None,
                        None,
                        None,
                        timestamp,
                        timestamp,
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO events (task_id, event_type, message, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        task["id"],
                        "seeded",
                        f"Task {task['id']} seeded in status {task['status']}.",
                        timestamp,
                    ),
                )


def list_tasks() -> list[dict]:
    initialize_store()
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM tasks
            ORDER BY CASE status
                WHEN 'ready' THEN 0
                WHEN 'planning' THEN 1
                WHEN 'coding' THEN 2
                WHEN 'testing' THEN 3
                WHEN 'deploy' THEN 4
                WHEN 'backlog' THEN 5
                WHEN 'done' THEN 6
                WHEN 'failed' THEN 7
                ELSE 8
            END, id
            """
        ).fetchall()
        return [dict(row) for row in rows]


def get_task(task_id: str) -> dict | None:
    initialize_store()
    with get_connection() as connection:
        row = connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return dict(row) if row else None


def list_recent_events(limit: int = 30) -> list[dict]:
    initialize_store()
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM events
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]


def move_task_to_ready(task_id: str) -> bool:
    task = get_task(task_id)
    if not task or task["status"] != "backlog":
        return False
    update_task_status(task_id, "ready", "Task moved to Ready and waiting for the orchestrator.")
    return True


def update_task_status(task_id: str, status: str, message: str) -> None:
    timestamp = utc_now()
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE tasks
            SET status = ?, updated_at = ?
            WHERE id = ?
            """,
            (status, timestamp, task_id),
        )
        connection.execute(
            """
            INSERT INTO events (task_id, event_type, message, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (task_id, status, message, timestamp),
        )


def progress_ready_tasks() -> list[dict]:
    initialize_store()
    transitioned: list[dict] = []
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, status
            FROM tasks
            WHERE status IN ('ready', 'planning', 'coding', 'testing', 'deploy')
            ORDER BY updated_at ASC
            """
        ).fetchall()

    for row in rows:
        next_status = TRANSITION_FLOW.get(row["status"])
        if not next_status:
            continue
        message = (
            f"Task advanced from {row['status']} to {next_status} by the local demo orchestrator."
        )
        update_task_status(row["id"], next_status, message)
        transitioned.append({"task_id": row["id"], "from": row["status"], "to": next_status})
    return transitioned


def build_status_summary() -> dict[str, int]:
    counts = Counter(task["status"] for task in list_tasks())
    return {status: counts.get(status, 0) for status in STATUS_ORDER}
