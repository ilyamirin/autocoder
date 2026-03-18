from fastapi.testclient import TestClient

from services.common.task_catalog import DEFAULT_TASKS
from services.orchestrator.app import app
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
