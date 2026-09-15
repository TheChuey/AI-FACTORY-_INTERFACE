"""interface/custom_module_manager.py
====================================

Phase 1 - Dynamic External Module Loader & Auto-Route Registration.

This is a SEPARATE, ADDITIVE system from interface/update_manager.py's
domain-based UpdateManager (engine/tools/server under interface/updates/).
It does not touch that catalog or its endpoints.

CustomModuleManager scans a single flat folder - server.paths.CUSTOM_MODULES_DIR
(configurable in Settings as "Custom Modules Path", default
data/custom_modules/) - for standalone .py files and imports each one with
importlib.util (they live outside any Python package, so this does NOT use
`import`/dotted module names the way UpdateManager does).

Convention for a drop-in module (see about/set_title.py's `create-module`
CLI command for a generator):

    UI_MANIFEST = {
        "module_id": "my_feature",
        "buttons": [ { "id": ..., "label": ..., "target": "header",
                        "action": "prompt_input", "prompt_message": ...,
                        "api_endpoint": "/api/my_feature/execute",
                        "title": ... } ]
    }

    def register_routes(app):
        @app.post("/api/my_feature/execute")
        def execute(payload: dict):
            ...

server/server.py's lifespan() discovers these at boot, calls register_routes()
once per module, and GET /api/interface/status exposes every active module's
UI_MANIFEST (via ui_manifests) so dashboard/js/ui/header-nav.js can render the
buttons dynamically (Phase 2) without ever editing index.html or header-nav.js
by hand.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from server.paths import CUSTOM_MODULES_DIR


class CustomModuleManager:
    """Finds, imports and tracks flat drop-in modules from CUSTOM_MODULES_DIR."""

    def __init__(self) -> None:
        self.active_modules_catalog: dict[str, ModuleType] = {}
        self.discover_all_active_modules()

    # ------------------------------------------------------------------ scan

    def discover_all_active_modules(self) -> dict[str, ModuleType]:
        """(Re)scan CUSTOM_MODULES_DIR and (re)import every module found.

        Files starting with "_" or "." are skipped (private/hidden helpers).
        A module that fails to import is logged and skipped - one broken
        drop-in file must never take the whole app down.
        """
        self.active_modules_catalog.clear()

        target_dir = Path(CUSTOM_MODULES_DIR)
        if not target_dir.exists():
            target_dir.mkdir(parents=True, exist_ok=True)
            return self.active_modules_catalog

        for file in sorted(target_dir.glob("*.py")):
            if file.name.startswith(("_", ".")):
                continue
            mod_name = file.stem
            try:
                module = self._import_from_path(mod_name, file)
                self.active_modules_catalog[mod_name] = module
            except Exception as exc:
                print(f"[custom-modules] Failed to load {file.name}: {exc}")

        return self.active_modules_catalog

    def reload_all(self) -> dict[str, ModuleType]:
        """Alias kept for symmetry with UpdateManager.reload_all()."""
        return self.discover_all_active_modules()

    def _import_from_path(self, mod_name: str, file: Path) -> ModuleType:
        """Import a standalone .py file that isn't part of any package."""
        qualified_name = f"custom_modules.{mod_name}"
        spec = importlib.util.spec_from_file_location(qualified_name, file)
        if spec is None or spec.loader is None:
            raise ImportError(f"could not build an import spec for {file}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[qualified_name] = module
        spec.loader.exec_module(module)
        return module

    # -------------------------------------------------------------- lookups

    def get_active_module(self, name: str) -> ModuleType:
        """Return the live module object for direct, native execution."""
        try:
            return self.active_modules_catalog[name]
        except KeyError:
            known = sorted(self.active_modules_catalog)
            raise KeyError(
                f"no active custom module '{name}' "
                f"(known modules: {known or 'none'})"
            ) from None

    def list_modules(self) -> list[str]:
        """Sorted names of every loaded custom module."""
        return sorted(self.active_modules_catalog)

    def ui_manifests(self) -> list[dict]:
        """UI_MANIFEST dict from every active module that declares one."""
        manifests = []
        for mod in self.active_modules_catalog.values():
            manifest = getattr(mod, "UI_MANIFEST", None)
            if isinstance(manifest, dict):
                manifests.append(manifest)
        return manifests

    # ------------------------------------------------------------- summary

    def summary(self) -> str:
        """Human-readable catalog listing."""
        names = sorted(self.active_modules_catalog)
        lines = [f"Custom drop-in modules in {CUSTOM_MODULES_DIR}:"]
        lines.append("  " + (", ".join(names) if names else "(none)"))
        lines.append(f"total: {len(names)} active module(s)")
        return "\n".join(lines)


_manager: CustomModuleManager | None = None


def get_custom_module_manager() -> CustomModuleManager:
    """Process-wide CustomModuleManager singleton (mirrors get_update_manager)."""
    global _manager
    if _manager is None:
        _manager = CustomModuleManager()
    return _manager
