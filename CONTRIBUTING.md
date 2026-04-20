# Contributing

This repository is a local autonomous coding demo. Contributions should keep
the demo path stable and reproducible.

## Local Setup

1. Use Homebrew Python `3.12`.
2. Create the project virtual environment:

```bash
python3.12 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

3. Copy `.env.example` to `.env` and fill in local credentials.
4. Start the stack with:

```bash
docker compose up --build -d
```

## Development Rules

- use the project virtualenv only: `.venv`
- keep the runtime model intact:
  `Kanboard -> orchestrator -> Gitea Actions -> live pet-app`
- do not commit real credentials or tokens
- do not change `.gitignore` through autonomous agent execution
- update `README.md` and `AGENTS.md` when changing runtime behavior, ports,
  credentials, lifecycle semantics, or coding-agent guardrails

## Branching

- long-lived branches are `main` and `codex/development`
- autonomous task branches use `codex/<task-id>-<unique-suffix>`
- do not reuse an old autonomous branch name for a rerun

## Tests

Avoid bare `pytest` from the repository root after runtime worktrees exist.

Use targeted commands instead:

```bash
PYTHONPATH=. .venv/bin/pytest tests/test_kanboard_sync.py tests/test_orchestrator.py tests/test_store.py tests/test_control_room.py tests/test_git_safety.py tests/test_live_runtime.py
```

```bash
PYTHONPATH=. .venv/bin/pytest tests/test_aider_executor.py tests/test_pet_app.py
```

Before every commit, run:

```bash
./scripts/check_no_secrets.sh
```

## Secrets

- never commit `.env`
- never replace placeholder values in tracked files with real credentials
- if a secret is committed by mistake, remove it from the current tree and from
  git history before publishing
