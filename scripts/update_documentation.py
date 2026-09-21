"""scripts/update_documentation.py
=================================

Preferred documentation entry point. Orchestrates the read-only, stateless
documentation build and validates that referenced paths/API/agents/tools exist
against the live tree.

Rules enforced:
- `docs/living/*` is hand-maintained and NEVER written by this tool.
- References must exist; a missing target is reported as a finding, never
  invented.

Usage:
    python scripts/update_documentation.py
    python scripts/update_documentation.py --check      # validate only, no writes
"""

import re
import sys

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DOCS_DIR = BASE_DIR / "docs"
## Known container dirs for repo-relative reference resolution.
_CONTAINERS = ("dashboard", "server", "engine", "tools", "memory", "interface",
               "config", "about", "scripts", "docs", "agent_monitoring",
               "current-known-good-copy")

sys.path.insert(0, str(BASE_DIR))
import scripts.update_blueprint as blueprint      # noqa: E402
import scripts.update_docs as gen                 # noqa: E402


def _path_known(path: str) -> bool:
    """True if the reference resolves under docs/, the repo root, or any
    well-known container directory. Bare filenames (no '/') are treated as
    context-relative and therefore known."""
    if "/" not in path and "\\" not in path:
        return True
    for base in (DOCS_DIR, BASE_DIR):
        try:
            if (base / path).resolve().is_file():
                return True
        except (OSError, ValueError):
            continue
    for container in _CONTAINERS:
        try:
            if (BASE_DIR / container / path).resolve().is_file():
                return True
        except (OSError, ValueError):
            continue
    return False


def validate_reference_paths() -> list[str]:
    """Backticked relative paths in reference docs must resolve to a file."""
    findings: list[str] = []
    pattern = re.compile(
        r"[`\[]([A-Za-z0-9_./\-\\]+\.(?:py|md|json|html|js|css|txt|sqlite3))[`\]]"
    )
    for path in sorted((DOCS_DIR / "reference").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        for match in pattern.finditer(text):
            ref = match.group(1)
            if ref.startswith(("http", "www", "../")) or Path(ref).is_absolute():
                continue
            if not _path_known(ref):
                findings.append(f"[reference] {path.relative_to(BASE_DIR)} -> {ref!r}")
    return findings


def validate_api() -> list[str]:
    """Endpoints in API.md headings must exist as @app.* decorators in
    server.py. Notes (non-heading prose) are not validated."""
    server_file = BASE_DIR / "server" / "server.py"
    api_file = DOCS_DIR / "reference" / "API.md"
    if not server_file.exists() or not api_file.exists():
        return []
    server_text = server_file.read_text(encoding="utf-8")
    endpoint_re = re.compile(r"/api/[A-Za-z0-9_{}/.\-]+")
    missing: set[str] = set()
    for line in api_file.read_text(encoding="utf-8").splitlines():
        if not line.strip().startswith("###"):
            continue
        for match in endpoint_re.finditer(line):
            candidate = match.group(0)
            if candidate.endswith("/"):
                candidate = candidate[:-1]
            if candidate.startswith("/api/") and candidate not in server_text:
                missing.add(candidate)
    return [f"[api] missing in server/server.py: {p}" for p in sorted(missing)]


def validate_agents() -> list[str]:
    """Agent headings in AGENT_REFERENCE.md must exist as agent_library
    folders, honoring the (folder `X/`) annotation where present."""
    lib = BASE_DIR / "engine" / "agent_library"
    ref = DOCS_DIR / "reference" / "AGENT_REFERENCE.md"
    findings: list[str] = []
    if not lib.exists() or not ref.exists():
        return findings
    folders = {p.name for p in lib.glob("*") if p.is_dir()}
    for line in ref.read_text(encoding="utf-8").splitlines():
        match = re.search(r"^##\s*`([A-Za-z0-9_-]+)`", line)
        if not match:
            continue
        folder_match = re.search(r"folder\s+`([^/`]+)/`", line)
        folder = folder_match.group(1) if folder_match else match.group(1)
        if folder not in folders:
            findings.append(f"[agent] folder not in engine/agent_library: {folder!r}")
    return findings


def validate_tools() -> list[str]:
    """Tool ids in TOOL_REFERENCE.md must exist in the tools registry."""
    registry_file = BASE_DIR / "tools" / "registry.py"
    ref = DOCS_DIR / "reference" / "TOOL_REFERENCE.md"
    findings: list[str] = []
    if not registry_file.exists() or not ref.exists():
        return findings
    registry_text = registry_file.read_text(encoding="utf-8")
    for line in ref.read_text(encoding="utf-8").splitlines():
        match = re.search(r"^###\s*`([A-Za-z0-9_-]+)`", line)
        if not match:
            continue
        tool_id = match.group(1)
        if tool_id not in registry_text:
            findings.append(f"[tool] not in tools/registry.py: {tool_id!r}")
    return findings


def validate_reference() -> list[str]:
    """Backticked file refs in reference/FILES.md must resolve."""
    files_file = DOCS_DIR / "reference" / "FILES.md"
    findings: list[str] = []
    if not files_file.exists():
        return findings
    for line in files_file.read_text(encoding="utf-8").splitlines():
        match = re.search(r"`([\w./\-\\]+\.(?:md|py|json|html|js|css|txt|sqlite3))`", line)
        if not match:
            continue
        target = match.group(1)
        if not _path_known(target):
            findings.append(f"[files] missing: {target!r}")
    return findings


def validate() -> list[str]:
    return (validate_reference_paths() + validate_api() + validate_agents()
            + validate_tools() + validate_reference())


def build(only_check: bool) -> None:
    if only_check:
        print("--check: validation only, no writes")
        return
    gen.generate(verbose=True)
    BLUEPRINT_FILE = BASE_DIR / "docs" / "BLUEPRINT.md"
    BLUEPRINT_FILE.write_text(blueprint.build_blueprint(), encoding="utf-8")
    print(f"Wrote {BLUEPRINT_FILE.relative_to(BASE_DIR)}")


def main() -> int:
    only_check = "--check" in sys.argv
    build(only_check)
    findings = validate()
    if findings:
        print("Findings:")
        for item in findings:
            print("  ", item)
    else:
        print("Validation: OK")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())