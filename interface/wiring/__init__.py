"""interface/wiring/
====================

The connection layer between the module loaders and the running app.

- `UpdateManager` discovers `interface/updates/<domain>/*.py` - callable
  natively from core code, traced by `InterfaceDispatcher`.
- `CustomModuleManager` discovers flat `data/custom_modules/*.py` - each with
  a `UI_MANIFEST` (header button) and `register_routes(app)` (FastAPI route).

This package joins the two worlds:

- route registration for custom modules lives here (previously hand-rolled in
  `server/server.py`), still idempotent per process;
- custom modules are bridged into the update manager's catalog under the
  virtual domain `custom`, so their functions are ALSO callable from core
  code through the same traced dispatcher:

      InterfaceDispatcher().execute_action("custom", <module>, <func>, ...)

`WiringManager` is the front door: `wire(app)` at boot, `rewire(app)` on
`apply`, `registry()` for `/api/interface/status`. Nothing here replaces the
loaders - it only connects them to the app.
"""

from __future__ import annotations

from interface.wiring.bridges import BRIDGE_DOMAIN, CustomModuleBridge

__all__ = ["WiringManager", "CustomModuleBridge", "BRIDGE_DOMAIN"]


class WiringManager:
    """Front door for wiring loaded modules into the running app."""

    def __init__(self, update_manager=None, custom_manager=None) -> None:
        if update_manager is None:
            from interface.update_manager import get_update_manager
            update_manager = get_update_manager()
        if custom_manager is None:
            from interface.custom_module_manager import get_custom_module_manager
            custom_manager = get_custom_module_manager()
        self.update_manager = update_manager
        self.custom_manager = custom_manager
        self.bridge = CustomModuleBridge(update_manager, custom_manager)

    # ------------------------------------------------------------------ wiring

    def wire(self, app=None) -> None:
        """Scan custom modules, register their routes once per process and
        bridge them into the dispatcher's catalog.

        `app` may be None (CLI usage) - then discovery + bridging still run
        but route registration needs an app and is skipped.
        """
        self.custom_manager.discover_all_active_modules()
        if app is not None:
            self.bridge.register_routes(app)
        self.bridge.activate()
        if app is not None:
            app.state.wiring = self

    def rewire(self, app=None) -> None:
        """Reload BOTH loaders from disk, then wire() again (the `apply`
        trigger). The bridge is re-injected because reload_all() rebuilds the
        update catalog from scratch."""
        self.update_manager.reload_all()
        self.wire(app)

    # ----------------------------------------------------------------- registry

    def registry(self) -> dict:
        """Consolidated view of both layers, for /api/interface/status."""
        from server.paths import CUSTOM_MODULES_DIR

        if self.custom_manager is not None:
            active = self.custom_manager.list_modules()
            ui_manifests = self.custom_manager.ui_manifests()
        else:
            active, ui_manifests = [], []

        catalog: dict[str, list[str]] = {}
        if self.update_manager is not None:
            for domain, names in sorted(self.update_manager.active_modules_catalog.items()):
                if domain == BRIDGE_DOMAIN:
                    continue
                catalog[domain] = sorted(names)

        return {
            "catalog": catalog,
            "custom_modules": {"dir": str(CUSTOM_MODULES_DIR), "active": active},
            "ui_manifests": ui_manifests,
            "bridge": {
                "domain": BRIDGE_DOMAIN,
                "active": self.bridge.reachable_names(),
            },
        }

    # ------------------------------------------------------------------ summary

    def summary(self) -> str:
        """Human-readable catalog + bridge listing for boot / CLI."""
        lines = []
        if self.update_manager is not None:
            lines.append(self.update_manager.summary(exclude=BRIDGE_DOMAIN))
        if self.custom_manager is not None:
            lines.append(self.custom_manager.summary())
        lines.append(self.bridge.summary())
        return "\n".join(lines)