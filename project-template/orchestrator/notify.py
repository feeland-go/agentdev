from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

QUEUE_DIR = Path("queue")


def _count(state: str) -> int:
    return len(list((QUEUE_DIR / state).glob("*.json")))


def queue_summary() -> dict[str, Any]:
    pending = _count("pending")
    active = _count("active")
    done = _count("done")
    failed = _count("failed")
    dead = _count("dead")
    total = pending + active + done + failed + dead

    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "pending": pending,
        "active": active,
        "done": done,
        "failed": failed,
        "dead": dead,
        "total": total,
    }


def format_summary(summary: dict[str, Any]) -> str:
    return (
        f"📊 Research Progress Update\\n"
        f"🕐 {summary['timestamp']}\\n\\n"
        f"Pending: {summary['pending']}\\n"
        f"Active : {summary['active']}\\n"
        f"Done   : {summary['done']}\\n"
        f"Failed : {summary['failed']}\\n"
        f"Dead   : {summary['dead']}\\n"
        f"Total  : {summary['total']}"
    )


def summary_json() -> str:
    return json.dumps(queue_summary(), indent=2)


if __name__ == "__main__":
    print(format_summary(queue_summary()))
