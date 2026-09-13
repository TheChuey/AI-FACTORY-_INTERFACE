"""Change the app title/subtitle shown as the H1 on index.html, and trigger
the modular update/restore system.

Usage:
    python about/set_title.py                      edit about.json interactively
    python about/set_title.py [title [subtitle]]   set title/subtitle positionally
    python about/set_title.py apply [--snapshot]   reload update modules + regen docs
    python about/set_title.py snapshot [folder]    publish current tree as baseline
    python about/set_title.py restore [baseline] [--dry-run]   roll back modified files

about.json is read by the server on every request, so a title change shows
after a refresh.
"""
import json
import subprocess
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve()
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

F = _SCRIPT_DIR.parent / "about.json"


def _save_about(data: dict) -> None:
    F.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _load_about() -> dict:
    return json.loads(F.read_text(encoding="utf-8")) if F.exists() else {}


def cmd_apply(argv):
    """Reload all active update modules and regenerate the docs snapshots."""
    from interface.update_manager import UpdateManager
    from interface.restore_manager import RestoreManager

    manager = UpdateManager()
    manager.reload_all()
    print(manager.summary())

    script = _PROJECT_ROOT / "scripts" / "update_docs.py"
    result = subprocess.run([sys.executable, str(script)], cwd=str(_PROJECT_ROOT))
    if result.returncode != 0:
        print(f"WARNING: docs regeneration exited with code {result.returncode}")
        return 1
    print("Docs snapshots regenerated (docs/APP_STRUCTURE.md, docs/APP_CODE_SNAPSHOT.md).")

    if "--snapshot" in argv:
        # Snapshot AFTER the docs regen so the baseline carries the fresh
        # snapshots (documents the ordering bug fix - previously the baseline
        # was published with pre-regen docs, making restore --dry-run report
        # the two doc files as modified).
        count = RestoreManager().snapshot_baseline()
        print(f"Baseline refreshed: {count} file(s) -> current-known-good-copy/")

    return 0


def cmd_snapshot(argv):
    """Publish a complete working copy of the current tree as the baseline."""
    from interface.restore_manager import RestoreManager

    dest = argv[0] if argv else None
    count = RestoreManager().snapshot_baseline(dest)
    label = dest or "current-known-good-copy/"
    print(f"Baseline published: {count} file(s) -> {label}")
    return 0


def cmd_restore(argv):
    """Compare against the baseline, back up and roll back modified files."""
    from interface.restore_manager import RestoreManager

    baseline = None
    dry_run = False
    for arg in argv:
        if arg in ("-n", "--dry-run"):
            dry_run = True
        elif arg.startswith("--"):
            print(f"unknown option: {arg}")
            return 1
        elif baseline is None:
            baseline = arg
        else:
            print(f"unexpected argument: {arg}")
            return 1

    RestoreManager().restore(baseline, dry_run=dry_run)
    return 0


def cmd_title(argv) -> int:
    """Original behavior: edit about.json interactively or positionally."""
    data = _load_about()
    data.setdefault("title", "Genessis")
    data.setdefault("subtitle", "Home")

    for i, key in enumerate(("title", "subtitle")):
        value = argv[i] if i < len(argv) else None
        if value is None:
            try:
                value = input(f"{key} [{data[key]}]: ").strip()
            except EOFError:
                break
        if value:
            data[key] = value

    _save_about(data)
    print("Saved ->", data["title"])
    return 0


COMMANDS = {
    "apply": cmd_apply,
    "snapshot": cmd_snapshot,
    "restore": cmd_restore,
}


def main() -> int:
    args = sys.argv[1:]
    if args and args[0] in COMMANDS:
        return COMMANDS[args[0]](args[1:])
    return cmd_title(args)


if __name__ == "__main__":
    sys.exit(main())