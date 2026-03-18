from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress
import os

from fastapi import FastAPI

from services.common.kanboard import KanboardSync
from services.common.store import (
    claim_next_ready_task,
    get_task,
    initialize_store,
    list_recent_events,
    list_tasks,
    update_task,
)
from services.orchestrator.task_executor import TaskExecutionError, TaskExecutor

POLL_INTERVAL_SECONDS = int(os.getenv("ORCHESTRATOR_POLL_INTERVAL_SECONDS", "5"))


def sync_terminal_kanboard_state(kanboard_sync: KanboardSync) -> None:
    if not kanboard_sync.enabled:
        return
    remote_tasks = kanboard_sync.remote_tasks()
    for task_id, remote_task in remote_tasks.items():
        local_task = get_task(task_id)
        if not local_task:
            continue
        remote_status = kanboard_sync.board_status(remote_task)
        if local_task["status"] in {"planning", "coding", "testing", "deploy"}:
            continue
        if remote_status == local_task["status"]:
            continue
        if remote_status in {"backlog", "ready", "done", "failed"}:
            update_task(
                task_id,
                status=remote_status,
                last_error=None if remote_status != "failed" else local_task.get("last_error"),
                event_type="kanboard",
                event_message=f"Local task status synced from Kanboard column to {remote_status}.",
            )


async def orchestration_loop(stop_event: asyncio.Event, kanboard_sync: KanboardSync) -> None:
    executor = TaskExecutor(kanboard_sync=kanboard_sync)
    while not stop_event.is_set():
        try:
            sync_terminal_kanboard_state(kanboard_sync)
        except Exception:
            pass
        task = claim_next_ready_task()
        if task:
            if kanboard_sync.enabled:
                try:
                    kanboard_sync.sync_task_status(task["id"], "planning")
                except Exception:
                    pass
            try:
                await asyncio.to_thread(executor.execute, task)
            except TaskExecutionError:
                pass
            except Exception:
                pass
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_store()
    stop_event = asyncio.Event()
    kanboard_sync = KanboardSync()
    task = asyncio.create_task(orchestration_loop(stop_event, kanboard_sync))
    try:
        yield
    finally:
        stop_event.set()
        task.cancel()
        kanboard_sync.close()
        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(title="Orchestrator", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/tasks")
def tasks() -> dict:
    return {"items": list_tasks()}


@app.get("/api/events")
def events() -> dict:
    return {"items": list_recent_events()}
