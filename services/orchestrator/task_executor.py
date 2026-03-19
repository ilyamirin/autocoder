from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

from services.common.git_safety import GitSafetyError, run_git_command
from services.common.live_runtime import LiveRuntimeConfig, ensure_live_worktree, promote_commit_to_live
from services.common.kanboard import KanboardSync
from services.common.store import add_event, mark_task_failed, update_task


class TaskExecutionError(RuntimeError):
    pass


@dataclass(frozen=True)
class TaskProfile:
    allowed_files: tuple[str, ...]
    test_args: tuple[str, ...]


AREA_PROFILES: dict[str, TaskProfile] = {
    "dashboard": TaskProfile(
        allowed_files=(
            "services/pet_app/domain.py",
            "services/pet_app/app.py",
            "services/pet_app/templates/dashboard.html",
            "tests/test_pet_app.py",
        ),
        test_args=("-m", "pytest", "tests/test_pet_app.py"),
    ),
    "finance": TaskProfile(
        allowed_files=("services/pet_app/domain.py", "tests/test_pet_app.py"),
        test_args=("-m", "pytest", "tests/test_pet_app.py"),
    ),
    "orders": TaskProfile(
        allowed_files=(
            "services/pet_app/domain.py",
            "services/pet_app/app.py",
            "services/pet_app/templates/orders.html",
            "tests/test_pet_app.py",
        ),
        test_args=("-m", "pytest", "tests/test_pet_app.py"),
    ),
    "products": TaskProfile(
        allowed_files=(
            "services/pet_app/domain.py",
            "services/pet_app/app.py",
            "services/pet_app/templates/products.html",
            "tests/test_pet_app.py",
        ),
        test_args=("-m", "pytest", "tests/test_pet_app.py"),
    ),
    "platform": TaskProfile(
        allowed_files=(
            "services/pet_app/app.py",
            "services/pet_app/templates/base.html",
            "services/pet_app/templates/dashboard.html",
            "tests/test_pet_app.py",
        ),
        test_args=("-m", "pytest", "tests/test_pet_app.py"),
    ),
    "data": TaskProfile(
        allowed_files=(
            "services/pet_app/domain.py",
            "services/pet_app/templates/dashboard.html",
            "tests/test_pet_app.py",
        ),
        test_args=("-m", "pytest", "tests/test_pet_app.py"),
    ),
}


@dataclass(frozen=True)
class ExecutorConfig:
    repo_root: Path
    worktree_root: Path
    base_branch: str
    bootstrap_branch: str
    live_worktree_path: Path
    model_base_url: str
    model_name: str
    reasoning_effort: str
    model_timeout_seconds: int
    push_enabled: bool
    gitea_owner: str
    gitea_repo: str
    gitea_push_base_url: str
    gitea_username: str
    gitea_password: str
    gitea_api_base_url: str
    gitea_http_base_url: str
    ci_poll_timeout_seconds: int
    ci_poll_interval_seconds: int

    @classmethod
    def from_env(cls) -> "ExecutorConfig":
        repo_root = Path(os.getenv("DEMO_REPO_ROOT", Path(__file__).resolve().parents[2])).resolve()
        worktree_root = Path(
            os.getenv("DEMO_WORKTREE_ROOT", repo_root / "data" / "worktrees")
        ).resolve()
        return cls(
            repo_root=repo_root,
            worktree_root=worktree_root,
            base_branch=os.getenv("EXECUTOR_RUNTIME_BRANCH", "codex/runtime"),
            bootstrap_branch=os.getenv("EXECUTOR_BOOTSTRAP_BRANCH", "codex/development"),
            live_worktree_path=Path(
                os.getenv("LIVE_WORKTREE_PATH", repo_root / "data" / "live_runtime")
            ).resolve(),
            model_base_url=os.getenv("MODEL_BASE_URL", "http://127.0.0.1:8000"),
            model_name=os.getenv("OPENAI_MODEL", "gpt-5.4"),
            reasoning_effort=os.getenv("MODEL_REASONING_EFFORT", "medium"),
            model_timeout_seconds=int(os.getenv("MODEL_TIMEOUT_SECONDS", "120")),
            push_enabled=os.getenv("EXECUTOR_PUSH_ENABLED", "true").lower() == "true",
            gitea_owner=os.getenv("GITEA_REPO_OWNER", "ilya"),
            gitea_repo=os.getenv("GITEA_REPO_NAME", "autonomous-coding-demo"),
            gitea_push_base_url=os.getenv("GITEA_PUSH_BASE_URL", "http://localhost:13000"),
            gitea_username=os.getenv("GITEA_PUSH_USERNAME", ""),
            gitea_password=os.getenv("GITEA_PUSH_PASSWORD", ""),
            gitea_api_base_url=os.getenv("GITEA_API_BASE_URL", "http://localhost:13000"),
            gitea_http_base_url=os.getenv("GITEA_HTTP_BASE_URL", "http://localhost:13000"),
            ci_poll_timeout_seconds=int(os.getenv("CI_POLL_TIMEOUT_SECONDS", "180")),
            ci_poll_interval_seconds=int(os.getenv("CI_POLL_INTERVAL_SECONDS", "5")),
        )


class ModelClient:
    def __init__(self, config: ExecutorConfig) -> None:
        self._config = config

    def generate_plan(self, task: dict[str, Any], profile: TaskProfile, repo_root: Path) -> dict[str, Any]:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a precise software engineer. Return JSON only. "
                    "Do not wrap it in markdown. "
                    "You may only modify files from the allowed list. "
                    "Update or add tests when needed."
                ),
            },
            {
                "role": "user",
                "content": self._build_user_prompt(task, profile, repo_root),
            },
        ]
        payload = {
            "model": self._config.model_name,
            "reasoning_effort": self._config.reasoning_effort,
            "messages": messages,
            "response_format": {"type": "json_object"},
        }
        with httpx.Client(
            base_url=self._config.model_base_url.rstrip("/"),
            timeout=httpx.Timeout(self._config.model_timeout_seconds),
        ) as client:
            response = client.post("/v1/chat/completions", json=payload)
            response.raise_for_status()
            body = response.json()

        try:
            content = body["choices"][0]["message"]["content"]
            plan = json.loads(content)
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            raise TaskExecutionError(f"Model returned an invalid response: {body!r}") from exc

        if not isinstance(plan.get("files"), list) or not plan["files"]:
            raise TaskExecutionError("Model did not return any file edits.")
        return plan

    def _build_user_prompt(self, task: dict[str, Any], profile: TaskProfile, repo_root: Path) -> str:
        sections = [
            f"Task ID: {task['id']}",
            f"Title: {task['title']}",
            f"Kind: {task['kind']}",
            f"Summary: {task['summary']}",
            f"Acceptance criteria: {task['acceptance_criteria']}",
            "",
            "Allowed files:",
            *[f"- {path}" for path in profile.allowed_files],
            "",
            "Return JSON with this shape:",
            (
                '{"summary":"short summary","commit_message":"short commit message",'
                '"files":[{"path":"relative/path.py","content":"full replacement file content"}]}'
            ),
            "",
            "Relevant repository files:",
        ]
        for relative_path in profile.allowed_files:
            file_path = repo_root / relative_path
            sections.append(f"\nFILE: {relative_path}\n")
            sections.append(file_path.read_text())
        return "\n".join(sections)


class TaskExecutor:
    def __init__(
        self,
        config: ExecutorConfig | None = None,
        model_client: ModelClient | None = None,
        kanboard_sync: KanboardSync | None = None,
    ) -> None:
        self._config = config or ExecutorConfig.from_env()
        self._model_client = model_client or ModelClient(self._config)
        self._kanboard_sync = kanboard_sync
        self._live_runtime = LiveRuntimeConfig(
            repo_root=self._config.repo_root,
            bootstrap_branch=self._config.bootstrap_branch,
            runtime_branch=self._config.base_branch,
            live_worktree_path=self._config.live_worktree_path,
        )

    def execute(self, task: dict[str, Any]) -> None:
        profile = AREA_PROFILES.get(task["target_area"])
        if not profile:
            raise TaskExecutionError(
                f"No execution profile is configured for target area '{task['target_area']}'."
            )

        worktree_path: Path | None = None
        branch_name: str | None = None
        try:
            ensure_live_worktree(self._live_runtime)
            worktree_path, branch_name = self._create_worktree(task["id"])
            ci_link = self._ci_link()
            self._update_task(
                task["id"],
                status="coding",
                branch_name=branch_name,
                repo_link=None,
                ci_link=ci_link,
                worktree_path=str(worktree_path),
                event_type="coding",
                event_message=f"Created worktree {worktree_path.name} on branch {branch_name}.",
            )

            plan = self._model_client.generate_plan(task, profile, worktree_path)
            self._apply_plan(worktree_path, profile, plan)
            add_event(task["id"], "agent", plan.get("summary", "Model generated code changes."))

            self._update_task(
                task["id"],
                status="testing",
                event_type="testing",
                event_message=f"Running local tests: {shlex.join(self._test_command(profile))}",
            )
            self._run(self._test_command(profile), cwd=worktree_path)

            commit_message = plan.get("commit_message") or f"Resolve {task['id']}: {task['title']}"
            commit_sha = self._commit_and_optionally_push(worktree_path, branch_name, commit_message)

            self._update_task(
                task["id"],
                commit_sha=commit_sha,
                repo_link=self._repo_link(branch_name),
                ci_link=ci_link,
                event_type="commit",
                event_message=f"Committed changes as {commit_sha[:7]} and pushed branch {branch_name}.",
            )

            if self._config.push_enabled:
                self._wait_for_ci(commit_sha, task["id"])
            self._update_task(
                task["id"],
                status="deploy",
                event_type="deploy",
                event_message="Promoting the successful task branch into the live pet-app runtime.",
            )
            deployed_sha = self._promote_to_live(commit_sha, task["id"])
            self._update_task(
                task["id"],
                status="done",
                live_commit_sha=deployed_sha,
                last_error=None,
                event_type="done",
                event_message="Agent execution finished successfully.",
            )
        except Exception as exc:
            mark_task_failed(task["id"], f"Execution failed: {exc}")
            self._sync_kanboard_status(task["id"], "failed")
            raise
        finally:
            if worktree_path and worktree_path.exists():
                self._cleanup_worktree(worktree_path, branch_name)

    def _create_worktree(self, task_id: str) -> tuple[Path, str]:
        self._config.worktree_root.mkdir(parents=True, exist_ok=True)
        branch_name = f"codex/{task_id.lower()}-{int(time.time() * 1000)}"
        worktree_path = self._config.worktree_root / branch_name.replace("/", "-")
        if worktree_path.exists():
            shutil.rmtree(worktree_path)
        self._run(
            (
                "git",
                "worktree",
                "add",
                "-b",
                branch_name,
                str(worktree_path),
                self._config.base_branch,
            ),
            cwd=self._config.repo_root,
        )
        return worktree_path, branch_name

    def _apply_plan(self, worktree_path: Path, profile: TaskProfile, plan: dict[str, Any]) -> None:
        allowed_paths = {path: (worktree_path / path).resolve() for path in profile.allowed_files}
        for file_edit in plan["files"]:
            relative_path = file_edit.get("path")
            content = file_edit.get("content")
            if relative_path not in allowed_paths:
                raise TaskExecutionError(f"Model tried to edit unsupported file '{relative_path}'.")
            if not isinstance(content, str):
                raise TaskExecutionError(f"Model returned non-text content for '{relative_path}'.")
            target_path = allowed_paths[relative_path]
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(content)

    def _commit_and_optionally_push(
        self, worktree_path: Path, branch_name: str, commit_message: str
    ) -> str:
        self._run(("git", "add", "-A"), cwd=worktree_path)
        self._run(
            (
                "git",
                "-c",
                "user.name=Autonomous Coding Agent",
                "-c",
                "user.email=agent@local.demo",
                "commit",
                "-m",
                commit_message,
            ),
            cwd=worktree_path,
        )
        commit_sha = self._run(("git", "rev-parse", "HEAD"), cwd=worktree_path).strip()
        if self._config.push_enabled:
            self._run(("git", "push", self._push_url(), f"HEAD:{branch_name}"), cwd=worktree_path)
        return commit_sha

    def _wait_for_ci(self, commit_sha: str, task_id: str) -> None:
        deadline = self._config.ci_poll_timeout_seconds
        with httpx.Client(
            base_url=self._config.gitea_api_base_url.rstrip("/"),
            auth=(self._config.gitea_username, self._config.gitea_password),
            timeout=httpx.Timeout(20.0),
        ) as client:
            for _ in range(0, deadline, self._config.ci_poll_interval_seconds):
                response = client.get(
                    f"/api/v1/repos/{self._config.gitea_owner}/{self._config.gitea_repo}/actions/tasks"
                )
                response.raise_for_status()
                runs = response.json().get("workflow_runs", [])
                for run in runs:
                    if run.get("head_sha") != commit_sha:
                        continue
                    status = run.get("status")
                    add_event(task_id, "ci", f"Gitea Actions run #{run['run_number']} is {status}.")
                    if status == "success":
                        return
                    if status == "failure":
                        raise TaskExecutionError(
                            f"Gitea Actions run #{run['run_number']} failed for {commit_sha[:7]}."
                        )
                time.sleep(self._config.ci_poll_interval_seconds)
        raise TaskExecutionError(f"Timed out waiting for Gitea Actions on {commit_sha[:7]}.")

    def _cleanup_worktree(self, worktree_path: Path, branch_name: str | None) -> None:
        self._run(("git", "worktree", "remove", "--force", str(worktree_path)), cwd=self._config.repo_root)
        if branch_name:
            self._run(("git", "branch", "-D", branch_name), cwd=self._config.repo_root, check=False)

    def _test_command(self, profile: TaskProfile) -> tuple[str, ...]:
        return (sys.executable, *profile.test_args)

    def _repo_link(self, branch_name: str) -> str:
        return (
            f"{self._config.gitea_http_base_url.rstrip('/')}/"
            f"{self._config.gitea_owner}/{self._config.gitea_repo}/src/branch/{branch_name}"
        )

    def _ci_link(self) -> str:
        return (
            f"{self._config.gitea_http_base_url.rstrip('/')}/"
            f"{self._config.gitea_owner}/{self._config.gitea_repo}/actions"
        )

    def _promote_to_live(self, commit_sha: str, task_id: str) -> str:
        try:
            deployed_sha = promote_commit_to_live(self._live_runtime, commit_sha)
        except GitSafetyError as exc:
            raise TaskExecutionError(str(exc)) from exc
        add_event(
            task_id,
            "deploy",
            (
                f"Live runtime branch {self._live_runtime.runtime_branch} now includes "
                f"{deployed_sha[:7]} and the pet-app should auto-reload."
            ),
        )
        return deployed_sha

    def _push_url(self) -> str:
        if not self._config.gitea_username or not self._config.gitea_password:
            raise TaskExecutionError("Missing Gitea push credentials for executor.")
        username = quote(self._config.gitea_username, safe="")
        password = quote(self._config.gitea_password, safe="")
        base_url = self._config.gitea_push_base_url.rstrip("/")
        authenticated_base = base_url.replace("://", f"://{username}:{password}@", 1)
        return f"{authenticated_base}/{self._config.gitea_owner}/{self._config.gitea_repo}.git"

    def _run(
        self, command: tuple[str, ...], *, cwd: Path, check: bool = True, timeout: int = 180
    ) -> str:
        if command and command[0] == "git":
            try:
                completed = run_git_command(
                    command,
                    cwd=cwd,
                    check=False,
                    timeout=timeout,
                )
            except GitSafetyError as exc:
                raise TaskExecutionError(str(exc)) from exc
        else:
            completed = subprocess.run(
                command,
                cwd=cwd,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        if check and completed.returncode != 0:
            raise TaskExecutionError(
                f"Command failed: {shlex.join(command)}\nSTDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
            )
        return completed.stdout.strip()

    def _update_task(
        self,
        task_id: str,
        *,
        event_type: str | None = None,
        event_message: str | None = None,
        **fields: Any,
    ) -> None:
        update_task(task_id, event_type=event_type, event_message=event_message, **fields)
        status = fields.get("status")
        if status:
            self._sync_kanboard_status(task_id, status)

    def _sync_kanboard_status(self, task_id: str, status: str) -> None:
        if not self._kanboard_sync or not self._kanboard_sync.enabled:
            return
        try:
            self._kanboard_sync.sync_task_status(task_id, status)
        except Exception as exc:
            add_event(task_id, "kanboard", f"Kanboard status sync failed: {exc}")
