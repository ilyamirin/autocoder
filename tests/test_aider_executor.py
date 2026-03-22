from pathlib import Path

from services.orchestrator.task_executor import AiderClient, ExecutorConfig, TaskProfile


def _config(tmp_path: Path) -> ExecutorConfig:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True)
    return ExecutorConfig(
        repo_root=repo_root,
        worktree_root=repo_root / "data" / "worktrees",
        base_branch="codex/runtime",
        bootstrap_branch="codex/development",
        live_worktree_path=repo_root / "data" / "live_runtime",
        coding_agent_bin="/usr/local/bin/aider",
        coding_model="openrouter/qwen/qwen3-coder-plus",
        coding_base_url=None,
        coding_timeout_seconds=900,
        coding_reasoning_effort="medium",
        coding_extended_thinking_budget=200000,
        coding_critic_max_iterations=5,
        coding_map_tokens=0,
        coding_edit_format="diff",
        coding_log_root=repo_root / "data" / "aider",
        coding_cache_prompts=True,
        coding_log_completions=True,
        coding_show_model_warnings=False,
        coding_check_model_accepts_settings=False,
        push_enabled=False,
        gitea_owner="ilya",
        gitea_repo="autonomous-coding-demo",
        gitea_push_base_url="http://gitea:3000",
        gitea_username="demo",
        gitea_password="demo",
        gitea_api_base_url="http://gitea:3000",
        gitea_http_base_url="http://localhost:13000",
        ci_poll_timeout_seconds=180,
        ci_poll_interval_seconds=5,
    )


def test_aider_prompt_includes_failure_context(tmp_path: Path) -> None:
    client = AiderClient(_config(tmp_path))
    profile = TaskProfile(
        allowed_files=("services/pet_app/domain.py", "tests/test_pet_app.py"),
        test_args=("-m", "pytest", "tests/test_pet_app.py"),
    )
    task = {
        "id": "BL-009",
        "title": "Обогатить тестовые данные",
        "kind": "quality",
        "summary": "Добавить больше returned и cancelled кейсов.",
        "acceptance_criteria": "Тесты зелёные.",
        "last_error": "AssertionError: expected 6 orders, got 8",
    }

    prompt = client._build_task_prompt(task, profile)

    assert "Previous failed attempt context:" in prompt
    assert "expected 6 orders, got 8" in prompt
    assert "Internal refinement budget: up to 5 passes." in prompt
    assert "Do not narrate shell commands" in prompt
    assert "Run the required local test command" not in prompt


def test_aider_command_uses_non_interactive_safe_flags(tmp_path: Path) -> None:
    client = AiderClient(_config(tmp_path))
    profile = TaskProfile(
        allowed_files=("services/pet_app/domain.py", "tests/test_pet_app.py"),
        test_args=("-m", "pytest", "tests/test_pet_app.py"),
    )
    run_root = tmp_path / "run"
    run_root.mkdir()

    command = client._build_command(
        prompt_path=run_root / "prompt.md",
        chat_history_path=run_root / "chat.history.md",
        input_history_path=run_root / "input.history",
        llm_history_path=run_root / "llm.history",
        profile=profile,
    )

    assert command[0] == "/usr/local/bin/aider"
    assert "--message-file" in command
    assert "--edit-format" in command
    assert "--no-auto-commits" in command
    assert "--no-dirty-commits" in command
    assert "--no-gitignore" in command
    assert "--no-add-gitignore-files" in command
    assert "--no-show-release-notes" in command
    assert "--yes-always" in command
    assert "--subtree-only" in command
    assert "--thinking-tokens" in command
    assert "--no-check-model-accepts-settings" in command
    assert command[-2:] == profile.allowed_files


def test_aider_run_root_is_created_under_generic_log_root(tmp_path: Path) -> None:
    client = AiderClient(_config(tmp_path))

    run_root = client._prepare_run_root("BL-001")

    assert run_root.exists()
    assert run_root.parent == tmp_path / "repo" / "data" / "aider" / "runs"
