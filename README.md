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
- the coding agent calls a local OpenAI-compatible model endpoint and edits only whitelisted files
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
- `kanboard`: task board and user-facing intake
  - includes the repo-local `GcgTheme` plugin for the golden-canon-inspired board layout
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
- the coding agent calls the local OpenAI-compatible model service from `MODEL_BASE_URL`
- the agent writes full-file replacements for a constrained file set, runs `pytest`, commits, pushes, and waits for `Gitea Actions`
- successful tasks are promoted into the managed live runtime worktree under `data/live_runtime`
- branch, commit, CI, and live commit metadata are written back into the control-room store
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
- `kanboard` loads the repo-local theme plugin from `infra/kanboard/plugins/GcgTheme`
- `gitea-actions-runner` registers itself with the static instance token exposed by `Gitea`
- the runner and action job containers reach the local forge through `http://host.docker.internal:13000`
- the orchestrator bind-mounts the repo, creates task worktrees in `data/worktrees`, and manages the live runtime worktree in `data/live_runtime`
- the orchestrator reaches the host model service through `host.docker.internal`

## Kanboard Theme

Kanboard is styled through a repo-local plugin instead of a core fork:

- plugin path: `infra/kanboard/plugins/GcgTheme`
- copied into the writable Kanboard plugin directory on container start
- injects a custom CSS layer plus login and header overrides
- keeps the Kanboard upgrade surface small while giving the board an editorial GCG-inspired layout

## Safety

Secrets are never committed. Use `.env` for local credentials and API keys.
A dedicated secret scan script is run before each commit.

Git operations inside the executor are protected by a small safety helper so
stale `.lock` files do not break autonomous runs.

## License

This repository's original code is licensed under the MIT License. See
[LICENSE](LICENSE).

Third-party software used by this project, including Kanboard, Gitea, Gitea
`act_runner`, Python, and Python package dependencies, remains under each
component's own license. See [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md).

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
