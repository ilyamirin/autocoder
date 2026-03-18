from fastapi.testclient import TestClient

from services.orchestrator.app import app


def test_orchestrator_lists_seeded_tasks(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DEMO_DB_PATH", str(tmp_path / "demo.db"))
    client = TestClient(app)
    response = client.get("/api/tasks")
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) >= 20
    assert any(item["status"] == "backlog" for item in items)
