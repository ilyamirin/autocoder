from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from services.common.git_safety import GitSafetyError, normalize_worktree_gitdir, run_git_command


@dataclass(frozen=True)
class LiveRuntimeConfig:
    repo_root: Path
    bootstrap_branch: str
    runtime_branch: str
    live_worktree_path: Path
    git_user_name: str = "Autonomous Coding Agent"
    git_user_email: str = "agent@local.demo"

    @classmethod
    def from_env(cls, repo_root: Path | None = None) -> "LiveRuntimeConfig":
        resolved_repo_root = (repo_root or Path(os.getenv("DEMO_REPO_ROOT", Path.cwd()))).resolve()
        return cls(
            repo_root=resolved_repo_root,
            bootstrap_branch=os.getenv("EXECUTOR_BOOTSTRAP_BRANCH", "codex/development"),
            runtime_branch=os.getenv("EXECUTOR_RUNTIME_BRANCH", "codex/runtime"),
            live_worktree_path=Path(
                os.getenv("LIVE_WORKTREE_PATH", resolved_repo_root / "data" / "live_runtime")
            ).resolve(),
        )


def ensure_live_worktree(config: LiveRuntimeConfig) -> Path:
    config.live_worktree_path.parent.mkdir(parents=True, exist_ok=True)
    _ensure_runtime_branch_exists(config)

    if (config.live_worktree_path / ".git").exists():
        _ensure_live_git_identity(config, config.live_worktree_path)
        _prepare_clean_live_worktree(config.live_worktree_path)
        return config.live_worktree_path

    if config.live_worktree_path.exists():
        shutil.rmtree(config.live_worktree_path)

    _git(
        ("git", "worktree", "add", "--force", str(config.live_worktree_path), config.runtime_branch),
        cwd=config.repo_root,
    )
    normalize_worktree_gitdir(config.live_worktree_path, config.repo_root)
    _ensure_live_git_identity(config, config.live_worktree_path)
    _prepare_clean_live_worktree(config.live_worktree_path)
    return config.live_worktree_path


def promote_commit_to_live(config: LiveRuntimeConfig, commit_sha: str) -> str:
    live_path = ensure_live_worktree(config)
    try:
        _git(("git", "cherry-pick", commit_sha), cwd=live_path)
    except GitSafetyError:
        _git(("git", "cherry-pick", "--abort"), cwd=live_path, check=False)
        raise
    deployed_sha = _git(("git", "rev-parse", "HEAD"), cwd=live_path)
    return deployed_sha.strip()


def _ensure_runtime_branch_exists(config: LiveRuntimeConfig) -> None:
    existing = _git(
        ("git", "branch", "--list", config.runtime_branch),
        cwd=config.repo_root,
    ).strip()
    if existing:
        return
    _git(
        ("git", "branch", config.runtime_branch, config.bootstrap_branch),
        cwd=config.repo_root,
    )


def _ensure_live_git_identity(config: LiveRuntimeConfig, live_path: Path) -> None:
    current_name = _git(("git", "config", "--get", "user.name"), cwd=live_path, check=False).strip()
    current_email = _git(("git", "config", "--get", "user.email"), cwd=live_path, check=False).strip()
    if current_name != config.git_user_name:
        _git(("git", "config", "user.name", config.git_user_name), cwd=live_path)
    if current_email != config.git_user_email:
        _git(("git", "config", "user.email", config.git_user_email), cwd=live_path)


def _prepare_clean_live_worktree(live_path: Path) -> None:
    cherry_pick_head = _git(
        ("git", "rev-parse", "--verify", "-q", "CHERRY_PICK_HEAD"),
        cwd=live_path,
        check=False,
    ).strip()
    if cherry_pick_head:
        _git(("git", "cherry-pick", "--abort"), cwd=live_path, check=False)
    # The live runtime is a managed deployment checkout, so it must never keep
    # dirty files from a partially applied task. Resetting to HEAD makes the
    # next promotion deterministic.
    _git(("git", "reset", "--hard", "HEAD"), cwd=live_path, check=False)
    _git(("git", "clean", "-fd"), cwd=live_path, check=False)


def _git(command: tuple[str, ...], *, cwd: Path, check: bool = True) -> str:
    completed = run_git_command(command, cwd=cwd, check=False)
    if check and completed.returncode != 0:
        raise GitSafetyError(
            f"Command failed: {' '.join(command)}\nSTDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
        )
    return completed.stdout
