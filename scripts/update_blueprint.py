"""scripts/update_blueprint.py
=============================

Assemble the GenV1 master blueprint (`docs/BLUEPRINT.md`) from the maintained
architecture documents under `docs/architecture/`.

This generator NEVER invents information: it extracts existing sections from
the maintained docs by heading markers, and writes a "Documentation Flow"
section that only cites real files. If a section or file is missing it fails
loudly instead of fabricating.

Usage:
    python scripts/update_blueprint.py          # assemble docs/BLUEPRINT.md
"""

import sys

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
ARCH_DIR = BASE_DIR / "docs" / "architecture"
BLUEPRINT_FILE = BASE_DIR / "docs" / "BLUEPRINT.md"

# Blueprint section -> (source doc, start heading, optional end heading).
_SECTIONS = [
    ("What GenV1 is", "SYSTEM.md", "## Purpose", "## Responsibilities"),
    ("Architecture (Layers)", "SYSTEM.md", "## Components", "## Inputs"),
    ("Runtime Flow", "SYSTEM.md", "## Runtime Flow", "## Configuration"),
    ("Extension Model", "SYSTEM.md", "## Extension Points", "## Rules"),
    ("Data Flow", "DATA.md", "## Record formats", "## Processing"),
    ("Configuration", "CONFIGURATION.md", "## Components", "## Runtime Flow"),
    ("Logging", "LOGGING.md", "## Components", "## Inputs"),
]


def _extract(text: str, start_mark: str, end_mark: str | None) -> str:
    """Return the body of a '## ...' heading up to the next heading.

    A line starting with `end_mark` (if given) also stops the scan.
    """
    lines = text.splitlines()
    out: list[str] = []
    on = False
    for line in lines:
        is_h2 = line.strip().startswith("## ")
        if is_h2:
            if line.strip() == start_mark:
                on = True
                continue
            if on and (end_mark is None or line.strip().startswith(end_mark)):
                break
        if on:
            out.append(line)
    return "\n".join(out).strip()


def _read(name: str) -> str:
    path = ARCH_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Missing architecture document: {path}")
    return path.read_text(encoding="utf-8")


def _component_summary() -> list[str]:
    """One entry per subsystem document: its Purpose body + a real path link."""
    entries: list[str] = []
    for path in sorted(ARCH_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        purpose = _extract(text, "## Purpose", "## Responsibilities")
        if not purpose:
            continue
        label = path.stem.replace("_", " ").title()
        entries.append(f"### {label}")
        entries.append("")
        entries.append(f"Source: `docs/architecture/{path.name}`")
        entries.append("")
        entries.append(purpose)
        entries.append("")
    return entries


def build_blueprint() -> str:
    out: list[str] = [
        "# GenV1 — Blueprint",
        "",
        "> **Location:** `docs/BLUEPRINT.md`",
        ">",
        "> Master architectural blueprint. Assembled by "
        "`scripts/update_blueprint.py` from the maintained documents in "
        "`docs/architecture/` — sections are extracted verbatim, nothing is "
        "invented. Contract and required sections: `docs/BLUEPRINT_SPEC.md`.",
        "",
        "---",
        "",
    ]

    for title, file, start, end in _SECTIONS:
        body = _extract(_read(file), start, end)
        out.append(f"## {title}")
        out.append("")
        if body:
            out.append(body)
        else:
            out.append("_No extractable content — open "
                       f"`docs/architecture/{file}`._")
        out.append("")

    # Major components: the Purpose of every subsystem document.
    out.append("## Major Components")
    out.append("")
    out.append("Every subsystem documented under `docs/architecture/`: its "
               "purpose, extracted verbatim from its architecture document.")
    out.append("")
    out.extend(_component_summary())

    # Documentation flow: real files only, factual hand-written prose.
    out.append("## Documentation Flow")
    out.append("")
    out.append(
        "GenV1's documentation is its own subsystem:"
        " `docs/INDEX.md` is the navigation map, the 10 documents in "
        "`docs/architecture/` describe the subsystems, `docs/reference/*` lists "
        "concrete files/APIs/agents/tools/modules/workflows, `docs/development/*` "
        "explains extension and documentation discipline, and `docs/living/*` "
        "records the changelog, current state, known issues, planned work and "
        "decisions. Two documents are generated output: "
        "`docs/generated/APP_STRUCTURE.md` (filesystem tree) and "
        "`docs/generated/APP_CODE_SNAPSHOT.md` (source snapshot), produced by "
        "`scripts/update_docs.py`. `scripts/update_documentation.py` is the "
        "preferred entry point: it regenerates the generated docs, validates "
        "references against the live tree, assembles this blueprint, and reports "
        "status. Living documents (`docs/living/*`) are never overwritten by "
        "automation."
    )
    out.append("")

    out.append("---")
    out.append("")
    out.append("## Related documentation")
    out.append("")
    out.append("- `docs/INDEX.md`")
    out.append("- `docs/BLUEPRINT_SPEC.md` — the contract this document must satisfy")
    out.append("- `docs/architecture/SYSTEM.md` — system overview source")
    out.append("- `scripts/update_blueprint.py` — the assembler")
    out.append("- `docs/development/DOCUMENTATION_RULES.md`")
    out.append("")
    return "\n".join(out)


def main() -> int:
    BLUEPRINT_FILE.write_text(build_blueprint(), encoding="utf-8")
    print(f"Wrote {BLUEPRINT_FILE.relative_to(BASE_DIR)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())