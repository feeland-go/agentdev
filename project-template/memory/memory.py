from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MEMORY_DIR = Path("vault/memory")
WORKING_MD = MEMORY_DIR / "working.md"
RESEARCH_MD = MEMORY_DIR / "research.md"
META_MD = MEMORY_DIR / "meta.md"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _now_time() -> str:
    return datetime.now().strftime("%H:%M")


def init_memory(project_topic: str) -> None:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    if not WORKING_MD.exists():
        WORKING_MD.write_text(
            f"# Working Memory\n**Project:** {project_topic}\n\n",
            encoding="utf-8",
        )

    if not RESEARCH_MD.exists():
        RESEARCH_MD.write_text(
            "# Research Map\n"
            f"**Project:** {project_topic}\n"
            f"**Last updated:** {_now()}\n\n"
            "## Topik yang Sudah Ada di Vault\n\n"
            "## Gap Terbuka\n\n"
            "## Pertanyaan yang Sudah Terjawab\n",
            encoding="utf-8",
        )

    if not META_MD.exists():
        META_MD.write_text(
            f"# Meta Memory\n**Project:** {project_topic}\n\n",
            encoding="utf-8",
        )


def _calculate_duration(task: dict[str, Any]) -> int:
    started_at = task.get("started_at")
    finished_at = task.get("finished_at")
    if not started_at or not finished_at:
        return 0

    try:
        started = datetime.fromisoformat(str(started_at))
        finished = datetime.fromisoformat(str(finished_at))
    except ValueError:
        return 0

    return max(0, int((finished - started).total_seconds()))


def append_working_memory(task: dict[str, Any], status: str) -> None:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    if not WORKING_MD.exists():
        WORKING_MD.write_text("# Working Memory\n\n", encoding="utf-8")

    duration = _calculate_duration(task)
    icon = "✓" if status == "done" else "✗"
    error_line = f"\n- Error: {task.get('error', '')}" if status != "done" else ""

    entry = (
        f"\n### [{_now_time()}] {str(task.get('stage', 'unknown')).upper()} {icon}\n"
        f"- Title: \"{str(task.get('title', ''))[:80]}\"\n"
        f"- Source: {task.get('source_type', 'n/a')} | "
        f"Credibility: {task.get('relevance_score', 'n/a')}\n"
        f"- URL: {task.get('url', '')}"
        f"{error_line}\n"
        f"- Durasi: {duration}s\n"
    )

    today_header = f"\n## Session: {datetime.now().strftime('%Y-%m-%d')}\n"
    content = WORKING_MD.read_text(encoding="utf-8")

    with WORKING_MD.open("a", encoding="utf-8") as handle:
        if today_header.strip() not in content:
            handle.write(today_header)
        handle.write(entry)


def append_stage_summary(stage: str, stats: dict[str, Any]) -> None:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    if not WORKING_MD.exists():
        WORKING_MD.write_text("# Working Memory\n\n", encoding="utf-8")

    entry = (
        f"\n### [STAGE SELESAI: {stage.upper()}]\n"
        f"- Berhasil: {stats.get('done', 0)} | "
        f"Gagal: {stats.get('failed', 0)} | "
        f"Dead: {stats.get('dead', 0)}\n"
        f"- Durasi total: {stats.get('duration', 'n/a')}\n"
    )

    with WORKING_MD.open("a", encoding="utf-8") as handle:
        handle.write(entry)


def _extract_section(content: str, heading: str) -> list[str]:
    lines = content.splitlines()
    collected: list[str] = []
    inside = False

    for line in lines:
        if line.strip() == heading.strip():
            inside = True
            continue
        if inside and line.startswith("## "):
            break
        if inside:
            collected.append(line)

    return [line for line in collected if line.strip()]


def update_research_map_from_stage(
    stage: str,
    topics: list[dict[str, Any]],
    open_gaps: list[str],
    answered_questions: list[str],
    partially_answered: list[str],
) -> None:
    if stage.lower() != "extract":
        return

    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    topic_lines = ["## Topik yang Sudah Ada di Vault", ""]
    for topic in topics:
        name = topic.get("name", "unknown")
        synthesis_path = topic.get("synthesis_path", "null")
        source_count = topic.get("source_count", 0)
        coverage = topic.get("coverage", "unknown")
        gaps = topic.get("gaps", [])

        topic_lines.append(f"### {name}")
        topic_lines.append(f"- Synthesis: {synthesis_path}")
        topic_lines.append(f"- Jumlah sumber: {source_count}")
        topic_lines.append(f"- Coverage: {coverage}")
        if gaps:
            for gap in gaps:
                topic_lines.append(f"- Gap: {gap}")
        else:
            topic_lines.append("- Gap: None")
        topic_lines.append("")

    gap_lines = ["## Gap Terbuka", ""]
    for gap in open_gaps:
        gap_lines.append(f"- [ ] {gap}")
    if not open_gaps:
        gap_lines.append("- (none)")

    answered_lines = ["## Pertanyaan yang Sudah Terjawab", ""]
    for item in answered_questions:
        answered_lines.append(f"- {item}")
    if partially_answered:
        answered_lines.append("")
        answered_lines.append("## Pertanyaan yang Sebagian Terjawab")
        answered_lines.append("")
        for item in partially_answered:
            answered_lines.append(f"- {item}")

    content = "\n".join(
        [
            "# Research Map",
            f"**Last updated:** {_now()}",
            "",
            *topic_lines,
            "",
            *gap_lines,
            "",
            *answered_lines,
            "",
        ]
    )

    RESEARCH_MD.write_text(content, encoding="utf-8")


def write_meta_memory(
    project_topic: str,
    yang_berjalan_baik: list[str],
    error_patterns: list[str],
    preferensi_terdeteksi: list[str],
    saran_project_berikutnya: list[str],
) -> None:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    def _bullet(lines: list[str]) -> str:
        if not lines:
            return "- (none)"
        return "\n".join(f"- {line}" for line in lines)

    content = (
        "# Meta Memory\n"
        f"**Project:** {project_topic}\n"
        f"**Selesai:** {_now()}\n\n"
        "## Yang Berjalan Baik\n"
        f"{_bullet(yang_berjalan_baik)}\n\n"
        "## Error Patterns\n"
        f"{_bullet(error_patterns)}\n\n"
        "## Preferensi yang Terdeteksi\n"
        f"{_bullet(preferensi_terdeteksi)}\n\n"
        "## Saran untuk Project Berikutnya\n"
        f"{_bullet(saran_project_berikutnya)}\n"
    )

    META_MD.write_text(content, encoding="utf-8")


def summarize_memory() -> dict[str, Any]:
    working = WORKING_MD.read_text(encoding="utf-8") if WORKING_MD.exists() else ""
    research = RESEARCH_MD.read_text(encoding="utf-8") if RESEARCH_MD.exists() else ""
    meta = META_MD.read_text(encoding="utf-8") if META_MD.exists() else ""

    return {
        "working_entries": len([line for line in working.splitlines() if line.startswith("### [")]),
        "open_gaps": [line.strip("- [ ] ") for line in _extract_section(research, "## Gap Terbuka")],
        "has_meta": bool(meta.strip()),
    }


if __name__ == "__main__":
    payload = {
        "status": "memory module ready",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    print(json.dumps(payload, indent=2))
