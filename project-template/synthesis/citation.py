from __future__ import annotations

from typing import Any


def format_citation(frontmatter: dict[str, Any]) -> str:
    authors = frontmatter.get("authors", "Unknown")
    if isinstance(authors, list):
        author_display = ", ".join(str(a) for a in authors[:3])
        if len(authors) > 3:
            author_display += " et al."
    else:
        author_display = str(authors)

    year = str(frontmatter.get("date_published", "n.d."))[:4]
    title = str(frontmatter.get("title", "Untitled"))
    url = str(frontmatter.get("source_url", ""))
    return f"{author_display} ({year}). *{title}*. {url}"


def format_inline_citation(frontmatter: dict[str, Any]) -> str:
    authors = frontmatter.get("authors", "Unknown")
    if isinstance(authors, list) and authors:
        last_name = str(authors[0]).split()[-1]
    else:
        last_name = str(authors).split()[-1]

    year = str(frontmatter.get("date_published", "n.d."))[:4]
    url = str(frontmatter.get("source_url", ""))
    return f"[{last_name}, {year}]({url})"
