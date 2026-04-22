from __future__ import annotations

import json
import re
from typing import Any


def parse_frontmatter(content: str) -> tuple[dict[str, str], str]:
    if not content.startswith("---"):
        return {}, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    frontmatter: dict[str, str] = {}
    for line in parts[1].strip().splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        frontmatter[key.strip()] = value.strip()

    return frontmatter, parts[2].strip()


def extract_raw_content(body: str) -> str:
    match = re.search(r"## Raw Content\n(.*?)(?=\n## |\Z)", body, re.DOTALL)
    if not match:
        return body.strip()
    return match.group(1).strip()


def parse_json_response(raw: str) -> dict[str, Any]:
    cleaned = re.sub(r"```(?:json)?\n?", "", raw).replace("```", "").strip()
    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        return {}
    return result if isinstance(result, dict) else {}
