from __future__ import annotations

from typing import Any


class JinaSearchConnector:
    def __init__(self, max_results: int = 10):
        self.max_results = max_results

    def search(self, query: str) -> list[dict[str, Any]]:
        if not query.strip():
            return []
        return [
            {
                "title": f"Mock result for: {query}",
                "url": f"https://example.com/search?q={query.replace(' ', '+')}",
                "description": "placeholder",
                "source_type": "web",
            }
        ][: self.max_results]
