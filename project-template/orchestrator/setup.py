import argparse
import json
from pathlib import Path
from typing import Any


def _to_yaml(value: Any, indent: int = 0) -> str:
    pad = "  " * indent
    if isinstance(value, dict):
        lines: list[str] = []
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                lines.append(f"{pad}{key}:")
                lines.append(_to_yaml(item, indent + 1))
            else:
                lines.append(f"{pad}{key}: {_yaml_scalar(item)}")
        return "\n".join(lines)

    if isinstance(value, list):
        lines = []
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(f"{pad}-")
                lines.append(_to_yaml(item, indent + 1))
            else:
                lines.append(f"{pad}- {_yaml_scalar(item)}")
        return "\n".join(lines)

    return f"{pad}{_yaml_scalar(value)}"


def _yaml_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)

    text = str(value)
    if text == "" or any(c in text for c in [":", "#", "[", "]", "{", "}", "\n"]):
        escaped = text.replace('"', '\\"')
        return f'"{escaped}"'
    return text


# setup.py intentionally avoids external dependencies for bootstrap reliability.




def _require_non_empty_str(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"'{key}' must be a non-empty string")
    return value.strip()


def _require_questions(data: dict[str, Any]) -> list[str]:
    questions = data.get("research_questions")
    if not isinstance(questions, list) or not questions:
        raise ValueError("'research_questions' must be a non-empty list")

    cleaned: list[str] = []
    for i, question in enumerate(questions, start=1):
        if not isinstance(question, str) or not question.strip():
            raise ValueError(f"'research_questions[{i}]' must be a non-empty string")
        cleaned.append(question.strip())
    return cleaned


def _optional_string_list(data: dict[str, Any], key: str) -> list[str]:
    value = data.get(key)
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"'{key}' must be a list when provided")

    cleaned: list[str] = []
    for i, item in enumerate(value, start=1):
        if not isinstance(item, str):
            raise ValueError(f"'{key}[{i}]' must be a string")
        item = item.strip()
        if item:
            cleaned.append(item)
    return cleaned


def _optional_date_range(data: dict[str, Any]) -> str | None:
    date_range = data.get("date_range")
    if date_range is None or date_range == "":
        return None
    if not isinstance(date_range, str):
        raise ValueError("'date_range' must be a string or null")
    return date_range.strip() or None


def build_research_config(answers: dict[str, Any]) -> dict[str, Any]:
    topic = _require_non_empty_str(answers, "topic")
    questions = _require_questions(answers)
    sub_topics = _optional_string_list(answers, "sub_topics")
    categories = _optional_string_list(answers, "arxiv_categories")
    date_range = _optional_date_range(answers)

    return {
        "project": {
            "topic": topic,
            "research_questions": questions,
            "sub_topics": sub_topics,
            "date_range": date_range,
            "arxiv_categories": categories,
        },
        "queue": {
            "min_relevance": 0.6,
            "max_sources": 500,
            "parallel_workers": 5,
            "task_timeout": 180,
            "max_retry": 2,
        },
        "memory": {
            "update_mode": "extract_stage_batch",
        },
    }


def write_research_config(answers: dict[str, Any], output_path: Path = Path("research_config.yaml")) -> None:
    config = build_research_config(answers)
    yaml_text = _to_yaml(config) + "\n"
    output_path.write_text(yaml_text, encoding="utf-8")
    print(f"✅ research_config.yaml written to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Write validated research_config.yaml")
    parser.add_argument("--write-config", type=str, help="JSON string from Hermes setup answers")
    parser.add_argument("--output", type=str, default="research_config.yaml", help="Output config path")
    args = parser.parse_args()

    if not args.write_config:
        raise SystemExit("Usage: python setup.py --write-config '<json>' [--output path]")

    try:
        answers = json.loads(args.write_config)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON payload for --write-config: {exc}") from exc

    if not isinstance(answers, dict):
        raise SystemExit("Invalid payload: root JSON must be an object")

    try:
        write_research_config(answers, output_path=Path(args.output))
    except ValueError as exc:
        raise SystemExit(f"Invalid setup payload: {exc}") from exc


if __name__ == "__main__":
    main()
