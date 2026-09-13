"""interface/restore_manager.py
==============================

Isolated baseline comparison, backup and rollback manager.

RestoreManager compares the live codebase against a known-good baseline using
SHA-256 hashes, copies every file it is about to overwrite into
`data/snapshots/pre_restore_backup/`, and only then restores the baseline
version. Runtime data and user settings are always excluded:

    data/  venv/  .git/  __pycache__/  current-known-good-copy/  test/
    dashboard/config/app_settings.json  about/about.json  *.bak  *.pyc  *.pyo

Restore semantics: only files present in BOTH trees whose checksum differs are
overwritten. Files that exist only in the baseline or only in the live tree
are reported but left untouched.

Workflow:
    RestoreManager().snapshot_baseline()   # publish current tree as baseline
    RestoreManager().restore(dry_run=True) # preview what would change
    RestoreManager().restore()             # back up + roll back, then sync docs
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_BASELINE = BASE_DIR / "current-known-good-copy"
LEGACY_BASELINE = BASE_DIR / "test"
BACKUP_ROOT = BASE_DIR / "data" / "snapshots" / "pre_restore_backup"
DOCS_SCRIPT = BASE_DIR / "scripts" / "update_docs.py"
MANIFEST_NAME = "BASELINE_MANIFEST.json"

# Top-level entries never compared, copied, backed up or restored.
EXCLUDED_TOP = {"data", "venv", ".git", "__pycache__", "current-known-good-copy", "test"}
# User/runtime files never touched even when their relative path matches.
EXCLUDED_FILES = {"dashboard/config/app_settings.json", "about/about.json"}
EXCLUDED_SUFFIXES = (".bak", ".pyc", ".pyo")

_TOP = EXCLUDED_TOP
_FILES = EXCLUDED_FILES
_SUFFIXES = EXCLUDED_SUFFIXES


def is_excluded(rel_path: str) -> bool:
    """True when a relative path must never participate in a snapshot/restore."""
    rel = rel_path.replace("\\", "/")
    if rel.startswith("./"):
        rel = rel[2:]
    if rel in _FILES:
        return True
    if rel.endswith(_SUFFIXES):
        return True
    return any(part in _TOP for part in rel.split("/"))


def file_map(root: Path) -> dict[str, Path]:
    """{relative_path: absolute_path} for every file under `root`, excluding
    runtime data and user settings."""
    mapping: dict[str, Path] = {}
    root = root.resolve()
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root)
        dirnames[:] = [
            d for d in dirnames
            if not is_excluded(str((Path(rel_dir) / d).as_posix()))
        ]
        for filename in filenames:
            full = Path(dirpath) / filename
            rel = full.relative_to(root).as_posix()
            if is_excluded(rel):
                continue
            mapping[rel] = full
    return mapping


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


class RestoreManager:
    """SHA-256 baseline compare, safety backup and rollback."""

    # ------------------------------------------------------------ snapshots

    def snapshot_baseline(self, dest: str | Path | None = None) -> int:
        """Publish a complete working copy of the current tree into the
        baseline folder (default: current-known-good-copy/). Returns the
        number of files copied."""
        target = Path(dest or DEFAULT_BASELINE).resolve()
        live = file_map(BASE_DIR)

        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True, exist_ok=True)

        for rel, source in sorted(live.items()):
            dest_file = target / rel
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest_file)

        manifest = {
            "created": datetime.now().isoformat(timespec="seconds"),
            "baseline": str(target),
            "files": len(live),
            "excludes": {
                "top": sorted(_TOP),
                "files": sorted(_FILES),
                "suffixes": list(_SUFFIXES),
            },
        }
        (target / MANIFEST_NAME).write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        self._report_manifest(target)
        return len(live)

    @staticmethod
    def _report_manifest(baseline: Path) -> None:
        manifest = baseline / MANIFEST_NAME
        if not manifest.is_file():
            return
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        print(
            f"Baseline: {data.get('baseline', baseline)} "
            f"({data.get('files', '?')} files, created {data.get('created', '?')})"
        )

    # ------------------------------------------------------------- restore

    def _resolve_baseline(self, given: str | Path | None) -> Path:
        if given:
            path = Path(given).resolve()
            if not path.is_dir():
                raise NotADirectoryError(f"baseline folder not found: {path}")
            return path
        if DEFAULT_BASELINE.is_dir():
            return DEFAULT_BASELINE
        if LEGACY_BASELINE.is_dir():
            print(
                f"WARNING: '{DEFAULT_BASELINE.name}' not found - falling back to "
                f"'{LEGACY_BASELINE.name}' (pre-infection snapshot, may be outdated). "
                f"Run `python about/set_title.py snapshot` to publish the current tree."
            )
            return LEGACY_BASELINE
        raise NotADirectoryError(
            "no baseline found - run `python about/set_title.py snapshot` first"
        )

    @staticmethod
    def _run_docs_regeneration() -> None:
        if not DOCS_SCRIPT.is_file():
            print("SKIP: scripts/update_docs.py not found")
            return
        result = subprocess.run(
            [sys.executable, str(DOCS_SCRIPT)], cwd=str(BASE_DIR)
        )
        if result.returncode == 0:
            print("Docs snapshots regenerated (docs/APP_STRUCTURE.md, docs/APP_CODE_SNAPSHOT.md).")
        else:
            print(f"WARNING: docs regeneration exited with code {result.returncode}")

    def diff(self, baseline: str | Path | None = None) -> dict:
        """Silent SHA-256 comparison against the baseline (no printing).

        Returns { baseline, shared, modified, skipped, untracked } where
        `modified` lists relative paths present in both trees whose checksum
        differs (ready to restore/back-up) and skipped/untracked hold the
        baseline-only / live-only reports."""
        base = self._resolve_baseline(baseline)
        base = base.resolve()

        live_map = file_map(BASE_DIR)
        base_map = file_map(base)
        shared = sorted(set(live_map) & set(base_map))
        modified = [rel for rel in shared if _sha256(live_map[rel]) != _sha256(base_map[rel])]
        skipped = sorted(set(base_map) - set(live_map))
        untracked = sorted(set(live_map) - set(base_map))

        return {
            "baseline": str(base),
            "shared": len(shared),
            "modified": modified,
            "skipped": skipped,
            "untracked": untracked,
        }

    def restore(self, baseline: str | Path | None = None, dry_run: bool = False) -> dict:
        """Compare the live tree against the baseline, back up and overwrite
        modified files (or just report when `dry_run`). Re-runs the docs
        regeneration after a real restore."""
        base = self._resolve_baseline(baseline)
        base = base.resolve()
        self._report_manifest(base)

        diff = self.diff(base)
        modified = list(diff["modified"])
        skipped = list(diff["skipped"])
        untracked = list(diff["untracked"])

        print(f"Comparing against baseline: {base}")
        print(f"  shared files: {diff['shared']}")
        print(f"  modified:     {len(modified)}")
        print(f"  baseline-only: {len(skipped)} (report only, not copied)")
        print(f"  live-only:    {len(untracked)} (report only, not touched)")

        for rel in skipped:
            print(f"    skip:  {rel}")
        for rel in untracked:
            print(f"    keep:  {rel}")

        result = {
            "baseline": str(base),
            "modified": len(modified),
            "skipped": len(skipped),
            "untracked": len(untracked),
            "backup_dir": None,
        }

        if not modified:
            print("Nothing to restore - live tree matches the baseline.")
            return result

        if dry_run:
            print("DRY RUN - no changes made. Would restore these files:")
            for rel in modified:
                print(f"    restore: {rel}")
            return result

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = BACKUP_ROOT / stamp
        backup_dir.mkdir(parents=True, exist_ok=True)

        live_map = file_map(BASE_DIR)
        base_map = file_map(base)

        for rel in modified:
            target = live_map[rel]
            backup_file = backup_dir / rel
            backup_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, backup_file)
            shutil.copy2(base_map[rel], target)

        result["backup_dir"] = str(backup_dir)
        print(f"Backed up {len(modified)} file(s) -> {backup_dir}")
        print(f"Restored  {len(modified)} file(s) from {base}")
        self._run_docs_regeneration()
        return result


_manager: RestoreManager | None = None


def get_restore_manager() -> RestoreManager:
    """Process-wide RestoreManager singleton."""
    global _manager
    if _manager is None:
        _manager = RestoreManager()
    return _manager