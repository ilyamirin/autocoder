# Autonomous Coding Demo

Docker Compose prototype for an autonomous coding pipeline:

- `Kanboard` as the task tracker
- `Gitea` for git hosting and PR visibility
- `Gitea Actions` for CI/CD
- `orchestrator` as the pipeline state machine
- `control-room` as the unified operator dashboard
- `pet-app` as the target application agents improve

The pet app is a compact seller operations dashboard that acts as a reduced
copy of an e-commerce seller back office. It is intentionally small but rich
enough to produce visible bugs, fixes, tests, and deployments.

## Current Scope

This repository starts with a working scaffold:

- project plan with stage-by-stage Definition of Done
- compose topology for the full stack
- Python service skeletons for the custom services
- seedable demo data for the pet app and control room

The first implementation milestone focuses on local reproducibility and
observability. External integrations with Kanboard and Gitea are introduced
progressively rather than hidden behind a large opaque bootstrap.

## Current Milestones Implemented

- repository scaffold with staged implementation plan
- FastAPI services for `pet-app`, `control-room`, and `orchestrator`
- shared SQLite-backed demo task store with seeded backlog and done tasks
- Kanboard seed script that creates the project, user, columns, and cards
- minimal `Gitea Actions` workflow for running `pytest`
- real task executor with `git worktree`, model-driven file edits, commit, push, and CI polling

## Development

1. Copy `.env.example` to `.env`
2. Fill the placeholder values
3. Build and run the stack:

```bash
docker compose up --build
```

## Services

- `pet-app`: seller dashboard demo application
- `control-room`: pipeline status dashboard
- `orchestrator`: task lifecycle engine and autonomous executor
- `kanboard`: task board and user-facing intake
- `gitea`: repository hosting and PR UI
- `gitea-actions-runner`: executes Gitea Actions jobs in Docker

## Agent Execution

- the executor watches `Ready` tasks and claims one at a time
- each task gets its own `git worktree` and branch under `codex/...`
- the coding agent calls the local OpenAI-compatible model service from `MODEL_BASE_URL`
- the agent writes full-file replacements for a constrained file set, runs `pytest`, commits, pushes, and waits for `Gitea Actions`
- branch, commit, and CI links are written back into the control-room store
- executor profiles currently cover all backlog areas: `finance`, `orders`, `dashboard`, `products`, `platform`, and `data`
- backlog tasks are marked with `execution_risk`: `safe`, `medium`, or `review`

For isolated local runs without waiting for the compose orchestrator:

```bash
PYTHONPATH=. .venv/bin/python scripts/run_executor_once.py --task-id BL-001 --force-ready
```

## Port Map

- `18000` -> `pet-app:8000`
- `18010` -> `control-room:8010`
- `18020` -> `orchestrator:8020`
- `18080` -> `kanboard:80`
- `13000` -> `gitea:3000`
- `12222` -> `gitea:22`

## Routing

- human task intake starts in `Kanboard`
- the demo services share state through `data/demo.db`
- `control-room` links out to `Kanboard`, `Gitea`, `Gitea Actions`, and the live `pet-app`
- `kanboard-seed` uses JSON-RPC against `http://kanboard/jsonrpc.php`
- `gitea-actions-runner` registers itself with the static instance token exposed by `Gitea`
- the runner and action job containers reach the local forge through `http://host.docker.internal:13000`
- the orchestrator bind-mounts the repo, creates worktrees in `data/worktrees`, and reaches the host model service through `host.docker.internal`

## Safety

Secrets are never committed. Use `.env` for local credentials and API keys.
A dedicated secret scan script is run before each commit.
