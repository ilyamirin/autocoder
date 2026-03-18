#!/usr/bin/env python3
from __future__ import annotations

import os

from services.common.kanboard import (
    KanboardClient,
    list_project_tasks,
    parse_demo_task_id,
    sync_task_status,
    task_index_by_catalog_id,
    wait_for_server,
)
from services.common.task_catalog import BOARD_COLUMNS, DEFAULT_TASKS


def ensure_project(client: KanboardClient, project_name: str) -> int:
    project = client.call("getProjectByName", {"name": project_name})
    if project:
        return int(project["id"])
    project_id = client.call(
        "createProject",
        {
            "name": project_name,
            "description": "Доска задач для демо автономного кодинга вокруг приложения Seller Desk.",
        },
    )
    return int(project_id)


def ensure_columns(client: KanboardClient, project_id: int) -> dict[str, int]:
    current_columns = client.call("getColumns", [project_id])
    by_title = {column["title"]: int(column["id"]) for column in current_columns}

    for position, title in enumerate(BOARD_COLUMNS, start=1):
        if title not in by_title:
            column_id = client.call("addColumn", [project_id, title])
            by_title[title] = int(column_id)
        client.call("changeColumnPosition", [project_id, by_title[title], position])

    return by_title


def ensure_user(client: KanboardClient) -> int:
    username = os.environ["KANBOARD_DEMO_USER_USERNAME"]
    user = client.call("getUserByName", {"username": username})
    if user:
        return int(user["id"])
    user_id = client.call(
        "createUser",
        {
            "username": username,
            "password": os.environ["KANBOARD_DEMO_USER_PASSWORD"],
            "name": os.environ["KANBOARD_DEMO_USER_NAME"],
            "email": os.environ["KANBOARD_DEMO_USER_EMAIL"],
            "role": "app-user",
        },
    )
    return int(user_id)


def ensure_project_membership(client: KanboardClient, project_id: int, user_id: int) -> None:
    project_users = client.call("getProjectUsers", [project_id]) or {}
    if str(user_id) in project_users:
        return
    client.call("addProjectUser", [project_id, user_id, "project-member"])


def task_exists(client: KanboardClient, project_id: int, title: str) -> bool:
    active_tasks = client.call("getAllTasks", {"project_id": project_id, "status_id": 1}) or []
    inactive_tasks = client.call("getAllTasks", {"project_id": project_id, "status_id": 0}) or []
    titles = {task["title"] for task in active_tasks + inactive_tasks}
    return title in titles


def kanboard_description(task: dict) -> str:
    return (
        f"Demo task id: `{task['id']}`\n\n"
        f"Тип: `{task['kind']}`\n"
        f"Зона: `{task['target_area']}`\n"
        f"Риск автоисполнения: `{task.get('execution_risk') or 'n/a'}`\n\n"
        f"Оценки:\n"
        f"- Наглядность: {task['visual_score']}/5\n"
        f"- Реалистичность: {task['realism_score']}/5\n"
        f"- Шанс успешного автоисполнения: {task['agent_score']}/5\n\n"
        f"Контекст:\n{task['summary']}\n\n"
        f"Definition of Done:\n{task['acceptance_criteria']}"
    )


def ensure_tasks(client: KanboardClient, project_id: int, owner_id: int, column_ids: dict[str, int]) -> None:
    status_to_column = {
        "backlog": "Backlog",
        "ready": "Ready",
        "planning": "Planning",
        "coding": "Coding",
        "testing": "Testing",
        "deploy": "Deploy",
        "done": "Done",
        "failed": "Failed",
    }

    existing_tasks = list_project_tasks(client, project_id)
    indexed_tasks = task_index_by_catalog_id(existing_tasks)

    for task in DEFAULT_TASKS:
        column_name = status_to_column[task["status"]]
        target_column_id = column_ids[column_name]
        existing = indexed_tasks.get(task["id"])
        if existing:
            client.call(
                "updateTask",
                {
                    "id": int(existing["id"]),
                    "title": task["title"],
                    "owner_id": owner_id,
                    "description": kanboard_description(task),
                },
            )
            sync_task_status(
                client,
                project_id=project_id,
                task_id=int(existing["id"]),
                swimlane_id=int(existing.get("swimlane_id") or 1),
                target_column_id=target_column_id,
            )
            continue

        if task_exists(client, project_id, task["title"]):
            continue

        created_task_id = client.call(
            "createTask",
            {
                "title": task["title"],
                "project_id": project_id,
                "column_id": target_column_id,
                "owner_id": owner_id,
                "description": kanboard_description(task),
            },
        )
        sync_task_status(
            client,
            project_id=project_id,
            task_id=int(created_task_id),
            swimlane_id=1,
            target_column_id=target_column_id,
        )


def main() -> None:
    client = KanboardClient(
        url=os.getenv("KANBOARD_URL", "http://kanboard/jsonrpc.php"),
        username=os.getenv("KANBOARD_API_USERNAME") or os.getenv("KANBOARD_ADMIN_USERNAME", "admin"),
        token=os.getenv("KANBOARD_API_TOKEN") or os.getenv("KANBOARD_ADMIN_PASSWORD", "admin"),
    )
    try:
        wait_for_server(client)
        project_id = ensure_project(client, os.environ["KANBOARD_PROJECT_NAME"])
        column_ids = ensure_columns(client, project_id)
        user_id = ensure_user(client)
        ensure_project_membership(client, project_id, user_id)
        ensure_tasks(client, project_id, user_id, column_ids)
        print(f"Kanboard seeded: project_id={project_id}, user_id={user_id}")
    finally:
        client.close()


if __name__ == "__main__":
    main()
