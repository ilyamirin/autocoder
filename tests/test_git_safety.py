from pathlib import Path

import pytest

from services.common.git_safety import GitSafetyError, GitDirectories, resolve_git_directories, wait_for_git_locks_to_clear


def test_resolve_git_directories_uses_commondir_for_worktree_like_layout(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    local_git_dir = tmp_path / "worktree-admin"
    local_git_dir.mkdir()
    common_git_dir = tmp_path / "common-git"
    common_git_dir.mkdir()

    (repo_root / ".git").write_text(f"gitdir: {local_git_dir}\n")
    (local_git_dir / "commondir").write_text("../common-git\n")

    directories = resolve_git_directories(repo_root)

    assert directories.local_git_dir == local_git_dir.resolve()
    assert directories.common_git_dir == common_git_dir.resolve()


def test_wait_for_git_locks_to_clear_times_out_on_index_lock(tmp_path: Path) -> None:
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "index.lock").write_text("busy\n")

    directories = GitDirectories(local_git_dir=git_dir, common_git_dir=git_dir)

    with pytest.raises(GitSafetyError, match="index.lock"):
        wait_for_git_locks_to_clear(
            directories,
            timeout_seconds=0.05,
            poll_interval_seconds=0.01,
        )
