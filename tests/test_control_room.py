from fastapi.testclient import TestClient

from services.control_room.app import app


def test_control_room_page_renders(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DEMO_DB_PATH", str(tmp_path / "demo.db"))
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "Control Room" in response.text
    assert "Pipeline Tasks" in response.text
    assert "BL-001" in response.text
