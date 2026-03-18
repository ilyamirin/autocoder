# Autonomous Coding Demo

Docker Compose prototype for an autonomous coding pipeline:

- `Kanboard` as the task tracker
- `Gitea` for git hosting and PR visibility
- `Woodpecker` for CI/CD
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
observability. External integrations with Kanboard, Gitea, and Woodpecker are
introduced progressively rather than hidden behind a large opaque bootstrap.

## Current Milestones Implemented

- repository scaffold with staged implementation plan
- FastAPI services for `pet-app`, `control-room`, and `orchestrator`
- shared SQLite-backed demo task store with seeded backlog and done tasks
- Kanboard seed script that creates the project, user, columns, and cards
- minimal `Woodpecker` pipeline for running `pytest`

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
- `orchestrator`: task lifecycle engine
- `kanboard`: task board and user-facing intake
- `gitea`: repository hosting and PR UI
- `woodpecker-server` / `woodpecker-agent`: CI/CD pipeline execution

## Safety

Secrets are never committed. Use `.env` for local credentials and API keys.
A dedicated secret scan script is run before each commit.
