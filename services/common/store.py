from __future__ import annotations

import os
import sqlite3
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

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

TASK_COLUMNS = {
    "branch_name": "TEXT",
    "repo_link": "TEXT",
    "ci_link": "TEXT",
    "commit_sha": "TEXT",
    "live_commit_sha": "TEXT",
    "worktree_path": "TEXT",
    "last_error": "TEXT",
    "execution_risk": "TEXT",
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
        _ensure_task_columns(connection)
        _sync_catalog_metadata(connection)
        task_count = connection.execute("SELECT COUNT(*) AS count FROM tasks").fetchone()["count"]
        if task_count == 0:
            _seed_tasks(connection)


def _ensure_task_columns(connection: sqlite3.Connection) -> None:
    current_columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(tasks)").fetchall()
    }
    for column_name, column_type in TASK_COLUMNS.items():
        if column_name not in current_columns:
            connection.execute(f"ALTER TABLE tasks ADD COLUMN {column_name} {column_type}")


def _seed_tasks(connection: sqlite3.Connection) -> None:
    timestamp = utc_now()
    for task in DEFAULT_TASKS:
        connection.execute(
            """
            INSERT INTO tasks (
                id, title, kind, status, summary, acceptance_criteria,
                target_area, execution_risk, branch_name, repo_link, ci_link, commit_sha,
                worktree_path, last_error, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task["id"],
                task["title"],
                task["kind"],
                task["status"],
                task["summary"],
                task["acceptance_criteria"],
                task["target_area"],
                task.get("execution_risk"),
                None,
                None,
                None,
                None,
                None,
                None,
                timestamp,
                timestamp,
            ),
        )
        _insert_event(
            connection,
            task["id"],
            "seeded",
            f"Task {task['id']} seeded in status {task['status']}.",
            timestamp,
        )


def _sync_catalog_metadata(connection: sqlite3.Connection) -> None:
    for task in DEFAULT_TASKS:
        connection.execute(
            """
            UPDATE tasks
            SET title = ?,
                kind = ?,
                status = CASE
                    WHEN tasks.status = 'backlog' AND ? = 'done' THEN 'done'
                    ELSE tasks.status
                END,
                summary = ?,
                acceptance_criteria = ?,
                target_area = ?,
                execution_risk = ?
            WHERE id = ?
            """,
            (
                task["title"],
                task["kind"],
                task["status"],
                task["summary"],
                task["acceptance_criteria"],
                task["target_area"],
                task.get("execution_risk"),
                task["id"],
            ),
        )


def _insert_event(
    connection: sqlite3.Connection, task_id: str, event_type: str, message: str, created_at: str
) -> None:
    connection.execute(
        """
        INSERT INTO events (task_id, event_type, message, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (task_id, event_type, message, created_at),
    )


def list_tasks() -> list[dict[str, Any]]:
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
            END, updated_at ASC, id
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_task(task_id: str) -> dict[str, Any] | None:
    initialize_store()
    with get_connection() as connection:
        row = connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return dict(row) if row else None


def list_recent_events(limit: int = 30) -> list[dict[str, Any]]:
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
    update_task(
        task_id,
        status="ready",
        last_error=None,
        event_type="ready",
        event_message="Task moved to Ready and waiting for the orchestrator.",
    )
    return True


def claim_next_ready_task() -> dict[str, Any] | None:
    initialize_store()
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT *
            FROM tasks
            WHERE status = 'ready'
            ORDER BY updated_at ASC
            LIMIT 1
            """
        ).fetchone()
        if not row:
            return None
        task = dict(row)
        timestamp = utc_now()
        connection.execute(
            """
            UPDATE tasks
            SET status = ?, updated_at = ?, last_error = NULL
            WHERE id = ?
            """,
            ("planning", timestamp, task["id"]),
        )
        _insert_event(
            connection,
            task["id"],
            "planning",
            "Orchestrator claimed the task and started planning the execution run.",
            timestamp,
        )
    task["status"] = "planning"
    task["updated_at"] = timestamp
    task["last_error"] = None
    return task


def claim_task(task_id: str) -> dict[str, Any] | None:
    initialize_store()
    with get_connection() as connection:
        row = connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not row or row["status"] != "ready":
            return None
        task = dict(row)
        timestamp = utc_now()
        connection.execute(
            """
            UPDATE tasks
            SET status = ?, updated_at = ?, last_error = NULL
            WHERE id = ?
            """,
            ("planning", timestamp, task_id),
        )
        _insert_event(
            connection,
            task_id,
            "planning",
            "Orchestrator claimed the task and started planning the execution run.",
            timestamp,
        )
    task["status"] = "planning"
    task["updated_at"] = timestamp
    task["last_error"] = None
    return task


def update_task(
    task_id: str,
    *,
    event_type: str | None = None,
    event_message: str | None = None,
    **fields: Any,
) -> None:
    if not fields and not event_type:
        return

    timestamp = utc_now()
    updates = dict(fields)
    updates["updated_at"] = timestamp
    columns = ", ".join(f"{column} = ?" for column in updates)
    values = list(updates.values())

    with get_connection() as connection:
        connection.execute(f"UPDATE tasks SET {columns} WHERE id = ?", (*values, task_id))
        if event_type and event_message:
            _insert_event(connection, task_id, event_type, event_message, timestamp)


def add_event(task_id: str, event_type: str, message: str) -> None:
    timestamp = utc_now()
    with get_connection() as connection:
        _insert_event(connection, task_id, event_type, message, timestamp)


def mark_task_failed(task_id: str, message: str) -> None:
    update_task(
        task_id,
        status="failed",
        last_error=message,
        event_type="failed",
        event_message=message,
    )


def build_status_summary() -> dict[str, int]:
    counts = Counter(task["status"] for task in list_tasks())
    return {status: counts.get(status, 0) for status in STATUS_ORDER}
