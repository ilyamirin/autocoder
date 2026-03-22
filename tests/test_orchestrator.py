from fastapi.testclient import TestClient

from services.common.task_catalog import DEFAULT_TASKS
from services.orchestrator.app import _should_accept_remote_status, app
from services.orchestrator.task_executor import AREA_PROFILES


def test_orchestrator_lists_seeded_tasks(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DEMO_DB_PATH", str(tmp_path / "demo.db"))
    client = TestClient(app)
    response = client.get("/api/tasks")
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) >= 20
    assert any(item["status"] == "backlog" for item in items)


def test_backlog_tasks_have_profiles_and_risk_labels() -> None:
    backlog_tasks = [task for task in DEFAULT_TASKS if task["status"] == "backlog"]
    assert backlog_tasks
    assert {task["target_area"] for task in backlog_tasks}.issubset(AREA_PROFILES.keys())
    assert all(task.get("execution_risk") in {"safe", "medium", "review"} for task in backlog_tasks)


def test_completed_task_is_not_downgraded_back_to_backlog() -> None:
    task = {
        "status": "done",
        "commit_sha": "abc123",
        "live_commit_sha": "def456",
    }

    assert _should_accept_remote_status(task, "backlog") is False
    assert _should_accept_remote_status(task, "ready") is False
    assert _should_accept_remote_status(task, "failed") is True
