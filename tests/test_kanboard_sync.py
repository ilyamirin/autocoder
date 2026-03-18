from services.common.store import get_task, initialize_store
from services.orchestrator.app import sync_terminal_kanboard_state


class FakeKanboardSync:
    enabled = True

    def __init__(self, remote_status: str) -> None:
        self._remote_status = remote_status

    def remote_tasks(self) -> dict[str, dict]:
        return {"BL-002": {"id": 42, "column_id": 2, "description": "Demo task id: `BL-002`"}}

    def board_status(self, remote_task: dict) -> str:
        return self._remote_status


def test_kanboard_ready_status_is_mirrored_locally(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DEMO_DB_PATH", str(tmp_path / "demo.db"))
    initialize_store()

    sync_terminal_kanboard_state(FakeKanboardSync("ready"))

    task = get_task("BL-002")
    assert task is not None
    assert task["status"] == "ready"


def test_kanboard_failed_status_is_mirrored_locally(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DEMO_DB_PATH", str(tmp_path / "demo.db"))
    initialize_store()

    sync_terminal_kanboard_state(FakeKanboardSync("failed"))

    task = get_task("BL-002")
    assert task is not None
    assert task["status"] == "failed"
