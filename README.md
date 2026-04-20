# Autonomous Coding Demo

Autonomous Coding Demo is a local, operator-facing reference stack for an
agentic software delivery loop.

It is intentionally small enough to run on a laptop, but complete enough to
show a real workflow:

`Kanboard -> orchestrator -> aider -> local tests -> Gitea Actions -> live app`

This repository is a public demo inspired by a larger proprietary internal
workflow. The architecture, task lifecycle, and operational model are real. The
domain model, data, and surrounding product context are reduced and anonymized
for open publication.

## What It Demonstrates

- human task intake through `Kanboard`
- automatic task claiming by the `orchestrator`
- isolated task execution in dedicated `git worktree` checkouts
- policy-constrained coding with `aider`
- local verification before push
- independent CI in `Gitea Actions`
- promotion of successful changes into a live runtime checkout
- browser-visible deploy artifacts in the sample application

This is not a chat wrapper around a toy app. It is a compact demo of a real
operator workflow for autonomous code delivery.

## Stack Overview

- `pet-app`: the sample target application
- `control-room`: the operator view for pipeline status and artifacts
- `orchestrator`: the task lifecycle engine
- `kanboard`: the human intake board
- `gitea`: git hosting and branch visibility
- `gitea-actions-runner`: the independent CI runner
- `aider`: the coding engine, launched directly by the orchestrator

## Runtime Model

1. A human moves a task to `Ready` in `Kanboard`.
2. The `orchestrator` claims the task.
3. A dedicated task branch and `git worktree` are created.
4. `aider` edits only the files allowed by the execution profile and
   [`docs/AGENT_POLICY.md`](docs/AGENT_POLICY.md).
5. Local tests run inside the task worktree.
6. The task branch is committed and pushed to `Gitea`.
7. `Gitea Actions` validates the branch independently.
8. A successful commit is promoted into the live runtime checkout at
   `data/live_runtime`.
9. `pet-app` serves the promoted code, so browser-visible changes are deploy
   artifacts, not just branch artifacts.

Current branch semantics:

- `main`: repository baseline and manual development
- `codex/development`: long-lived development branch used by the demo
- `codex/<task-id>-<suffix>`: isolated autonomous task branches
- `codex/runtime`: the live runtime branch used for promote-to-live

## Agent Policy

The coding engine is `aider`, configured through project `.env` values and
constrained by one versioned policy file:

- [`docs/AGENT_POLICY.md`](docs/AGENT_POLICY.md)

That file defines:

- global instructions such as smallest-patch behavior
- area-specific heuristics and write-scope expectations
- soft limits that keep autonomous edits narrow and reviewable

The current default coding model is:

- provider: `OpenRouter`
- model: `openrouter/qwen/qwen3-coder-plus`
- reasoning effort: `medium`

`aider` runs in strict `diff` mode and must not mutate `.gitignore`.

## Quick Start

1. Create a local environment file:

```bash
cp .env.example .env
```

2. Fill in the required placeholders in `.env`:

- `OPENROUTER_API_KEY`
- `KANBOARD_ADMIN_USERNAME`
- `KANBOARD_ADMIN_PASSWORD`
- `GITEA_ADMIN_USERNAME`
- `GITEA_ADMIN_PASSWORD`
- `GITEA_PUSH_USERNAME`
- `GITEA_PUSH_PASSWORD`
- `GITEA_RUNNER_REGISTRATION_TOKEN`

If the local Gitea instance is recreated or moved to another port, you can
force a clean runner re-registration by setting:

- `GITEA_RUNNER_FORCE_REREGISTER=true`

3. Create the local Python environment:

```bash
python3.12 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

4. Start the full stack:

```bash
docker compose up --build -d
```

5. Seed Kanboard and the demo task catalog if needed:

```bash
.venv/bin/python scripts/seed_kanboard.py
```

## Manual Demo Flow

1. Open `Kanboard`.
2. Move a backlog card into `Ready`.
3. Watch the task progress in `Control Room`.
4. Inspect the task branch and CI run in `Gitea`.
5. After `Done`, verify the visible change in the live `pet-app`.

Good candidate tasks for a manual run:

- `BL-013` Minimal seed-data enrichment without logic changes
- `BL-014` Return-rate fix through a narrow domain-only patch
- `BL-015` Low-stock indicator without new API surfaces
- `BL-016` Live build badge through a minimal platform patch

## Verified Scenario

The demo has already completed a full end-to-end run for:

- `BL-014` Return-rate fix through a narrow domain-only patch

That run went through:

`Kanboard -> aider -> local tests -> Gitea Actions -> live promote -> Done`

## Default Local URLs

- `pet-app`: [http://localhost:18000](http://localhost:18000)
- `control-room`: [http://localhost:18010](http://localhost:18010)
- `orchestrator`: [http://localhost:18020](http://localhost:18020)
- `kanboard`: [http://localhost:18080](http://localhost:18080)
- `gitea`: [http://localhost:13000](http://localhost:13000)

## Port Map

- `18000` -> `pet-app:8000`
- `18010` -> `control-room:8010`
- `18020` -> `orchestrator:8020`
- `18080` -> `kanboard:80`
- `13000` -> `gitea:3000`
- `12222` -> `gitea:22`

## Testing

Do not run bare `pytest` from the repository root once `data/live_runtime` or
task worktrees exist. Mirrored test files in runtime checkouts can cause
duplicate collection.

Use targeted test commands instead:

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

## Demo-Only Notes

This repository is intentionally a demo stack, not a production platform.

Current demo constraints:

- persistence is still centered on local demo state
- the stack is optimized for local reproducibility, not multi-tenant isolation
- live deploy currently promotes to `codex/runtime` rather than `main`
- credentials are expected to come from local `.env`, not a secret manager
- the sample application is intentionally small and anonymized

## Public Release Notes

This repository is safe to publish as a public demo only if you keep real
credentials out of `.env` and out of git history.

The tracked repository intentionally ships with placeholders such as:

- `replace-me`
- `demo.operator@example.invalid`
- `admin@example.invalid`

Do not replace them with real values in tracked files.

## License

This repository is licensed under the [MIT License](LICENSE).

Third-party software remains under its own licenses. See
[THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md).
