from __future__ import annotations

import fcntl
import os
import subprocess
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


class GitSafetyError(RuntimeError):
    pass


@dataclass(frozen=True)
class GitDirectories:
    local_git_dir: Path
    common_git_dir: Path


def resolve_git_directories(repo_root: Path) -> GitDirectories:
    local_git_dir = _resolve_git_dir(repo_root)
    commondir_file = local_git_dir / "commondir"
    if commondir_file.exists():
        common_git_dir = (local_git_dir / commondir_file.read_text().strip()).resolve()
    else:
        common_git_dir = local_git_dir
    return GitDirectories(local_git_dir=local_git_dir, common_git_dir=common_git_dir)


def run_git_command(
    command: tuple[str, ...],
    *,
    cwd: Path,
    check: bool = True,
    timeout: int = 180,
    wait_timeout_seconds: float = 15.0,
) -> subprocess.CompletedProcess[str]:
    directories = resolve_git_directories(cwd.resolve())
    with cooperative_git_lock(directories.common_git_dir, timeout_seconds=wait_timeout_seconds):
        wait_for_git_locks_to_clear(
            directories,
            timeout_seconds=wait_timeout_seconds,
            poll_interval_seconds=0.2,
        )
        return subprocess.run(
            command,
            cwd=cwd,
            check=check,
            capture_output=True,
            text=True,
            timeout=timeout,
        )


def wait_for_git_locks_to_clear(
    directories: GitDirectories,
    *,
    timeout_seconds: float,
    poll_interval_seconds: float,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    while True:
        locks = list_git_lock_paths(directories)
        if not locks:
            return
        if time.monotonic() >= deadline:
            details = ", ".join(f"{path.name} age={lock_age_seconds(path):.1f}s" for path in locks)
            raise GitSafetyError(f"Git lock files did not clear in time: {details}")
        time.sleep(poll_interval_seconds)


def list_git_lock_paths(directories: GitDirectories) -> list[Path]:
    lock_paths: set[Path] = set()
    for git_dir in {directories.local_git_dir, directories.common_git_dir}:
        for relative_path in (
            "index.lock",
            "HEAD.lock",
            "FETCH_HEAD.lock",
            "packed-refs.lock",
            "config.lock",
            "shallow.lock",
        ):
            candidate = git_dir / relative_path
            if candidate.exists():
                lock_paths.add(candidate.resolve())

        refs_dir = git_dir / "refs"
        if refs_dir.exists():
            lock_paths.update(path.resolve() for path in refs_dir.rglob("*.lock"))

    return sorted(lock_paths)


def lock_age_seconds(lock_path: Path) -> float:
    return max(0.0, time.time() - lock_path.stat().st_mtime)


@contextmanager
def cooperative_git_lock(common_git_dir: Path, *, timeout_seconds: float) -> Iterator[None]:
    lock_path = common_git_dir / "codex_git_guard.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+") as lock_file:
        deadline = time.monotonic() + timeout_seconds
        while True:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                lock_file.seek(0)
                lock_file.truncate()
                lock_file.write(f"pid={os.getpid()}\n")
                lock_file.flush()
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise GitSafetyError(
                        f"Timed out waiting for cooperative git lock: {lock_path.name}"
                    )
                time.sleep(0.2)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _resolve_git_dir(repo_root: Path) -> Path:
    dot_git = repo_root / ".git"
    if dot_git.is_dir():
        return dot_git.resolve()
    if dot_git.is_file():
        content = dot_git.read_text().strip()
        prefix = "gitdir:"
        if not content.startswith(prefix):
            raise GitSafetyError(f"Unsupported .git file format in {repo_root}")
        git_dir = content[len(prefix) :].strip()
        return (repo_root / git_dir).resolve()
    raise GitSafetyError(f"No .git directory found for {repo_root}")
