#!/usr/bin/env python3
from __future__ import annotations

from services.common.live_runtime import LiveRuntimeConfig, ensure_live_worktree


def main() -> None:
    config = LiveRuntimeConfig.from_env()
    path = ensure_live_worktree(config)
    print(f"Live runtime ready at {path}")


if __name__ == "__main__":
    main()
