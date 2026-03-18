from services.common.store import get_task, initialize_store, update_task


def test_runtime_done_task_is_not_reset_to_catalog_backlog(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DEMO_DB_PATH", str(tmp_path / "demo.db"))
    initialize_store()

    update_task("BL-002", status="done")
    initialize_store()

    task = get_task("BL-002")
    assert task is not None
    assert task["status"] == "done"
