from __future__ import annotations

from typing import Any


class ArxivConnector:
    def search(self, query: str, max_results: int = 10) -> list[dict[str, Any]]:
        if not query.strip():
            return []
        return [
            {
                "title": f"Mock arXiv result for: {query}",
                "source_url": "https://arxiv.org/abs/0000.00000",
                "pdf_url": "https://arxiv.org/pdf/0000.00000.pdf",
                "content": "mock abstract",
                "authors": ["Unknown"],
                "date_published": "1970-01-01",
                "tags": ["cs.AI"],
                "source_type": "arxiv",
            }
        ][:max_results]

    def normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        return {
            "title": raw.get("title"),
            "source_url": raw.get("source_url"),
            "source_type": "arxiv",
            "date_published": raw.get("date_published"),
            "authors": raw.get("authors", []),
            "tags": raw.get("tags", []),
            "credibility_score": raw.get("credibility_score"),
            "content": raw.get("content", ""),
            "pdf_url": raw.get("pdf_url"),
            "arxiv_id": raw.get("arxiv_id"),
        }
