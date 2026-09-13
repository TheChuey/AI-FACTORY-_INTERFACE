"""interface/update_manager.py
============================

Dynamic discovery (Option B) of update modules and the external archive.

Update modules are `.py` files under `interface/updates/<domain>/` (domains:
`engine`, `tools`, `server`). UpdateManager scans those folders, imports every
module, and keeps the live module objects in `active_modules_catalog` so
callers can execute them natively:

    from interface.update_manager import UpdateManager
    mod = UpdateManager().get_active_module("engine", "hello_update")
    mod.run_example()

Retiring a module physically moves its file out of the repo into
`data/interface_archive/<domain>/` so the codebase never accumulates old
experimental logic:
    UpdateManager().move_module_to_external_archive("engine", "hello_update")
"""

from __future__ import annotations

import importlib
import shutil
import sys
from pathlib import Path
from types import ModuleType

BASE_DIR = Path(__file__).resolve().parents[1]
UPDATES_DIR = BASE_DIR / "interface" / "updates"
ARCHIVE_DIR = BASE_DIR / "data" / "interface_archive"

DOMAINS = ("engine", "tools", "server")


class UpdateManager:
    """Finds, imports and tracks update modules by domain."""

    def __init__(self) -> None:
        self.active_modules_catalog: dict[str, dict[str, ModuleType]] = {}
        self.discover()

    # ------------------------------------------------------------------ scan

    def _candidates(self) -> list[tuple[str, str, Path]]:
        """(domain, module_name, file_path) for every update module found."""
        found: list[tuple[str, str, Path]] = []
        for domain in DOMAINS:
            domain_dir = UPDATES_DIR / domain
            if not domain_dir.is_dir():
                continue
            for file in sorted(domain_dir.glob("*.py")):
                if file.name == "__init__.py":
                    continue
                found.append((domain, file.stem, file))
        return found

    def discover(self) -> dict[str, dict[str, ModuleType]]:
        """(Re)scan the updates folders and (re)import every module found."""
        for domain, name, _file in self._candidates():
            module = self._import_module(domain, name)
            self.active_modules_catalog.setdefault(domain, {})[name] = module
        return self.active_modules_catalog

    def discover_all_active_modules(self) -> dict[str, dict[str, ModuleType]]:
        """Clear the catalog and re-import every active update module from disk.

        Alias kept for the docs/02_IMPLEMENTATION_PLAN.md surface; behaves like
        reload_all() so freshly added or edited modules are picked up.
        """
        return self.reload_all()

    def _import_module(self, domain: str, name: str) -> ModuleType:
        full_name = f"interface.updates.{domain}.{name}"
        if full_name in sys.modules:
            return sys.modules[full_name]
        return importlib.import_module(full_name)

    def reload_all(self) -> dict[str, dict[str, ModuleType]]:
        """Drop every cached update module and re-import from disk.

        Used by the `apply` CLI trigger to pick up newly added or edited
        update modules in the current process.
        """
        for full_name in list(sys.modules):
            if full_name == "interface.updates" or full_name.startswith("interface.updates."):
                del sys.modules[full_name]
        self.active_modules_catalog = {}
        return self.discover()

    # --------------------------------------------------------------- Option B

    def get_active_module(self, domain: str, name: str) -> ModuleType:
        """Return the live module object for direct, native execution."""
        try:
            return self.active_modules_catalog[domain][name]
        except KeyError:
            known = sorted(self.active_modules_catalog.get(domain, {}))
            raise KeyError(
                f"no active module '{name}' in domain '{domain}' "
                f"(known modules: {known or 'none'})"
            ) from None

    def list_domain_modules(self, domain: str) -> list[str]:
        """Sorted names of every loaded module under a domain."""
        return sorted(self.active_modules_catalog.get(domain, {}))

    # ----------------------------------------------------------------- archive

    def move_module_to_external_archive(self, domain: str, name: str) -> Path:
        """Move `interface/updates/<domain>/<name>.py` out of the repo into
        `data/interface_archive/<domain>/` and refresh the catalog."""
        source = UPDATES_DIR / domain / f"{name}.py"
        if not source.is_file():
            raise FileNotFoundError(f"update module not found: {source}")
        dest_dir = ARCHIVE_DIR / domain
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / source.name
        if dest.exists():
            dest.unlink()
        shutil.move(str(source), str(dest))
        self.active_modules_catalog.get(domain, {}).pop(name, None)
        sys.modules.pop(f"interface.updates.{domain}.{name}", None)
        return dest

    # ----------------------------------------------------------------- summary

    def summary(self) -> str:
        """Human-readable catalog listing, domain by domain."""
        lines = [f"Update modules in {UPDATES_DIR}:"]
        for domain in sorted(self.active_modules_catalog):
            names = sorted(self.active_modules_catalog[domain])
            lines.append(f"  {domain}/  ->  {', '.join(names) if names else '(none)'}")
        total = sum(len(names) for names in self.active_modules_catalog.values())
        lines.append(f"total: {total} active module(s)")
        return "\n".join(lines)


_manager: UpdateManager | None = None


def get_update_manager() -> UpdateManager:
    """Process-wide UpdateManager singleton."""
    global _manager
    if _manager is None:
        _manager = UpdateManager()
    return _manager