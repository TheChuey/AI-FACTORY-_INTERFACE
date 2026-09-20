"""interface/restore_manager.py
==============================

Master-copy backup and restore manager.

`RestoreManager` keeps ONE known-good master copy of the live source tree at
`current-known-good-copy/` (runtime data and user settings excluded) and can
roll the whole app back to it:

    RestoreManager().snapshot()   # publish current tree as the master copy
    RestoreManager().status()     # master info + how many files drift
    RestoreManager().restore()    # overlay every master file back onto live

Restore semantics (overlay): every file in the master copy is written over the
live tree. A live file that differs is backed up first into
`agent_monitoring/data/snapshots/pre_restore_backup/`, then overwritten; master
files missing from the live tree are added; live-only files are left untouched.
Runtime data and user settings are always excluded:

    data/  agent_monitoring/data/  venv/  .git/  __pycache__/
    current-known-good-copy/  test/  BASELINE_MANIFEST.json
    dashboard/config/app_settings.json  about/about.json  *.bak  *.pyc  *.pyo
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
BACKUP_ROOT = BASE_DIR / "agent_monitoring" / "data" / "snapshots" / "pre_restore_backup"
DOCS_SCRIPT = BASE_DIR / "scripts" / "update_docs.py"
MANIFEST_NAME = "BASELINE_MANIFEST.json"

# Paths never compared, copied, backed up or restored.
EXCLUDED_TOP = {"data", "agent_monitoring/data", "venv", ".git", "__pycache__", "current-known-good-copy", "test"}
# User/runtime files never touched even when their relative path matches.
EXCLUDED_FILES = {"dashboard/config/app_settings.json", "about/about.json", MANIFEST_NAME}
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


def _read_manifest(baseline: Path) -> dict:
    manifest = baseline / MANIFEST_NAME
    if not manifest.is_file():
        return {}
    try:
        return json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


class RestoreManager:
    """Master-copy publishing, drift status and overlay restore."""

    # ------------------------------------------------------------- snapshot

    def snapshot(self, dest: str | Path | None = None) -> int:
        """Publish a complete working copy of the current tree into the
        master folder (default: current-known-good-copy/). Returns the
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
        manifest_file = target / MANIFEST_NAME
        manifest_file.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(
            f"Master copy published: {manifest.get('baseline')} "
            f"({manifest.get('files')} files, created {manifest.get('created')})"
        )
        return len(live)

    # -------------------------------------------------------------- status

    def status(self) -> dict:
        """Master copy info plus how many live files drift from it."""
        folder = str(DEFAULT_BASELINE)
        if not DEFAULT_BASELINE.is_dir():
            return {
                "exists": False,
                "folder": folder,
                "files": 0,
                "created": None,
                "modified": 0,
                "modified_files": [],
                "error": "No master copy yet - save the current state as master first.",
            }
        manifest = _read_manifest(DEFAULT_BASELINE)
        base_map = file_map(DEFAULT_BASELINE)
        live_map = file_map(BASE_DIR)
        modified = sorted(
            rel for rel in base_map
            if rel not in live_map or _sha256(live_map[rel]) != _sha256(base_map[rel])
        )
        return {
            "exists": True,
            "folder": folder,
            "files": manifest.get("files", len(base_map)),
            "created": manifest.get("created"),
            "modified": len(modified),
            "modified_files": modified[:50],
            "error": None,
        }

    # ------------------------------------------------------------- restore

    @staticmethod
    def _run_docs_regeneration() -> bool:
        """Regenerate docs/APP_STRUCTURE.md + docs/APP_CODE_SNAPSHOT.md."""
        if not DOCS_SCRIPT.is_file():
            print("SKIP: scripts/update_docs.py not found")
            return False
        result = subprocess.run(
            [sys.executable, str(DOCS_SCRIPT)], cwd=str(BASE_DIR)
        )
        if result.returncode == 0:
            print("Docs snapshots regenerated (docs/APP_STRUCTURE.md, docs/APP_CODE_SNAPSHOT.md).")
            return True
        print(f"WARNING: docs regeneration exited with code {result.returncode}")
        return False

    def restore(self) -> dict:
        """Overlay every master file back onto the live tree.

        Differing live files are backed up first into
        agent_monitoring/data/snapshots/pre_restore_backup/<stamp>/; master files
        missing from live are added; live-only files are never deleted. Docs are
        regenerated afterwards."""
        if not DEFAULT_BASELINE.is_dir():
            raise NotADirectoryError(
                "No master copy found - save the current state as master first."
            )
        base_map = file_map(DEFAULT_BASELINE)
        live_map = file_map(BASE_DIR)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_root = BACKUP_ROOT / stamp

        to_write = sorted(
            rel for rel in base_map
            if rel not in live_map or _sha256(live_map[rel]) != _sha256(base_map[rel])
        )
        if to_write:
            backup_root.mkdir(parents=True, exist_ok=True)

        restored = added = 0
        for rel in to_write:
            target = BASE_DIR / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            previous = live_map.get(rel)
            if previous is not None:
                backup_file = backup_root / rel
                backup_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(previous, backup_file)
                restored += 1
            else:
                added += 1
            shutil.copy2(base_map[rel], target)

        docs_regenerated = self._run_docs_regeneration()
        backup_dir = str(backup_root) if to_write else None
        if to_write:
            print(
                f"Restored {restored} overwritten file(s) + {added} new file(s) "
                f"from {DEFAULT_BASELINE} (backup -> {backup_root})"
            )
        else:
            print("Nothing to restore - live tree matches the master copy.")
        return {
            "restored": restored,
            "added": added,
            "backup_dir": backup_dir,
            "docs_regenerated": docs_regenerated,
        }


_manager: RestoreManager | None = None


def get_restore_manager() -> RestoreManager:
    """Process-wide RestoreManager singleton."""
    global _manager
    if _manager is None:
        _manager = RestoreManager()
    return _manager