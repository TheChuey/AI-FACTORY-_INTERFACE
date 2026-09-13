"""scripts/update_docs.py
=======================

Regenerate the documentation snapshots:

    docs/APP_STRUCTURE.md      folder-tree snapshot of the codebase
    docs/APP_CODE_SNAPSHOT.md  one section per code file, with contents

Runtime data and user settings are excluded (data/, venv/, .git/, __pycache__,
the restore baseline folder, app_settings.json, about.json, *.bak, *.pyc).

Usage:
    python scripts/update_docs.py                # both documents
    python scripts/update_docs.py structure      # only APP_STRUCTURE.md
    python scripts/update_docs.py snapshot       # only APP_CODE_SNAPSHOT.md
"""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from interface.restore_manager import file_map, is_excluded  # noqa: E402

BASE_DIR = Path(__file__).resolve().parents[1]
DOCS_DIR = BASE_DIR / "docs"
STRUCTURE_FILE = DOCS_DIR / "APP_STRUCTURE.md"
SNAPSHOT_FILE = DOCS_DIR / "APP_CODE_SNAPSHOT.md"

CODE_EXTS = {".py", ".md", ".json", ".html", ".js", ".css", ".txt"}
_FENCE_LANGUAGE = {
    ".py": "python",
    ".md": "markdown",
    ".json": "json",
    ".html": "html",
    ".js": "javascript",
    ".css": "css",
    ".txt": "text",
}


def _header(title: str) -> str:
    return f"# {title}\n\n_Auto-generated on {datetime.now().isoformat(timespec='seconds')} by `scripts/update_docs.py`._\n"


# ---------------------------------------------------------------- structure

def _render_tree(node: dict) -> list[str]:
    """Render a nested {name: node} dict into box-drawing tree lines."""
    lines: list[str] = []
    items = sorted(node.items(), key=lambda item: (not isinstance(item[1], dict), item[0]))
    for index, (name, child) in enumerate(items):
        is_last = index == len(items) - 1
        lines.append(("`-- " if is_last else "|-- ") + name)
        if isinstance(child, dict):
            pad = "    " if is_last else "|   "
            for line in _render_tree(child):
                lines.append(pad + line)
    return lines


def build_structure_markdown() -> str:
    files = file_map(BASE_DIR)
    root: dict = {}
    for rel in sorted(files):
        parts = rel.split("/")
        node = root
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = None

    markdown = [_header("Terminator1 — App Structure")]
    markdown.append(f"\n```\n{Path(BASE_DIR).name}/\n")
    markdown.extend(_render_tree(root))
    markdown.append("```")
    markdown.append(f"\n_{len(files)} tracked source file(s)._\n")
    return "\n".join(markdown)


# ----------------------------------------------------------------- snapshot

def build_snapshot_markdown() -> str:
    files = file_map(BASE_DIR)
    snapshot: list[str] = [_header("Terminator1 — App Code Snapshot")]
    count = 0
    for rel in sorted(files):
        path = files[rel]
        suffix = path.suffix.lower()
        if suffix not in CODE_EXTS or not path.is_file():
            continue
        if path.resolve() == SNAPSHOT_FILE.resolve():
            continue  # never embed the snapshot inside itself
        language = _FENCE_LANGUAGE.get(suffix, "")
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            text = f"(unreadable: {path})"
        snapshot.append(f"\n## {rel}\n")
        snapshot.append(f"```{language}\n{text}\n```")
        count += 1
    snapshot.append(f"\n_{count} code file(s)._")
    return "\n".join(snapshot)


# -------------------------------------------------------------------- main

def main() -> int:
    only = sys.argv[1].lower() if len(sys.argv) > 1 else ""
    if only not in ("structure", "snapshot", ""):
        print(__doc__)
        return 1

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    if only in ("", "structure"):
        STRUCTURE_FILE.write_text(build_structure_markdown(), encoding="utf-8")
        print(f"Wrote {STRUCTURE_FILE.relative_to(BASE_DIR)}")
    if only in ("", "snapshot"):
        SNAPSHOT_FILE.write_text(build_snapshot_markdown(), encoding="utf-8")
        print(f"Wrote {SNAPSHOT_FILE.relative_to(BASE_DIR)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())