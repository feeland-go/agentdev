import json
from pathlib import Path
from typing import Any

QUEUE_DIR = Path("queue")
DEFAULT_MIN_RELEVANCE = 0.6


def load_existing_urls() -> set[str]:
    urls: set[str] = set()
    for state in ["pending", "active", "done", "failed", "dead"]:
        for task_file in (QUEUE_DIR / state).glob("*.json"):
            try:
                task = json.loads(task_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            url = task.get("url")
            if isinstance(url, str) and url:
                urls.add(url)
    return urls


def score_candidate(candidate: dict[str, Any]) -> float:
    score = candidate.get("relevance_score")
    if isinstance(score, (int, float)):
        return float(score)
    return 0.0


def filter_candidates(candidates: list[dict[str, Any]], min_relevance: float = DEFAULT_MIN_RELEVANCE) -> list[dict[str, Any]]:
    existing_urls = load_existing_urls()
    approved: list[dict[str, Any]] = []

    for candidate in candidates:
        url = candidate.get("url")
        if not isinstance(url, str) or not url:
            continue
        if url in existing_urls:
            continue

        score = score_candidate(candidate)
        if score < min_relevance:
            continue

        candidate["relevance_score"] = score
        approved.append(candidate)
    return approved


def enqueue_candidates(candidates: list[dict[str, Any]]) -> int:
    pending_dir = QUEUE_DIR / "pending"
    pending_dir.mkdir(parents=True, exist_ok=True)

    created = 0
    for index, candidate in enumerate(candidates, start=1):
        task_id = f"fetch_doc_{index:06d}"
        task = {
            "task_id": task_id,
            "stage": "fetch",
            "granularity": "document",
            "topic": candidate.get("topic"),
            "source_type": candidate.get("source_type", "web"),
            "url": candidate.get("url"),
            "title": candidate.get("title", "Untitled"),
            "relevance_score": candidate.get("relevance_score", 0.0),
            "retry_count": 0,
            "max_retry": 2,
            "created_at": candidate.get("created_at"),
            "started_at": None,
            "finished_at": None,
            "error": None,
        }
        (pending_dir / f"{task_id}.json").write_text(json.dumps(task, indent=2), encoding="utf-8")
        created += 1
    return created
