from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

from services.common.git_safety import GitSafetyError, normalize_worktree_gitdir, run_git_command
from services.common.kanboard import KanboardSync
from services.common.live_runtime import LiveRuntimeConfig, ensure_live_worktree, promote_commit_to_live
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
    coding_agent_bin: str
    coding_model: str
    coding_base_url: str | None
    coding_timeout_seconds: int
    coding_reasoning_effort: str
    coding_extended_thinking_budget: int
    coding_critic_max_iterations: int
    coding_map_tokens: int
    coding_edit_format: str
    coding_log_root: Path
    coding_cache_prompts: bool
    coding_log_completions: bool
    coding_show_model_warnings: bool
    coding_check_model_accepts_settings: bool
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
            coding_agent_bin=os.getenv("CODING_AGENT_BIN", "/usr/local/bin/aider"),
            coding_model=os.getenv("CODING_MODEL", "openrouter/qwen/qwen3-coder-plus"),
            coding_base_url=os.getenv("CODING_BASE_URL") or None,
            coding_timeout_seconds=int(os.getenv("CODING_TIMEOUT_SECONDS", "900")),
            coding_reasoning_effort=os.getenv("CODING_REASONING_EFFORT", "medium"),
            coding_extended_thinking_budget=int(
                os.getenv("CODING_EXTENDED_THINKING_BUDGET", "200000")
            ),
            coding_critic_max_iterations=int(os.getenv("CODING_CRITIC_MAX_ITERATIONS", "5")),
            coding_map_tokens=int(os.getenv("CODING_MAP_TOKENS", "0")),
            coding_edit_format=os.getenv("CODING_EDIT_FORMAT", "diff"),
            coding_log_root=Path(
                os.getenv("CODING_LOG_ROOT", repo_root / "data" / "aider")
            ).resolve(),
            coding_cache_prompts=os.getenv("CODING_CACHE_PROMPTS", "true").lower() == "true",
            coding_log_completions=os.getenv("CODING_LOG_COMPLETIONS", "true").lower() == "true",
            coding_show_model_warnings=os.getenv("CODING_SHOW_MODEL_WARNINGS", "false").lower()
            == "true",
            coding_check_model_accepts_settings=os.getenv(
                "CODING_CHECK_MODEL_ACCEPTS_SETTINGS", "false"
            ).lower()
            == "true",
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


class AiderClient:
    def __init__(self, config: ExecutorConfig) -> None:
        self._config = config

    def run_task(self, task: dict[str, Any], profile: TaskProfile, worktree_path: Path) -> dict[str, Any]:
        run_root = self._prepare_run_root(task["id"])
        prompt_path = run_root / "prompt.md"
        stdout_log_path = run_root / "stdout.log"
        stderr_log_path = run_root / "stderr.log"
        chat_history_path = run_root / "chat.history.md"
        input_history_path = run_root / "input.history"
        llm_history_path = run_root / "llm.history"
        prompt_path.write_text(self._build_task_prompt(task, profile))

        command = self._build_command(
            prompt_path=prompt_path,
            chat_history_path=chat_history_path,
            input_history_path=input_history_path,
            llm_history_path=llm_history_path,
            profile=profile,
        )
        env = self._build_env(
            chat_history_path=chat_history_path,
            input_history_path=input_history_path,
            llm_history_path=llm_history_path,
        )

        try:
            completed = subprocess.run(
                command,
                cwd=worktree_path,
                env=env,
                check=False,
                capture_output=True,
                text=True,
                timeout=self._config.coding_timeout_seconds + 120,
            )
        except subprocess.TimeoutExpired as exc:
            stdout_text = exc.stdout or ""
            stderr_text = (exc.stderr or "") + "\nTimed out waiting for aider.\n"
            stdout_log_path.write_text(stdout_text)
            stderr_log_path.write_text(stderr_text)
            raise TaskExecutionError(
                "aider timed out. "
                f"See logs at {stdout_log_path} and {stderr_log_path}."
            ) from exc

        stdout_log_path.write_text(completed.stdout)
        stderr_log_path.write_text(completed.stderr)

        if completed.returncode != 0:
            raise TaskExecutionError(
                "aider execution did not complete cleanly. "
                f"See logs at {stdout_log_path}, {stderr_log_path}, and {llm_history_path}."
            )

        return {
            "summary": self._extract_summary(completed.stdout),
            "event_excerpt": self._extract_event_excerpt(completed.stdout),
            "stdout_log_path": str(stdout_log_path),
            "stderr_log_path": str(stderr_log_path),
            "llm_history_path": str(llm_history_path),
            "chat_history_path": str(chat_history_path),
            "input_history_path": str(input_history_path),
        }

    def _build_task_prompt(self, task: dict[str, Any], profile: TaskProfile) -> str:
        sections = [
            "You are aider working on a single autonomous coding task.",
            "Operate only inside the current working directory, which is the repository root for this task worktree.",
            "All file paths below are relative to the current working directory.",
            "Use the allowed file paths exactly as written. Do not prepend the workspace path to them.",
            "Do not create commits, do not push branches, and do not change remotes.",
            "Only edit files from the allowed list below.",
            "If the task cannot be solved within the allowed files, stop and explain why.",
            "You are not done until at least one allowed file has changed.",
            (
                "Before finishing, do a final self-review pass and tighten the patch if you spot any "
                f"remaining issue. Internal refinement budget: up to {self._config.coding_critic_max_iterations} passes."
            ),
            "Do not narrate shell commands, test commands, or filenames outside structured edits.",
            "When you are done, leave the modified files in the workspace and finish with a concise summary of the code change.",
            "",
            f"Task ID: {task['id']}",
            f"Title: {task['title']}",
            f"Kind: {task['kind']}",
            f"Summary: {task['summary']}",
            f"Acceptance criteria: {task['acceptance_criteria']}",
            "",
        ]
        if task.get("last_error"):
            sections.extend(
                [
                    "Previous failed attempt context:",
                    str(task["last_error"])[:4000],
                    "",
                ]
            )
        sections.extend(
            [
                "Allowed files:",
                *[f"- {path}" for path in profile.allowed_files],
                "",
                f"Required test command: {shlex.join(self._test_command(profile))}",
                "",
                "Suggested first steps:",
                "1. Read the allowed files using the exact relative paths listed below.",
                "2. Make the smallest correct code change.",
                "3. Update or add tests if the task needs them.",
                "4. Run the required test command.",
                "",
                "Relevant repository files to inspect first:",
            ]
        )
        sections.extend(f"- {relative_path}" for relative_path in profile.allowed_files)
        return "\n".join(sections) + "\n"

    def _prepare_run_root(self, task_id: str) -> Path:
        slug = f"{task_id.lower()}-{datetime.now(tz=timezone.utc).strftime('%Y%m%dT%H%M%S')}"
        run_root = self._config.coding_log_root / "runs" / slug
        run_root.mkdir(parents=True, exist_ok=True)
        return run_root

    def _build_env(
        self,
        *,
        chat_history_path: Path,
        input_history_path: Path,
        llm_history_path: Path,
    ) -> dict[str, str]:
        env = os.environ.copy()
        env.update(
            {
                "AIDER_MODEL": self._config.coding_model,
                "AIDER_REASONING_EFFORT": self._config.coding_reasoning_effort,
                "AIDER_THINKING_TOKENS": str(self._config.coding_extended_thinking_budget),
                "AIDER_TIMEOUT": str(self._config.coding_timeout_seconds),
                "AIDER_CACHE_PROMPTS": str(self._config.coding_cache_prompts).lower(),
                "AIDER_CHAT_HISTORY_FILE": str(chat_history_path),
                "AIDER_INPUT_HISTORY_FILE": str(input_history_path),
                "AIDER_LLM_HISTORY_FILE": str(llm_history_path),
                "AIDER_ANALYTICS": "false",
                "AIDER_CHECK_UPDATE": "false",
                "AIDER_PRETTY": "false",
                "AIDER_STREAM": "false",
                "AIDER_MAP_TOKENS": str(self._config.coding_map_tokens),
            }
        )
        if self._config.coding_base_url:
            env["AIDER_OPENAI_API_BASE"] = self._config.coding_base_url
        return env

    def _build_command(
        self,
        *,
        prompt_path: Path,
        chat_history_path: Path,
        input_history_path: Path,
        llm_history_path: Path,
        profile: TaskProfile,
    ) -> tuple[str, ...]:
        command = [
            self._config.coding_agent_bin,
            "--model",
            self._config.coding_model,
            "--edit-format",
            self._config.coding_edit_format,
            "--reasoning-effort",
            self._config.coding_reasoning_effort,
            "--timeout",
            str(self._config.coding_timeout_seconds),
            "--message-file",
            str(prompt_path),
            "--input-history-file",
            str(input_history_path),
            "--chat-history-file",
            str(chat_history_path),
            "--llm-history-file",
            str(llm_history_path),
            "--map-tokens",
            str(self._config.coding_map_tokens),
            "--no-auto-commits",
            "--no-dirty-commits",
            "--no-gitignore",
            "--no-add-gitignore-files",
            "--no-restore-chat-history",
            "--no-show-release-notes",
            "--yes-always",
            "--subtree-only",
            "--no-pretty",
            "--no-stream",
        ]
        if self._config.coding_extended_thinking_budget > 0:
            command.extend(
                ["--thinking-tokens", str(self._config.coding_extended_thinking_budget)]
            )
        if not self._config.coding_show_model_warnings:
            command.append("--no-show-model-warnings")
        if not self._config.coding_check_model_accepts_settings:
            command.append("--no-check-model-accepts-settings")
        command.extend(profile.allowed_files)
        return tuple(command)

    def _extract_summary(self, stdout_text: str) -> str:
        lines = [line.strip() for line in stdout_text.splitlines() if line.strip()]
        if not lines:
            return "aider applied code changes in the task worktree."
        return " ".join(lines[-3:])[:400]

    def _extract_event_excerpt(self, stdout_text: str, limit: int = 8) -> list[str]:
        lines = [line.strip() for line in stdout_text.splitlines() if line.strip()]
        return lines[-limit:]

    def _test_command(self, profile: TaskProfile) -> tuple[str, ...]:
        return ("python", *profile.test_args)


class TaskExecutor:
    def __init__(
        self,
        config: ExecutorConfig | None = None,
        model_client: AiderClient | None = None,
        kanboard_sync: KanboardSync | None = None,
    ) -> None:
        self._config = config or ExecutorConfig.from_env()
        self._model_client = model_client or AiderClient(self._config)
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

            run_result = self._model_client.run_task(task, profile, worktree_path)
            self._validate_allowed_file_changes(worktree_path, profile)
            add_event(
                task["id"],
                "agent",
                run_result.get("summary") or "aider applied code changes in the task worktree.",
            )
            for excerpt in run_result.get("event_excerpt", []):
                add_event(task["id"], "agent", excerpt)
            add_event(
                task["id"],
                "agent",
                (
                    "aider logs saved to "
                    f"{run_result.get('stdout_log_path')}, {run_result.get('stderr_log_path')}, "
                    f"and {run_result.get('llm_history_path')}."
                ),
            )

            self._update_task(
                task["id"],
                status="testing",
                event_type="testing",
                event_message=f"Running local tests: {shlex.join(self._test_command(profile))}",
            )
            self._run(self._test_command(profile), cwd=worktree_path)

            commit_message = f"Resolve {task['id']}: {task['title']}"
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
        normalize_worktree_gitdir(worktree_path, self._config.repo_root)
        return worktree_path, branch_name

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

    def _validate_allowed_file_changes(self, worktree_path: Path, profile: TaskProfile) -> None:
        changed_files_output = self._run(
            ("git", "diff", "--name-only", "--relative"),
            cwd=worktree_path,
        )
        changed_files = [line.strip() for line in changed_files_output.splitlines() if line.strip()]
        if not changed_files:
            raise TaskExecutionError("aider finished without producing any code changes.")
        disallowed = sorted(set(changed_files) - set(profile.allowed_files))
        if disallowed:
            raise TaskExecutionError(
                "aider modified files outside the task profile: " + ", ".join(disallowed)
            )

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
