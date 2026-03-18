#!/usr/bin/env python3
from __future__ import annotations

import argparse

from services.common.store import claim_next_ready_task, claim_task, get_task, initialize_store, move_task_to_ready
from services.orchestrator.task_executor import TaskExecutor


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one autonomous coding task locally.")
    parser.add_argument("--task-id", help="Specific task id to execute.")
    parser.add_argument(
        "--force-ready",
        action="store_true",
        help="Move a backlog task to ready before execution.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    initialize_store()

    task = None
    if args.task_id:
        current = get_task(args.task_id)
        if current and current["status"] == "backlog" and args.force_ready:
            move_task_to_ready(args.task_id)
        task = claim_task(args.task_id)
        if not task:
            raise SystemExit(f"Task {args.task_id} is not available in Ready.")
    else:
        task = claim_next_ready_task()
        if not task:
            raise SystemExit("No ready task found.")

    TaskExecutor().execute(task)
    print(f"Executed task {task['id']}.")


if __name__ == "__main__":
    main()
