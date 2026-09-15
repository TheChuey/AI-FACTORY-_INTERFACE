# Changelog

All notable changes to this project. Format based on Keep a Changelog
(https://keepachangelog.com/), grouped by date.

## 2026-09-13 — Phase 1/2/3: drop-in custom modules (Dynamic External Module Loader)

Installed the three-phase "drop a `.py` file in and it just works" extension
system, following `phase-1-2-3-update/INSTRUCTIONS.md`. You can now drop a
standalone `.py` module into **Custom Modules Path** (default
`data/custom_modules/`) and — after a restart, or a live apply — it gets a
header button on the dashboard plus its own FastAPI routes, with **no manual
editing** of `index.html`, `header-nav.js`, or `server.py`.

This is a **second, independent** loader from the existing
`interface/update_manager.py` domain system (`interface/updates/<domain>/`).
The two managers never talk to each other, so nothing already built was
touched or can break.

### Added — new file

- `interface/custom_module_manager.py` — `CustomModuleManager` scans the flat
  `CUSTOM_MODULES_DIR` folder for `*.py` files (skipping `_`/`.`-prefixed
  helpers), imports each standalone file with `importlib.util` (they are not a
  Python package), and exposes `active_modules_catalog`, `reload_all()`,
  `get_active_module(name)`, `list_modules()` and `ui_manifests()`. A module
  with a broken import is logged and skipped — one bad drop-in file never
  blocks boot. Also provides the process-wide `get_custom_module_manager()`
  singleton.

### Added — `server/paths.py`

- `customModulesPath` setting key (Settings → App defaults → **Custom Modules
  Path**), with `GENESSIS_CUSTOM_MODULES_PATH` env-var override, resolved the
  same way `dataDir` / `ragDbPath` already are (relative → project root,
  absolute → used as-is, blank → `<dataDir>/custom_modules`). Exposed as
  `CUSTOM_MODULES_PATH` / `CUSTOM_MODULES_DIR`; `about()` now reports
  `custom_modules_dir` and its `sources` map. `data/custom_modules/` is
  created automatically on first boot.

### Added — `server/server.py`

- `lifespan()` creates a `CustomModuleManager`, prints the active catalog, and
  calls each active module's `register_routes(app)`; a broken module can never
  block boot (warns and sets `app.state.custom_module_manager = None`).
- `_register_custom_routes(manager)` + the `_CUSTOM_ROUTES_REGISTERED` set —
  routes are registered at most once per process, so
  `POST /api/interface/apply` can pick up brand-new modules **live** without
  double-registering old ones (edits to an already-loaded module's route logic
  still need a real restart).
- `GET /api/interface/status` now also returns `custom_modules` (resolved
  folder + active names) and `ui_manifests` (every active module's
  `UI_MANIFEST`, used by the frontend to render header buttons).

### Added — CLI (`about/set_title.py`)

- `python about/set_title.py create-module <name>` — scaffolds a drop-in
  module pre-wired with a `UI_MANIFEST` and `register_routes(app)` (writes to
  Custom Modules Path, default `data/custom_modules/<name>.py`). Validates the
  name (letters / numbers / `-` / `_`), refuses to overwrite existing files,
  and prints activate instructions.
- `apply` now prints a `CustomModuleManager.summary()` catalog line (new
  modules go live via `apply`, edits to loaded ones need a restart).

### Added — frontend (`dashboard/`)

- `js/ui/header-nav.js` — new export `renderDynamicHeaderButtons(container,
  onClick)`: fetches `/api/interface/status`, reads `ui_manifests`, and appends
  one button per manifest entry (id-deduplicated). Fail-soft — renders nothing
  on a server with no custom modules.
- `js/app.js` — calls `renderDynamicHeaderButtons` right after mounting the
  normal nav row; a click follows the `action: "prompt_input"` contract
  (prompt via `prompt_message`, POST to `api_endpoint`, alert the response).
- `js/ui/config-form.js` — "Custom Modules Path" text field on the Settings
  page, persisted through the existing generic `saveAppSettings()` merge; path
  changes apply after a restart (the existing "restart needed" banner).

### Using it

```bash
python about/set_title.py create-module analytics_builder   # scaffold one
python server.py                                            # restart to activate
# or, without restarting: python about/set_title.py apply
```

Reload the dashboard — the "＋ Analytics Builder" button appears in the header
automatically and POSTs to the module's endpoint on click.

### Verified

- `python -m py_compile` clean on the 4 changed/new Python files; `node
  --check` clean on the 3 changed JS files.
- `CustomModuleManager` imports cleanly (empty folder → zero active modules).

## 2026-09-12 — Cross-platform paths (Windows/Linux/macOS) + save feedback

The app now runs from the same checkout on Windows, Linux, macOS and the
ChromeOS Linux container, and where data is saved can be changed without
editing a file. (A merge combined a Windows-side `GENESSIS_*` env-var approach
with the Chromebook-side per-OS-key approach, so both are supported.)

### Added — portable path resolution (`server/paths.py`)

- **Per-OS path keys** in `dashboard/config/app_settings.json`: one settings
  file can carry three layouts — the plain `dataDir` / `chatSavePath` /
  `ragDbPath` plus `dataDirWindows` / `dataDirLinux` / `dataDirMac` (and the
  matching chat/rag variants). The key for the CURRENT machine wins; keys for
  OSes you do not use are left alone. Relative -> project root; absolute ->
  used as-is; empty -> default.
- **Env-var overrides** (highest precedence): `GENESSIS_DATA_DIR`,
  `GENESSIS_CHAT_SAVE_PATH`, `GENESSIS_RAG_DB_PATH` override the stored
  settings; `~` and `$VAR` are expanded, so `~/genessis-data` works.
  Precedence chain: env var -> per-OS key -> plain key -> project-relative
  `data/`.
- **Windows drive-path guard**: a Windows absolute path (`E:\...`, `E:/...`,
  `\\server\share`) in the plain key is ignored on non-Windows hosts when no
  per-OS key is set — the app falls back to a project default instead of
  creating a literal `E:\...` folder on Linux/macOS. `server.py`'s legacy
  `/api/chat-save` resolver uses the same guard.
- `platform()` now reports `win` / `linux` / `mac`; `about()` gained a
  `sources` map telling which key or env var resolved each setting. Stray
  `E:\data\rag_store` folders created by old resolutions were removed.
- `.gitignore` — `[A-Z]:*` rule so accidental drive-letter folders can never
  be tracked.

### Added — resilient model selection

- `engine/core/llm.py` — `_resolve_model()`: an uninstalled requested model is
  dropped with an `[ask_llm]` warning and the first detected model is used
  instead; tool-calling agents prefer a tools-capable detected model;
  per-model capabilities are cached briefly; an explicit request is still
  honoured when no models are visible.
- `dashboard/config/app_settings.json` — `defaultModel` is `""` (resolves to
  the first detected model; the user picks from the dropdown).

### Changed — save flow + startup visibility

- `server/server.py` — `GET /api/settings` returns `platform`; save merges
  without rewriting path values; `lifespan()` prints the resolved data / chat
  records / RAG folders at boot and flags env-overridden keys.
- `dashboard/js/ui/config-form.js` — an always-visible **per-OS paths** section
  (Windows / Linux / macOS inputs for Data folder, Chat save path and RAG
  database) with the current platform's row highlighted. `config-page.js` /
  `api.js` pass the detected platform through.
- `dashboard/js/config-page.js` — save shows a green **"Settings saved"**
  response window with a restart hint when stored paths changed since boot.
  `dashboard/config.html` gained the `.save-response` styles.

### Changed — docs

- `README.md` — "Running on Linux / macOS / ChromeOS (Chromebook)" quickstart,
  "Changing where data is saved" (per-OS keys vs env vars vs defaults) and
  "Model selection" sections; folder tree updated (`js/ui/` added, `test/`
  removed); the deleted `docs/documentation_CREATING_AGENTS.md` link replaced;
  "Recent changes" points at the current entry.
- `docs/RESTRUCTURE_README.md` — `test/` + the deleted agent-authoring doc
  removed from the tree; portable-`paths.py` note added under "Launching".

### Verified

- Path unit tests (forged Linux/macOS semantics): drive/UNC detection;
  per-OS key selection; env override wins over stored settings; `$HOME`/`~`
  expansion; `about()["sources"]` populated.
- `/api/settings` returns `{settings, restartNeeded, platform}` and merges
  cleanly.
- uvicorn boot with `GENESSIS_DATA_DIR` set to a temp folder: boot log shows
  data/records/rag under the override; `/api/rag/status` 200.

## 2026-09-12 — AI-readable app snapshot docs

The whole app is readable as two auto-generated markdown files an AI can
ingest: `docs/APP_STRUCTURE.md` (file/folder tree) and
`docs/APP_CODE_SNAPSHOT.md` (every source file's name and full contents).
Both are produced by `scripts/update_docs.py`; refresh them after any
meaningful change with `venv/bin/python scripts/update_docs.py` (the walk
skips `test/`, `venv/`, `.git/`, `data/`, `__pycache__/` and `*.bak`/`*.pyc`
so the snapshot spans only the running app).

## 2026-09-12 — Frontend wiring for the interface system + title propagation

The Modular Interface / update system is now reachable from the browser.
New `server/server.py` endpoints power a Settings card, a header pill shows
module activity, and the about.json title/tagline is propagated to the
browser tab on every page.

### Added — `/api/interface/*` endpoints (`server/server.py`)

- `GET /api/interface/status` — live module catalog (per domain), external
  archive contents, trace-log tail (`data/interface_trace.log`, last 20
  lines), and baseline info: folder, `BASELINE_MANIFEST.json` metadata and a
  live **drift count** (SHA-256 diff vs `current-known-good-copy/`).
- `POST /api/interface/apply` — `reload_all()` the update modules, then
  regenerate `docs/APP_STRUCTURE.md` + `docs/APP_CODE_SNAPSHOT.md`.
- `POST /api/interface/snapshot` — publish the current tree as the new
  baseline (rebaseline via `RestoreManager.snapshot_baseline()`).
- `POST /api/interface/restore` — `{baseline?, apply?, dryRun?}`; **dry-run by
  default**. A real restore backs up overwritten files to
  `data/snapshots/pre_restore_backup/` before rolling back, then regenerates
  the docs.
- `POST /api/interface/run` — `{domain, module, function, args?, kwargs?}`
  through `InterfaceDispatcher.execute_action()`. Arbitrary code execution;
  **disabled by default** and gated server-side by `INTERFACE_RUN_ENABLED`.
  Flipped with:
- `POST /api/interface/toggle-run` — `{enabled}` arms/disarms `/run` for the
  current process (logged to `data/interface_trace.log`).
- `RestoreManager.diff(baseline)` — silent SHA-256 comparison returning
  `{baseline, shared, modified, skipped, untracked}`; `restore()` and the
  status endpoint share it (no more double file-map builds).
- `about/set_title.py apply --snapshot` now snapshots AFTER the docs
  regeneration (was reversed, so the baseline captured stale docs and
  `restore --dry-run` reported the two doc files as modified).

### Added — frontend (`dashboard/`)

- `js/api/api.js` — `getInterfaceStatus`, `applyInterface`,
  `snapshotInterface`, `restoreInterface`, `runInterface`, `setRunEnabled`.
- `js/ui/interface-manager.js` — the "Updates / Interface" card on the
  Settings page (below Models): module catalog, archive, baseline freshness +
  drift, trace-log tail, Apply / Snapshot / Restore (dry-run) / Restore
  (real) buttons, and an **opt-in "Enable module execution" gated** run-module
  panel (function name + JSON args/kwargs) mirroring `run_enabled` from the
  server.
- `js/ui/interface-indicator.js` — quiet "N updates" header pill (green dot,
  amber when the baseline drifts, "\u2022 on" when run is armed); hidden on
  servers without `/api/interface/*`; links to `config.html#interface-section`.
  Rendered on `index.html` and `config.html`.
- `config.html` — `#interface-section` mount + local card styles.
- Title propagation: `app.js#setPageTitle()` now sets `document.title`
  (`<title> – <subtitle>`); `config-page.js` boot fetches `/api/about` for the
  tab title; `chat.html` fetches `/api/about` and shows a small site chip
  (`#sc-site-title`) in its header plus the tab title.

### Verified

- `py_compile` clean on `server/server.py` and `interface/restore_manager.py`.
- TestClient: `/api/interface/status` 200 (catalog, drift); `/run` denied with
  403 while disabled; `toggle-run` on -> `secondary_engine_action(5)` == `50`
  (traced); bad function -> 500; `apply` reloaded `engine=2` + regenerated
  docs; `restore` dry-run reported the expected modified files. All six pages
  endpoints serve 200.

## 2026-09-12 — 02 implementation plan folded in; server startup wiring

Follow-up to the Modular Interface build, based on the 02 implementation plan
(`docs/02_IMPLEMENTATION_PLAN.md`, later folded in and removed). The plan's
missing pieces were folded into the existing
implementation instead of a verbatim overwrite, preserving the earlier choices
(`current-known-good-copy/` baseline, `--dry-run`, `snapshot` command, safer
exclusions). The plan's Linux path (`venv/bin/python`) is `venv\Scripts\python.exe`
on this Windows project.

### Added

- `interface/updates/engine/newfunction.py` — sample engine update module
  (`execute_new_logic()` / `secondary_engine_action()`), the 02-plan Step 6
  example. `hello_update.py` is kept alongside.
- `update_manager.discover_all_active_modules()` — alias for `reload_all()`
  (clear catalog, drop cached modules, re-import from disk).
- `update_manager.list_domain_modules(domain)` — sorted module names per domain.
- `interface_dispatcher.execute_action(domain, module, function, *args)` —
  resolve a module by name through the update manager and run it traced;
  raises `ModuleNotFoundError` for unknown modules.
- Trace logging now also goes through the `app_change_tracker` logger with a
  `FileHandler` on `data/interface_trace.log` (02-plan Step 3); stdout print
  kept.

### Changed — server startup (02-plan Step 7)

- `server/server.py` — `lifespan()` now builds `UpdateManager`, runs
  `discover_all_active_modules()`, builds `InterfaceDispatcher`, and exposes
  both on `app.state` (`app.state.update_manager`,
  `app.state.interface_dispatcher`). Discovery failures print a warning and
  leave the state `None` so a broken update module never blocks server boot.

## 2026-09-12 — Modular Interface & System Update Architecture

Introduced a pluggable update/restore layer so new features never touch core
modules again. Design reference: see **`README.md`** ("Modular interface") and
this changelog — the original design doc
(`docs/01_IDEA_AND_ARCHITECTURE.md`) was folded in and removed.

### Added — `interface/` package

- `interface/update_manager.py` (`UpdateManager`) — dynamically discovers and
  imports every `.py` under `interface/updates/<domain>/` (`engine/`,
  `tools/`, `server/`), keeps live module objects in `active_modules_catalog`,
  and exposes `get_active_module(domain, module)` for direct native execution.
  `move_module_to_external_archive(domain, module)` relocates retired update
  modules to `data/interface_archive/<domain>/`.
- `interface/interface_dispatcher.py` (`InterfaceDispatcher`) —
  `trace_and_execute(fn, *args)` logs the caller file + line number
  (via `inspect`) before running a module function, to
  `data/interface_trace.log`.
- `interface/restore_manager.py` (`RestoreManager`) — SHA-256 baseline
  comparison (`current-known-good-copy/` by default, `test/` fallback),
  `snapshot_baseline()` to publish a complete working copy of the last good
  source, and `restore()` which backs up every overwritten file to
  `data/snapshots/pre_restore_backup/<timestamp>/` before rolling back and
  then regenerates the docs snapshots. Restore semantics: only files present
  in BOTH trees whose checksum differs are overwritten; baseline-only and
  live-only files are reported but left untouched. User data is excluded
  (`data/`, `venv/`, `.git/`, `__pycache__/`, `current-known-good-copy/`,
  `test/`, `dashboard/config/app_settings.json`, `about/about.json`,
  `*.bak`, `*.pyc`).
- `interface/updates/` — seeded with `engine/`, `tools/`, `server/` domains
  and one example module (`engine/hello_update.py`: `run_example()` /
  `double()`).

### Added — documentation snapshots

- `scripts/update_docs.py` — regenerates `docs/APP_STRUCTURE.md` (folder-tree
  snapshot) and `docs/APP_CODE_SNAPSHOT.md` (per-file source snapshot; never
  embeds itself). Runs automatically on `apply` and after `restore`.

### Changed — CLI

- `about/set_title.py` now dispatches `apply`, `snapshot` and `restore`:
  - `python about/set_title.py apply [--snapshot]` — reload all active update
    modules (+ publish the baseline when `--snapshot` is passed), then
    regenerate the docs snapshots.
  - `python about/set_title.py snapshot [folder]` — publish the current tree
    into `current-known-good-copy/` (the default restore baseline).
  - `python about/set_title.py restore [baseline] [--dry-run]` — compare the
    live tree against the baseline, back up + restore modified files, and
    regenerate the docs snapshots.
  - no args still edits about.json interactively / positionally.

### Verified

- `python -m py_compile` passes on every new/changed module.
- `apply` discovered + imported `engine/hello_update` and generated both docs
  snapshots.
- Option B access returned live module: `run_example()` and `double(21) == 42`.
- `trace_and_execute()` logged the caller (`file:line -> module.function`) to
  `data/interface_trace.log`.
- `move_module_to_external_archive()` moved the example to
  `data/interface_archive/engine/` and refreshed the catalog.
- A real restore: tampered `docs/APP_STRUCTURE.md` was detected (1 modified),
  backed up to `data/snapshots/pre_restore_backup/<timestamp>/`, rolled back
  from the baseline, and both docs snapshots were regenerated. A fresh
  baseline yields `modified: 0` on `restore --dry-run`.
- Exclusions confirmed: no `.git/`, `data/`, or `venv/` content leaks into the
  generated snapshots.

### Changed — other

- `current-known-good-copy/` added to `.gitignore` (generated baseline copy;
  `data/` was already ignored).

## 2026-09-12 — Agent Monitor removed; launch fixed; docs updated

The Agent Monitoring feature (live activity feed) was removed and the affected
backend modules were restored to their original, working versions. Chats are
fully functional again.

### Removed — Agent Monitor (frontend)

The monitor was a companion window that polled a live activity feed while an
agent worked. It is gone entirely:

- `dashboard/monitor.html` — deleted (the monitor page).
- `dashboard/js/monitor.js` — deleted (polling loop + rendering).
- `dashboard/js/api/api.js` — `getActivity()` / `clearActivity()` removed
  (they called `/api/activity` and `/api/activity/clear`).
- `dashboard/chat.html` — the "Monitor" header button and its click listener
  removed.
- `dashboard/js/app.js` — `openAgentMonitor()` and the `config.onObserve`
  wiring removed.
- `dashboard/config.html` + `dashboard/js/config-page.js` — the "Agent
  Monitor" settings section (`#monitor-section`, `renderMonitorSection()`)
  removed.
- `server/__pycache__/activity.cpython-314.pyc` — stale bytecode cleaned.

Note: `dashboard/js/classes/chat-window.js` still has a generic `onObserve`
extension hook, but nothing sets it, so it never triggers.

### Removed — Agent Monitor (backend)

- `server/activity.py` — deleted (the ActivityFeed singleton + `/api/activity`
  endpoints no longer exist, so the poller 404s are gone).

### Restored — backend modules rolled back to working originals

- `engine/core/agent.py` — restored from the original; the monitor-era
  sink/events/`_emit`/`_clip_args` and stdout-capturing `act()` are gone.
  `think()` / `act()` / `observe()` behave as before.
- `server/server.py` — restored from the original base and the legitimate
  pre-monitor endpoints re-added so the Settings page keeps working:
  - `GET /api/tools`
  - `GET /api/agents/{agent_id}/config`
  - `PUT /api/agents/{agent_id}/config`
  - `GET /api/about`

Pre-rollback copies are kept as recovery backups:
`server/server.py.infected.bak` and `engine/core/agent.py.infected.bak`.

### Fixed — launching `server.py` from any directory

`server/server.py` now bootstraps `sys.path` at the top: it inserts the
project root and drops its own folder from the path so this file can never
shadow the `server/` package. Previously `python server.py` failed with
`ModuleNotFoundError: No module named 'engine'` (and the `server`/`server.py`
name collision made a simple path fix impossible).

Now all three of these work:
`python server.py` (from `server/`), `python server/server.py` (from the
project root), and `venv\Scripts\python -m uvicorn server.server:app` (root).

### Changed — documentation

- `README.md` — rewritten to match the current layout (`engine/`, `server/`,
  `tools/`, `memory/`, `dashboard/`, ...), with a module-by-module inventory,
  up-to-date API table and launch instructions.
- `docs/RESTRUCTURE_README.md` — folder tree refreshed, monitor removal and
  launch-anywhere noted.