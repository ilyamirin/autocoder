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

## What Works Now

- full stack runs in one `docker compose`
- `Kanboard` is the human task intake and status board
- `orchestrator` claims `Ready` tasks from `Kanboard`
- the executor creates a dedicated `git worktree` and `codex/...` branch per run
- the coding agent runs through `aider` in the existing orchestrator container and edits only whitelisted files
- the executor runs local tests, pushes to `Gitea`, waits for `Gitea Actions`, and promotes successful changes into the live runtime branch
- the running `pet-app` serves code from the live runtime worktree, so successful tasks become visible in the browser
- completed tasks remain visible in the `Done` column in `Kanboard`

## Development

1. Copy `.env.example` to `.env`
2. Fill the placeholder values
3. Build and run the stack:

```bash
docker compose up --build
```

The repository is developed with local Homebrew Python 3.12 and a local virtual
environment:

```bash
python3.12 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

## Manual Demo Flow

1. Open `Kanboard`
2. Move a backlog task into `Ready`
3. Wait for `orchestrator` to claim it and move it through `Planning`, `Coding`, `Testing`, `Deploy`, and `Done`
4. Watch branch, commit, and CI status in `Gitea`
5. Refresh the live `pet-app` and verify the change in the browser

The currently verified end-to-end task is `BL-008`, which adds a visible `Low stock`
badge on the live `/products` page.

## Services

- `pet-app`: seller dashboard demo application
- `control-room`: pipeline status dashboard
- `orchestrator`: task lifecycle engine and autonomous executor
- `aider`: invoked directly by the orchestrator inside each task worktree
- `kanboard`: task board and user-facing intake
- `gitea`: repository hosting and PR UI
- `gitea-actions-runner`: executes Gitea Actions jobs in Docker

## Default URLs

- `pet-app`: [http://localhost:18000](http://localhost:18000)
- `control-room`: [http://localhost:18010](http://localhost:18010)
- `orchestrator`: [http://localhost:18020](http://localhost:18020)
- `kanboard`: [http://localhost:18080](http://localhost:18080)
- `gitea`: [http://localhost:13000](http://localhost:13000)

## Demo Credentials

- `Kanboard` admin: `configured in .env`
- `Kanboard` demo user: `demo.operator / replace-me`
- `Gitea`: `ilya / replace-me`

## Agent Execution

- the executor watches `Ready` tasks and claims one at a time
- each task gets its own `git worktree` and branch under `codex/...`
- the coding agent is `aider`, launched directly by the orchestrator inside the task worktree
- `aider` uses `OpenRouter` credentials from `.env` together with global `CODING_*` settings
- `aider` runs in a strict `diff` edit mode and does not mutate `.gitignore`
- `aider` logs and LLM history are stored under `data/aider`
- after `aider` finishes, the orchestrator runs authoritative local tests, commits, pushes, and waits for `Gitea Actions`
- successful tasks are promoted into the managed live runtime worktree under `data/live_runtime`
- branch, commit, CI, and live commit metadata are written back into the control-room store
- executor profiles currently cover all backlog areas: `finance`, `orders`, `dashboard`, `products`, `platform`, and `data`
- backlog tasks are marked with `execution_risk`: `safe`, `medium`, or `review`

For isolated local runs without waiting for the compose orchestrator:

```bash
PYTHONPATH=. .venv/bin/python scripts/run_executor_once.py --task-id BL-001 --force-ready
```

## Infrastructure Sizing

If `aider` is configured to use `OpenRouter` or another external model
provider, this stack does not require a local GPU. The server-side load comes
from local tests, `Gitea Actions`, git worktrees, logs, and disk I/O rather
than model inference.

### Current Runtime Characteristics

- the current orchestrator executes one claimed task at a time
- each task creates a dedicated worktree
- CI jobs run through `Gitea Actions` and consume the same host resources
- the demo stack currently uses local `SQLite` files, which is acceptable for a
  demo but not ideal for a multi-user long-running environment

### Recommended Starting Point

For a small operator team of roughly `5-7` people creating about `5-6` tasks
per day, start with:

- `8 vCPU`
- `16 GB RAM`
- `300-500 GB NVMe SSD`
- `Ubuntu 24.04 LTS`
- no GPU

This is a good fit when the autonomous pipeline is mostly processing one active
task at a time and the target repository has moderate test and build cost.

### Comfortable Capacity

If the educational portal repository grows to include heavier frontend builds,
backend services, larger test suites, or you want headroom for overlapping CI
activity, use:

- `12-16 vCPU`
- `32 GB RAM`
- `500 GB NVMe SSD`
- no GPU

This is the recommended production-oriented starting point for a real team,
even if daily ticket volume is still moderate.

### Database Recommendation

Before relying on the system for ongoing team work, move persistent services off
`SQLite`:

- use `PostgreSQL` for `Gitea`
- use `PostgreSQL` for the internal control-room and orchestrator store

`SQLite` is convenient for the demo, but the first operational bottlenecks for
this architecture are more likely to be database concurrency, CI contention,
and disk I/O than raw CPU.

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
- the orchestrator bind-mounts the repo, creates task worktrees in `data/worktrees`, and manages the live runtime worktree in `data/live_runtime`
- the orchestrator launches `aider` directly as a subprocess inside the existing container
- no additional coding-agent service or sandbox containers are created for task execution

## Safety

Secrets are never committed. Use `.env` for local credentials and API keys.
A dedicated secret scan script is run before each commit.

Git operations inside the executor are protected by a small safety helper so
stale `.lock` files do not break autonomous runs.

## License

This repository's original code is licensed under the MIT License. See
[LICENSE](LICENSE).

Third-party software used by this project, including Kanboard, Gitea, Gitea
`act_runner`, optional `aider` usage, Python, and Python package dependencies,
remains under each component's own license. In particular, `aider` is
`Apache-2.0` licensed and is compatible to use alongside this repository
without changing the repository's own `MIT` license, as long as upstream
third-party notices are preserved when redistributed. See
[THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md).

## Test Notes

Do not run bare `pytest` from the repository root after the live runtime or
task worktrees exist. Those directories contain mirrored test files and pytest
will collect duplicates.

Use one of these instead:

```bash
PYTHONPATH=. .venv/bin/pytest tests/test_kanboard_sync.py tests/test_orchestrator.py tests/test_store.py tests/test_control_room.py tests/test_git_safety.py tests/test_live_runtime.py
```

or:

```bash
PYTHONPATH=. .venv/bin/pytest tests/test_pet_app.py
```
