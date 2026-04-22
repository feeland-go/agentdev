import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

QUEUE_DIR = Path("queue")
TASK_TIMEOUT_SECONDS = 180
GRACE_SECONDS = 30


def _load_task(task_file: Path) -> dict[str, Any]:
    return json.loads(task_file.read_text(encoding="utf-8"))


def _save_task(task_file: Path, task: dict[str, Any]) -> None:
    task_file.write_text(json.dumps(task, indent=2), encoding="utf-8")


def _move_to_pending(task_file: Path) -> None:
    pending_dir = QUEUE_DIR / "pending"
    pending_dir.mkdir(parents=True, exist_ok=True)
    target = pending_dir / task_file.name
    if target.exists():
        target.unlink()
    task_file.rename(target)


def _elapsed_seconds(started_at: str) -> int:
    started = datetime.fromisoformat(started_at)
    now = datetime.now(timezone.utc)
    return int((now - started).total_seconds())


def watchdog() -> list[str]:
    recovered: list[str] = []
    for task_file in sorted((QUEUE_DIR / "active").glob("*.json")):
        task = _load_task(task_file)
        started_at = task.get("started_at")
        if not isinstance(started_at, str) or not started_at:
            continue

        elapsed = _elapsed_seconds(started_at)
        if elapsed <= TASK_TIMEOUT_SECONDS + GRACE_SECONDS:
            continue

        task["started_at"] = None
        task["error"] = f"watchdog_requeue_after_{elapsed}s"
        _save_task(task_file, task)
        _move_to_pending(task_file)
        recovered.append(task.get("task_id", task_file.stem))

    return recovered


if __name__ == "__main__":
    recovered = watchdog()
    if recovered:
        print(f"[WATCHDOG] Requeued: {', '.join(recovered)}")
    else:
        print("[WATCHDOG] No stuck tasks found")
