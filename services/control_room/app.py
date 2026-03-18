from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from services.common.store import build_status_summary, initialize_store, list_recent_events, list_tasks

@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_store()
    yield


app = FastAPI(title="Control Room", lifespan=lifespan)
templates = Jinja2Templates(directory="services/control_room/templates")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request) -> HTMLResponse:
    context = {
        "request": request,
        "tasks": list_tasks(),
        "summary": build_status_summary(),
        "events": list_recent_events(),
    }
    return templates.TemplateResponse(request, "index.html", context)
