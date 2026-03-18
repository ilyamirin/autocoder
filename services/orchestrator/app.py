from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress
import os

from fastapi import FastAPI

from services.common.store import initialize_store, list_recent_events, list_tasks, progress_ready_tasks

POLL_INTERVAL_SECONDS = int(os.getenv("ORCHESTRATOR_POLL_INTERVAL_SECONDS", "5"))


async def orchestration_loop(stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        progress_ready_tasks()
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_store()
    stop_event = asyncio.Event()
    task = asyncio.create_task(orchestration_loop(stop_event))
    try:
        yield
    finally:
        stop_event.set()
        task.cancel()
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
