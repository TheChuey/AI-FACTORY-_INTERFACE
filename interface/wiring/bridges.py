"""interface/wiring/bridges.py
==============================

The concrete connections between the module loaders and the running app:

  - Route registration: calls `register_routes(app)` for every custom drop-in
    module, at most once per process. FastAPI allows adding routes at any
    time, so brand-new modules can go live via `apply` without a restart.
  - The dispatcher bridge: custom modules are mirrored into the update
    manager's catalog under the virtual domain `BRIDGE_DOMAIN`, making them
    reachable from core code through the SAME traced dispatcher used for
    update modules:

        InterfaceDispatcher().execute_action("custom", "analytics_builder",
                                             "my_logic", arg)

    The bridge is re-injected after every reload because
    UpdateManager.reload_all() rebuilds its catalog from scratch.
"""

from __future__ import annotations

BRIDGE_DOMAIN = "custom"

# Custom drop-in modules whose register_routes(app) has already been called
# for THIS process (see CustomModuleBridge.register_routes).
_REGISTERED: set[str] = set()


class CustomModuleBridge:
    """Joins the flat custom drop-ins to the domain-based update world."""

    def __init__(self, update_manager=None, custom_manager=None) -> None:
        self.update_manager = update_manager
        self.custom_manager = custom_manager

    # ------------------------------------------------------------------ routes

    def register_routes(self, app) -> list[str]:
        """Call register_routes(app) for every not-yet-registered custom
        module. Returns the names newly registered this call."""
        newly_registered: list[str] = []
        if self.custom_manager is None:
            return newly_registered
        for name, mod in self.custom_manager.active_modules_catalog.items():
            if name in _REGISTERED:
                continue
            if hasattr(mod, "register_routes"):
                try:
                    mod.register_routes(app)
                    _REGISTERED.add(name)
                    newly_registered.append(name)
                    print(f"[custom-modules] Auto-registered routes for: {name}")
                except Exception as exc:
                    print(f"[custom-modules] Failed to register routes for {name}: {exc}")
        return newly_registered

    # ------------------------------------------------------------------ bridge

    def activate(self) -> None:
        """Mirror every active custom module into the update manager's catalog
        under BRIDGE_DOMAIN so execute_action("custom", ...) can reach it."""
        self.deactivate()
        if self.custom_manager is None or self.update_manager is None:
            return
        catalog = dict(self.custom_manager.active_modules_catalog)
        if catalog:
            self.update_manager.active_modules_catalog[BRIDGE_DOMAIN] = catalog
        names = ", ".join(sorted(catalog)) if catalog else "(none)"
        print(f"[wiring] bridge: custom modules -> domain '{BRIDGE_DOMAIN}': {names}")

    def deactivate(self) -> None:
        """Drop the bridge domain (used before re-injecting after a reload)."""
        if self.update_manager is not None:
            self.update_manager.active_modules_catalog.pop(BRIDGE_DOMAIN, None)

    def reachable_names(self) -> list[str]:
        """Names of custom modules callable via execute_action(BRIDGE_DOMAIN,
        <name>, <func>, ...)."""
        if self.update_manager is None:
            return []
        return sorted(self.update_manager.active_modules_catalog.get(BRIDGE_DOMAIN, {}))

    # ------------------------------------------------------------------ summary

    def summary(self) -> str:
        names = self.reachable_names()
        return ("Custom modules reachable via execute_action"
                f"('{BRIDGE_DOMAIN}', <name>, <func>): "
                + (", ".join(names) if names else "(none)"))