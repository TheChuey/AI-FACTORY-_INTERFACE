# GenV1 — Interface, Update & Restore Architecture

> **Location:** `docs/architecture/INTERFACE.md`
> **Next:** `docs/architecture/MEMORY.md` · **Prev:** `docs/architecture/TOOLS.md`

## Purpose

Describe the modular interface layer: update modules, the traced dispatcher,
the restore/master-copy manager, drop-in custom modules, and the wiring bridge
that connects the two.

## Responsibilities

- Discover/import update modules from `interface/updates/<domain>/`.
- Execute module functions with caller tracing to
  `<dataDir>/interface_trace.log`.
- Publish, inspect and restore from one **master copy**
  (`current-known-good-copy/`) with overlay-restore semantics.
- Load standalone `.py` custom modules from the Custom Modules Path and register
  their FastAPI routes.
- Bridge custom modules into the update catalog under the virtual `custom`
  domain.

## Does Not Own

- The agent runtime (`engine/`), the tools (`tools/`), or the frontend.
- User data (restore never touches runtime data folders).

## Components

- `interface/update_manager.py` — `UpdateManager`: catalog, discovery,
  `get_active_module`, `move_module_to_external_archive`.
- `interface/interface_dispatcher.py` — `InterfaceDispatcher`:
  `trace_and_execute()`, `execute_action(domain, module, function, ...)`.
- `interface/restore_manager.py` — `RestoreManager`: `snapshot()` / `status()` /
  `restore()`; SHA-256 diff; pre-restore backups.
- `interface/custom_module_manager.py` — `CustomModuleManager`:
  flat-folder `.py` loader, `active_modules_catalog`, `reload_all()`,
  `ui_manifests()`.
- `interface/wiring/bridges.py` — `CustomModuleBridge`: route registration +
  `custom` domain bridge; `wiring.rewire(app)` re-asserts after reload.
- `interface/updates/{engine,tools,server}/` — active update module domains.

## Inputs

- Files under `interface/updates/<domain>/` and the Custom Modules Path.
- `/api/interface/*` requests from the Settings "Updates / Interface" card.

## Processing

- At boot (`lifespan`): build `UpdateManager`, run discovery, build
  `InterfaceDispatcher`, create `CustomModuleManager`, wire via
  `interface/wiring/`. Fail-soft on broken modules.
- `apply` reloads both loaders, re-wires the bridge, then regenerates the docs
  snapshots.
- `snapshot` publishes the live tree as the master copy.
- `restore` backs up differing files to
  `<dataDir>/snapshots/pre_restore_backup/<stamp>/`, overwrites them from the
  master, adds master-only files, never deletes live-only files, excludates
  runtime data and user settings, then regenerates docs.
- `/api/interface/run` executes an update-module function — **disabled by
  default** (`INTERFACE_RUN_ENABLED`); avoid arbitrary execution.

## Outputs

- `GET /api/interface/status` payload; regenerated docs snapshots; trace log
  entries; restore results.

## Dependencies

- `server/server.py` (wiring + endpoints), `server/paths.py` (archive/custom
  folders), `scripts/update_docs.py` (post-restore regeneration).

## Consumers

- The Settings page Updates/Interface card; the header indicator pill; core
  code calling `execute_action`.

## Extension Points

- **Update modules**: drop `.py` in `interface/updates/<domain>/`.
- **Custom modules**: drop a `UI_MANIFEST` + `register_routes(app)` module into
  the Custom Modules Path; scaffold with `python about/set_title.py
  create-module <name>`.
- **Bridge usage**: `InterfaceDispatcher().execute_action("custom", "<name>",
  "<func>", ...)`.

## Rules

- Custom-module routes register at most once per process (`_REGISTERED`);
  brand-new modules go live via `apply`, edits to loaded modules need a real
  restart.
- The two loaders (update vs custom) stay separate; the bridge is re-injected
  after every reload.
- Restore semantics: master-only files added, live-only files preserved,
  user data (`agent_monitoring/data/`, `venv/`, `.git/`, `app_settings.json`,
  `about.json`) never touched.

## Failure Behavior

- A broken module import is logged and skipped — one bad file never blocks
  boot (`app.state.custom_module_manager = None`).
- `apply` reload failure → 500 with diagnostic.

## Runtime Flow

```text
Apply/Restart
  -> UpdateManager.reload_all() / CustomModuleManager.reload_all()
  -> bridges.register_routes(app)            (once per process)
  -> bridges.activate()                      (mirror into 'custom' domain)
  -> /api/interface/status serves catalog + manifests + baseline
Save current state as master
  -> RestoreManager.snapshot()               publish current-known-good-copy/
Restore to master copy
  -> RestoreManager.restore()                backup + overlay + docs regen
```

## Configuration

- `customModulesPath` setting / `GENESSIS_CUSTOM_MODULES_PATH` env var.
- `INTERFACE_RUN_ENABLED` toggle via `/api/interface/toggle-run`.

## APIs

- `GET /api/interface/status`
- `POST /api/interface/apply`
- `POST /api/interface/snapshot`
- `POST /api/interface/restore`
- `POST /api/interface/run`
- `POST /api/interface/toggle-run`

## Source Files

```text
interface/update_manager.py
interface/interface_dispatcher.py
interface/restore_manager.py
interface/custom_module_manager.py
interface/wiring/__init__.py
interface/wiring/bridges.py
interface/updates/{engine,tools,server}/
```

## Related Documentation

- `docs/development/CUSTOM_MODULES.md`
- `docs/reference/MODULE_REFERENCE.md`
- `docs/reference/API.md`
- `docs/living/CHANGELOG.md` (master-copy recovery, drop-in modules)