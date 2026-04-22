from __future__ import annotations

from datetime import datetime
from pathlib import Path

VAULT_DIR = Path("vault")
INDEX_FILE = VAULT_DIR / "_index.md"


def _list_markdown(path: Path) -> list[Path]:
    if not path.exists():
        return []
    return sorted(path.glob("*.md"))


def rebuild_index() -> Path:
    sources = _list_markdown(VAULT_DIR / "sources")
    extracted = _list_markdown(VAULT_DIR / "extracted")
    synthesis = _list_markdown(VAULT_DIR / "synthesis")

    lines = [
        "# Research Index",
        f"**Last updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        f"- Sources: {len(sources)}",
        f"- Extracted: {len(extracted)}",
        f"- Synthesis: {len(synthesis)}",
        "",
        "## Sources",
    ]
    lines.extend(f"- {item.name}" for item in sources)
    lines.extend(["", "## Extracted"])
    lines.extend(f"- {item.name}" for item in extracted)
    lines.extend(["", "## Synthesis"])
    lines.extend(f"- {item.name}" for item in synthesis)

    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    INDEX_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return INDEX_FILE


if __name__ == "__main__":
    index_path = rebuild_index()
    print(f"[INDEX] rebuilt: {index_path}")
