from pathlib import Path
from typing import Any

DEFAULT_RESEARCH_MAP = "Belum ada peta riset. Ini putaran pertama."


def read_research_map(vault_root: Path = Path("vault")) -> str:
    research_map_path = vault_root / "memory" / "research.md"
    if not research_map_path.exists():
        return DEFAULT_RESEARCH_MAP
    return research_map_path.read_text(encoding="utf-8")


def _build_base_query(topic: str, question: str) -> str:
    return f"{topic} {question}".strip()


def _detect_gap_targets(research_map: str) -> list[str]:
    lines = [line.strip("- ").strip() for line in research_map.splitlines()]
    targets = [line for line in lines if line and "gap" in line.lower()]
    return targets[:10]


def generate_queries(config: dict[str, Any], vault_root: Path = Path("vault")) -> list[dict[str, str]]:
    project = config.get("project", {})
    topic = str(project.get("topic", "")).strip()
    questions = project.get("research_questions", [])
    if not isinstance(questions, list):
        questions = []

    research_map = read_research_map(vault_root=vault_root)
    gap_targets = _detect_gap_targets(research_map)

    queries: list[dict[str, str]] = []
    for question in questions:
        if not isinstance(question, str) or not question.strip():
            continue
        queries.append(
            {
                "query": _build_base_query(topic, question),
                "source": "both",
                "priority": "high",
                "targets_gap": "null",
            }
        )

    for gap in gap_targets:
        queries.append(
            {
                "query": f"{topic} {gap}".strip(),
                "source": "both",
                "priority": "high",
                "targets_gap": gap,
            }
        )

    return queries
