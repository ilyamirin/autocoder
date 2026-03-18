from __future__ import annotations

import subprocess
from pathlib import Path

from services.common.live_runtime import LiveRuntimeConfig, ensure_live_worktree, promote_commit_to_live


def test_live_runtime_worktree_is_created_and_accepts_promoted_commit(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    _git(("git", "init", "-b", "main"), cwd=repo_root)

    file_path = repo_root / "demo.txt"
    file_path.write_text("base\n")
    _git(("git", "add", "demo.txt"), cwd=repo_root)
    _git(
        (
            "git",
            "-c",
            "user.name=Test User",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-m",
            "base",
        ),
        cwd=repo_root,
    )
    _git(("git", "branch", "codex/development"), cwd=repo_root)

    config = LiveRuntimeConfig(
        repo_root=repo_root,
        bootstrap_branch="codex/development",
        runtime_branch="codex/runtime",
        live_worktree_path=repo_root / "data" / "live_runtime",
    )

    live_path = ensure_live_worktree(config)
    assert live_path.exists()
    assert (live_path / "demo.txt").read_text() == "base\n"
    assert _git(("git", "config", "--get", "user.name"), cwd=live_path).strip() == "Autonomous Coding Agent"
    assert _git(("git", "config", "--get", "user.email"), cwd=live_path).strip() == "agent@local.demo"

    _git(("git", "checkout", "-b", "codex/test-task", "codex/runtime"), cwd=repo_root)
    file_path.write_text("updated\n")
    _git(("git", "add", "demo.txt"), cwd=repo_root)
    _git(
        (
            "git",
            "-c",
            "user.name=Test User",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-m",
            "update",
        ),
        cwd=repo_root,
    )
    commit_sha = _git(("git", "rev-parse", "HEAD"), cwd=repo_root).strip()
    _git(("git", "checkout", "main"), cwd=repo_root)

    # Simulate a previously interrupted promotion that left the live checkout dirty.
    (live_path / "demo.txt").write_text("dirty\n")
    assert _git(("git", "status", "--short"), cwd=live_path).strip()

    deployed_sha = promote_commit_to_live(config, commit_sha)

    assert deployed_sha
    assert (live_path / "demo.txt").read_text() == "updated\n"
    assert _git(("git", "status", "--short"), cwd=live_path).strip() == ""


def _git(command: tuple[str, ...], *, cwd: Path) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout
