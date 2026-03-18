# AGENTS.md

This repository is a local autonomous coding demo platform. Treat it as an
operator-facing demo, not as a generic app repo.

## Environment

- use local Homebrew Python 3.12
- use the project virtualenv only: `.venv`
- main stack is started with `docker compose up --build -d`
- model endpoint is expected at `http://127.0.0.1:8000/` on the host and is
  exposed inside containers via `http://host.docker.internal:8000`

## Git Workflow

- long-lived branches:
  - `main`
  - `codex/development`
- autonomous task branches must use `codex/<task-id>-<unique-suffix>`
- do not reuse a previous task branch name for a rerun
- before every commit run `./scripts/check_no_secrets.sh`

## Runtime Model

- human intake starts in `Kanboard`
- `orchestrator` syncs with `Kanboard` and claims `Ready` tasks
- task code changes happen in `data/worktrees/...`
- successful changes are promoted into the live runtime checkout at
  `data/live_runtime`
- `pet-app` serves code from `data/live_runtime`, so browser-visible changes are
  a deploy artifact, not just a branch artifact

## Kanboard Semantics

- `Done` tasks must remain visible on the board
- do not close completed tasks in `Kanboard`; move them to `Done` and keep them open
- same principle for `Failed`: keep failed cards visible in the `Failed` column

## Testing

- avoid raw `pytest` from repo root once `data/live_runtime` or task worktrees exist
- use targeted root tests, for example:
  - `PYTHONPATH=. .venv/bin/pytest tests/test_kanboard_sync.py tests/test_orchestrator.py tests/test_store.py tests/test_control_room.py tests/test_git_safety.py tests/test_live_runtime.py`
  - `PYTHONPATH=. .venv/bin/pytest tests/test_pet_app.py`

## Safety Constraints

- never commit secrets from `.env`
- do not remove or reset user-created branches or task worktrees unless explicitly asked
- do not break the demo path:
  `Kanboard -> orchestrator -> Gitea Actions -> live pet-app`

## Documentation Rule

If behavior changes in any of these areas, update `README.md` and this file in
the same task:

- ports or credentials
- branch or runtime model
- task lifecycle semantics
- testing commands
