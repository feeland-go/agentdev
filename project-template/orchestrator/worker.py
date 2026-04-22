import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

QUEUE_DIR = Path("queue")
DEFAULT_PARALLEL_WORKERS = 5
DEFAULT_MAX_RETRY = 2


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_task(task_file: Path) -> dict[str, Any]:
    return json.loads(task_file.read_text(encoding="utf-8"))


def _save_task(task_file: Path, task: dict[str, Any]) -> None:
    task_file.write_text(json.dumps(task, indent=2), encoding="utf-8")


def move_task(task_file: Path, destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / task_file.name
    if target.exists():
        raise RuntimeError(f"Target already exists: {target}")
    task_file.rename(target)
    return target


def get_next_pending() -> Path | None:
    pending = sorted((QUEUE_DIR / "pending").glob("*.json"))
    return pending[0] if pending else None


def _build_next_doc_task(task: dict[str, Any], stage: str) -> dict[str, Any]:
    index = task["task_id"].split("_")[-1]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    task_id = f"{stage}_doc_{timestamp}_{index}"
    return {
        "task_id": task_id,
        "stage": stage,
        "granularity": "document",
        "topic": task.get("topic"),
        "source_type": task.get("source_type"),
        "url": task.get("url"),
        "title": task.get("title"),
        "relevance_score": task.get("relevance_score", 0.0),
        "retry_count": 0,
        "max_retry": task.get("max_retry", DEFAULT_MAX_RETRY),
        "created_at": _now_iso(),
        "started_at": None,
        "finished_at": None,
        "error": None,
    }


def enqueue_next_doc_stage(task: dict[str, Any], stage: str) -> Path:
    next_task = _build_next_doc_task(task, stage)
    next_path = QUEUE_DIR / "pending" / f"{next_task['task_id']}.json"
    next_path.parent.mkdir(parents=True, exist_ok=True)
    next_path.write_text(json.dumps(next_task, indent=2), encoding="utf-8")
    return next_path


def maybe_enqueue_topic_synthesis(task: dict[str, Any]) -> Path | None:
    topic = task.get("topic")
    if not topic:
        return None

    slug = str(topic).strip().lower().replace(" ", "-")
    existing = list((QUEUE_DIR / "pending").glob(f"synthesize_topic_*_{slug}.json"))
    existing += list((QUEUE_DIR / "active").glob(f"synthesize_topic_*_{slug}.json"))
    if existing:
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    task_id = f"synthesize_topic_{timestamp}_{slug}"
    synth_task = {
        "task_id": task_id,
        "stage": "synthesize",
        "granularity": "topic",
        "topic": topic,
        "source_type": task.get("source_type"),
        "url": None,
        "title": f"Topic synthesis: {topic}",
        "relevance_score": task.get("relevance_score", 0.0),
        "retry_count": 0,
        "max_retry": task.get("max_retry", DEFAULT_MAX_RETRY),
        "created_at": _now_iso(),
        "started_at": None,
        "finished_at": None,
        "error": None,
    }

    path = QUEUE_DIR / "pending" / f"{task_id}.json"
    path.write_text(json.dumps(synth_task, indent=2), encoding="utf-8")
    return path


def run_fetch(task: dict[str, Any]) -> None:
    _ = task


def run_extract(task: dict[str, Any]) -> None:
    _ = task


def run_synthesize(task: dict[str, Any]) -> None:
    _ = task


def notify_task_done(task: dict[str, Any]) -> None:
    _ = task


def notify_task_dead(task: dict[str, Any]) -> None:
    _ = task


def check_trigger_final_report() -> None:
    return


def handle_task_failure(task_file: Path, task: dict[str, Any], error: Exception) -> None:
    task["error"] = str(error)
    task["retry_count"] = int(task.get("retry_count", 0)) + 1
    _save_task(task_file, task)

    if task["retry_count"] >= int(task.get("max_retry", DEFAULT_MAX_RETRY)):
        dead_file = move_task(task_file, QUEUE_DIR / "dead")
        notify_task_dead(_load_task(dead_file))
    else:
        move_task(task_file, QUEUE_DIR / "failed")


def worker(task_file: Path) -> None:
    task = _load_task(task_file)
    task["started_at"] = _now_iso()
    _save_task(task_file, task)

    try:
        stage = task.get("stage")
        granularity = task.get("granularity", "document")

        if stage == "fetch" and granularity == "document":
            run_fetch(task)
            enqueue_next_doc_stage(task, "extract")
        elif stage == "extract" and granularity == "document":
            run_extract(task)
            maybe_enqueue_topic_synthesis(task)
        elif stage == "synthesize" and granularity == "topic":
            run_synthesize(task)
            check_trigger_final_report()
        else:
            raise RuntimeError(f"Unsupported stage/granularity: {stage}/{granularity}")

        task["finished_at"] = _now_iso()
        task["error"] = None
        _save_task(task_file, task)
        done_file = move_task(task_file, QUEUE_DIR / "done")
        notify_task_done(_load_task(done_file))
    except Exception as exc:
        handle_task_failure(task_file, task, exc)


def _retry_failed_if_needed(active_threads: list[threading.Thread]) -> bool:
    pending_exists = any((QUEUE_DIR / "pending").glob("*.json"))
    if active_threads or pending_exists:
        return False

    failed_tasks = list((QUEUE_DIR / "failed").glob("*.json"))
    for task_file in failed_tasks:
        move_task(task_file, QUEUE_DIR / "pending")
    return bool(failed_tasks)


def sliding_window_runner(parallel_workers: int = DEFAULT_PARALLEL_WORKERS) -> None:
    active_threads: list[threading.Thread] = []

    while True:
        active_threads = [thread for thread in active_threads if thread.is_alive()]

        while len(active_threads) < parallel_workers:
            next_task = get_next_pending()
            if not next_task:
                break

            active_path = move_task(next_task, QUEUE_DIR / "active")
            thread = threading.Thread(target=worker, args=(active_path,), daemon=True)
            thread.start()
            active_threads.append(thread)

        if _retry_failed_if_needed(active_threads):
            continue

        if not active_threads and not any((QUEUE_DIR / "pending").glob("*.json")):
            break

        time.sleep(2)


if __name__ == "__main__":
    sliding_window_runner()
