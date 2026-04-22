from __future__ import annotations

from typing import Any


class JinaReaderConnector:
    def fetch(self, url: str) -> dict[str, Any]:
        return {
            "title": "Mock fetched content",
            "url": url,
            "content": "## Raw Content\n\nplaceholder content",
            "publishedTime": None,
            "usage": {"tokens": 0},
        }

    def normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        return {
            "title": raw.get("title"),
            "source_url": raw.get("url"),
            "source_type": "web",
            "date_published": raw.get("publishedTime"),
            "authors": None,
            "tags": [],
            "credibility_score": None,
            "content": raw.get("content", ""),
            "pdf_url": None,
            "arxiv_id": None,
        }
