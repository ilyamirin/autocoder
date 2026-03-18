from __future__ import annotations

import os
import sqlite3
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

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

DEFAULT_TASKS = [
    {
        "id": "DONE-001",
        "title": "Base dashboard with GMV and net revenue cards",
        "kind": "feature",
        "status": "done",
        "summary": "Initial analytics cards for the seller cockpit.",
        "acceptance_criteria": "Dashboard shows GMV and net revenue values.",
        "target_area": "dashboard",
    },
    {
        "id": "DONE-002",
        "title": "Orders page with seeded data table",
        "kind": "feature",
        "status": "done",
        "summary": "Basic orders list with order ids, dates, statuses, and totals.",
        "acceptance_criteria": "Orders page renders a non-empty table.",
        "target_area": "orders",
    },
    {
        "id": "DONE-003",
        "title": "Products page with stock overview",
        "kind": "feature",
        "status": "done",
        "summary": "Basic product list with stock and margin percent.",
        "acceptance_criteria": "Products page shows stock and margin columns.",
        "target_area": "products",
    },
    {
        "id": "DONE-004",
        "title": "Finance page daily revenue chart",
        "kind": "feature",
        "status": "done",
        "summary": "Daily revenue history for the last week.",
        "acceptance_criteria": "Finance page renders daily revenue values.",
        "target_area": "finance",
    },
    {
        "id": "DONE-005",
        "title": "Date range filter for order analytics",
        "kind": "feature",
        "status": "done",
        "summary": "Metrics respect the selected date range.",
        "acceptance_criteria": "Dashboard totals change when date range changes.",
        "target_area": "dashboard",
    },
    {
        "id": "DONE-006",
        "title": "Baseline API health endpoint",
        "kind": "quality",
        "status": "done",
        "summary": "Health endpoint for pet app and orchestrator.",
        "acceptance_criteria": "GET /health returns ok.",
        "target_area": "platform",
    },
    {
        "id": "DONE-007",
        "title": "Dockerized pet app service",
        "kind": "quality",
        "status": "done",
        "summary": "The pet app can run inside docker compose.",
        "acceptance_criteria": "Pet app is reachable on the mapped port.",
        "target_area": "platform",
    },
    {
        "id": "DONE-008",
        "title": "Seed seller demo data",
        "kind": "quality",
        "status": "done",
        "summary": "Synthetic seller data prepared for the demo.",
        "acceptance_criteria": "Dashboard metrics are populated from seed data.",
        "target_area": "data",
    },
    {
        "id": "BL-001",
        "title": "Net revenue ignores returns for refunded orders",
        "kind": "bug",
        "status": "backlog",
        "summary": "Finance totals should subtract refunded orders.",
        "acceptance_criteria": "Net revenue excludes refunded order totals.",
        "target_area": "finance",
    },
    {
        "id": "BL-002",
        "title": "Orders sorting by date is lexicographic instead of chronological",
        "kind": "bug",
        "status": "backlog",
        "summary": "String sorting breaks the recent orders view.",
        "acceptance_criteria": "Newest orders appear first regardless of month/day formatting.",
        "target_area": "orders",
    },
    {
        "id": "BL-003",
        "title": "Dashboard totals do not react to category filter",
        "kind": "bug",
        "status": "backlog",
        "summary": "Category filter affects the table but not summary cards.",
        "acceptance_criteria": "Filtered dashboard cards match filtered dataset.",
        "target_area": "dashboard",
    },
    {
        "id": "BL-004",
        "title": "Add low stock products panel to dashboard",
        "kind": "feature",
        "status": "backlog",
        "summary": "Show products with critically low stock.",
        "acceptance_criteria": "Dashboard lists products with stock under the threshold.",
        "target_area": "dashboard",
    },
    {
        "id": "BL-005",
        "title": "Add CSV export for orders",
        "kind": "feature",
        "status": "backlog",
        "summary": "Operations needs a quick CSV export from the orders page.",
        "acceptance_criteria": "Orders page provides CSV download.",
        "target_area": "orders",
    },
    {
        "id": "BL-006",
        "title": "Highlight negative margin products",
        "kind": "feature",
        "status": "backlog",
        "summary": "Negative margin should be visible without opening product details.",
        "acceptance_criteria": "Negative margin rows are clearly highlighted.",
        "target_area": "products",
    },
    {
        "id": "BL-007",
        "title": "Return rate widget overcounts cancelled orders",
        "kind": "bug",
        "status": "backlog",
        "summary": "Cancelled orders should not increase the return rate denominator.",
        "acceptance_criteria": "Return rate excludes cancelled orders from the base.",
        "target_area": "dashboard",
    },
    {
        "id": "BL-008",
        "title": "Top products card should support brand filter",
        "kind": "feature",
        "status": "backlog",
        "summary": "Brand filter needs to propagate to top products.",
        "acceptance_criteria": "Top products card changes when a brand is selected.",
        "target_area": "products",
    },
    {
        "id": "BL-009",
        "title": "Seed more return reasons for analytics slice",
        "kind": "quality",
        "status": "backlog",
        "summary": "The demo needs a richer reasons distribution.",
        "acceptance_criteria": "Return reasons chart has at least four categories.",
        "target_area": "data",
    },
    {
        "id": "BL-010",
        "title": "Add build badge with deployed task id",
        "kind": "feature",
        "status": "backlog",
        "summary": "The live app should reveal which task version is deployed.",
        "acceptance_criteria": "UI shows a build badge with task id and timestamp.",
        "target_area": "platform",
    },
    {
        "id": "BL-011",
        "title": "Improve empty state for no matching orders",
        "kind": "feature",
        "status": "backlog",
        "summary": "Current empty table is unclear.",
        "acceptance_criteria": "Users see a readable empty state with next actions.",
        "target_area": "orders",
    },
    {
        "id": "BL-012",
        "title": "Add smoke test for dashboard home page",
        "kind": "quality",
        "status": "backlog",
        "summary": "The demo needs one more smoke test for confidence.",
        "acceptance_criteria": "Test suite covers the dashboard landing page.",
        "target_area": "platform",
    },
]


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
