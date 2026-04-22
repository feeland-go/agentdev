from __future__ import annotations

import json
from pathlib import Path
from typing import Any

QUEUE_DIR = Path("queue")


def queue_counts() -> dict[str, int]:
    counts: dict[str, int] = {}
    for state in ["pending", "active", "done", "failed", "dead"]:
        counts[state] = len(list((QUEUE_DIR / state).glob("*.json")))
    return counts


def queue_duplicates() -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()

    for state in ["pending", "active", "done", "failed", "dead"]:
        for task_file in (QUEUE_DIR / state).glob("*.json"):
            task_id = task_file.stem
            if task_id in seen:
                duplicates.add(task_id)
            else:
                seen.add(task_id)

    return sorted(duplicates)


def env_sanity(project_root: Path = Path(".")) -> dict[str, bool]:
    project_env = (project_root / ".env").exists()
    hermes_env = (Path.home() / ".hermes" / ".env").exists()
    return {
        "project_env_exists": project_env,
        "hermes_env_exists": hermes_env,
    }


def summary() -> dict[str, Any]:
    counts = queue_counts()
    duplicates = queue_duplicates()
    sanity = env_sanity()
    return {
        "queue": counts,
        "duplicates": duplicates,
        "env": sanity,
        "ok": not duplicates,
    }


if __name__ == "__main__":
    print(json.dumps(summary(), indent=2))
