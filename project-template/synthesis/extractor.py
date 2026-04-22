from __future__ import annotations

from pathlib import Path
from typing import Any

from .citation import format_citation, format_inline_citation
from .llm_client import call_llm
from .utils import extract_raw_content, parse_frontmatter, parse_json_response


def extract_document(source_file: Path) -> dict[str, Any]:
    content = source_file.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(content)
    raw_content = extract_raw_content(body)

    result = parse_json_response(call_llm(raw_content[:6000]))
    if not result:
        result = {
            "summary": "",
            "key_points": [],
            "key_entities": [],
            "contradictions": [],
            "gaps": [],
        }

    result["inline_citation"] = format_inline_citation(frontmatter)
    result["citation"] = format_citation(frontmatter)
    return result
