from fastapi.testclient import TestClient

from services.common.store import initialize_store, update_task
from services.control_room.app import app


def test_control_room_page_renders(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DEMO_DB_PATH", str(tmp_path / "demo.db"))
    initialize_store()
    update_task("BL-001", status="coding", branch_name="codex/bl-001-demo", repo_link=None)
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "Control Room" in response.text
    assert "Pipeline Tasks" in response.text
    assert "BL-001" in response.text
    assert "local worktree only" in response.text
    assert "setTimeout(() => window.location.reload(), 3000);" in response.text
