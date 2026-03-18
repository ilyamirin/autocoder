from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from typing import Any

import httpx

STATUS_TO_COLUMN = {
    "backlog": "Backlog",
    "ready": "Ready",
    "planning": "Planning",
    "coding": "Coding",
    "testing": "Testing",
    "deploy": "Deploy",
    "done": "Done",
    "failed": "Failed",
}

COLUMN_TO_STATUS = {value: key for key, value in STATUS_TO_COLUMN.items()}


def parse_demo_task_id(description: str) -> str | None:
    match = re.search(r"Demo task id:\s*`([^`]+)`", description or "")
    return match.group(1) if match else None


@dataclass(frozen=True)
class KanboardConfig:
    url: str
    username: str
    token: str
    project_name: str
    enabled: bool

    @classmethod
    def from_env(cls) -> "KanboardConfig":
        username = os.getenv("KANBOARD_API_USERNAME") or os.getenv("KANBOARD_ADMIN_USERNAME", "")
        token = os.getenv("KANBOARD_API_TOKEN") or os.getenv("KANBOARD_ADMIN_PASSWORD", "")
        project_name = os.getenv("KANBOARD_PROJECT_NAME", "")
        enabled = (
            os.getenv("KANBOARD_SYNC_ENABLED", "true").lower() == "true"
            and bool(username)
            and bool(token)
            and bool(project_name)
        )
        return cls(
            url=os.getenv("KANBOARD_URL", "http://kanboard/jsonrpc.php"),
            username=username,
            token=token,
            project_name=project_name,
            enabled=enabled,
        )


class KanboardClient:
    def __init__(self, url: str, username: str, token: str) -> None:
        self._url = url.rstrip("/")
        self._client = httpx.Client(auth=(username, token), timeout=httpx.Timeout(20.0))
        self._request_id = 0

    def close(self) -> None:
        self._client.close()

    def call(self, method: str, params: Any | None = None) -> Any:
        self._request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params or {},
        }
        response = self._client.post(self._url, json=payload)
        response.raise_for_status()
        body = response.json()
        if body.get("error"):
            raise RuntimeError(f"Kanboard API error for {method}: {body['error']}")
        return body.get("result")


def wait_for_server(client: KanboardClient, attempts: int = 30, sleep_seconds: int = 2) -> None:
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            client.call("getAllProjects")
            return
        except Exception as exc:  # pragma: no cover - exercised against live Kanboard only
            last_error = exc
            time.sleep(sleep_seconds)
    raise RuntimeError("Kanboard did not become ready in time") from last_error


def list_project_tasks(client: KanboardClient, project_id: int) -> list[dict]:
    active_tasks = client.call("getAllTasks", {"project_id": project_id, "status_id": 1}) or []
    inactive_tasks = client.call("getAllTasks", {"project_id": project_id, "status_id": 0}) or []
    return active_tasks + inactive_tasks


def task_index_by_catalog_id(tasks: list[dict]) -> dict[str, dict]:
    indexed: dict[str, dict] = {}
    for task in tasks:
        catalog_id = parse_demo_task_id(task.get("description", ""))
        if catalog_id:
            indexed[catalog_id] = task
    return indexed


def sync_task_status(
    client: KanboardClient,
    project_id: int,
    task_id: int,
    swimlane_id: int,
    target_column_id: int,
) -> None:
    client.call(
        "moveTaskPosition",
        {
            "project_id": project_id,
            "task_id": task_id,
            "column_id": target_column_id,
            "position": 1,
            "swimlane_id": swimlane_id,
        },
    )
    # Keep tasks open so completed and failed cards remain visible on the demo board.
    client.call("openTask", {"task_id": task_id})


class KanboardSync:
    def __init__(self, config: KanboardConfig | None = None, client: KanboardClient | None = None) -> None:
        self._config = config or KanboardConfig.from_env()
        self._client = client
        self._project_id: int | None = None
        self._column_ids: dict[str, int] | None = None
        self._column_names_by_id: dict[int, str] | None = None

    @property
    def enabled(self) -> bool:
        return self._config.enabled

    def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None

    def remote_tasks(self) -> dict[str, dict]:
        if not self.enabled:
            return {}
        tasks = list_project_tasks(self._client_or_create(), self._project_id_or_load())
        return task_index_by_catalog_id(tasks)

    def board_status(self, remote_task: dict) -> str:
        column_name = self._column_name(remote_task)
        status_id = int(remote_task.get("is_active", remote_task.get("status_id", 1)))
        if status_id == 0:
            return "failed" if column_name == "Failed" else "done"
        return COLUMN_TO_STATUS.get(column_name, "backlog")

    def sync_task_status(self, task_id: str, status: str) -> None:
        if not self.enabled:
            return
        remote_task = self.remote_tasks().get(task_id)
        if not remote_task:
            return
        column_name = STATUS_TO_COLUMN[status]
        target_column_id = self._column_ids_or_load()[column_name]
        sync_task_status(
            self._client_or_create(),
            project_id=self._project_id_or_load(),
            task_id=int(remote_task["id"]),
            swimlane_id=int(remote_task.get("swimlane_id") or 1),
            target_column_id=target_column_id,
        )

    def _client_or_create(self) -> KanboardClient:
        if self._client is None:
            self._client = KanboardClient(
                url=self._config.url,
                username=self._config.username,
                token=self._config.token,
            )
        return self._client

    def _project_id_or_load(self) -> int:
        if self._project_id is None:
            project = self._client_or_create().call(
                "getProjectByName", {"name": self._config.project_name}
            )
            if not project:
                raise RuntimeError(f"Kanboard project '{self._config.project_name}' was not found.")
            self._project_id = int(project["id"])
        return self._project_id

    def _column_ids_or_load(self) -> dict[str, int]:
        if self._column_ids is None:
            columns = self._client_or_create().call("getColumns", [self._project_id_or_load()])
            self._column_ids = {column["title"]: int(column["id"]) for column in columns}
            self._column_names_by_id = {int(column["id"]): column["title"] for column in columns}
        return self._column_ids

    def _column_name(self, remote_task: dict) -> str:
        self._column_ids_or_load()
        column_id = int(remote_task.get("column_id") or 0)
        return self._column_names_by_id.get(column_id, "")
