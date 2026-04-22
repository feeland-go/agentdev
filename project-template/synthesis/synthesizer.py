from __future__ import annotations

from pathlib import Path
from typing import Any

from .llm_client import call_llm
from .utils import parse_frontmatter, parse_json_response


def synthesize_topic(topic: str, extracted_files: list[Path]) -> dict[str, Any]:
    docs: list[str] = []
    for file_path in extracted_files:
        content = file_path.read_text(encoding="utf-8")
        frontmatter, body = parse_frontmatter(content)
        docs.append(f"{frontmatter.get('title', file_path.stem)}\n{body}")

    prompt = f"TOPIC: {topic}\n\n" + "\n\n---\n\n".join(docs)
    result = parse_json_response(call_llm(prompt[:12000]))
    if not result:
        result = {
            "overview": "",
            "sections": [],
            "key_findings": [],
            "gaps": [],
        }
    return result
