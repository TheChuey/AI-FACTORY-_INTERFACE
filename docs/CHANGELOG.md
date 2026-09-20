# Changelog

All notable changes to this project. Format based on Keep a Changelog
(https://keepachangelog.com/), grouped by date.

## 2026-09-18 — Master-copy recovery

The "Updates / Interface" recovery feature was rebuilt around a single
known-good **master copy** (`current-known-good-copy/`) with overlay-restore
semantics and a guard UI, replacing the old multi-baseline dry-run flow.

### Changed — `interface/restore_manager.py`

- Rewritten to keep **one** master copy. New API: `snapshot()` (publish the
  current tree as the master), `status()` (master info + how many live files
  drift), `restore()` (overlay every master file back onto the live tree).
- Remove `snapshot_baseline()`, `diff()` and the arg-driven `restore(baseline=,
  dry_run=)`; `LEGACY_BASELINE` (old `test/` folder) removed.
- Restore semantics (overlay): differing live files are backed up first into
  `agent_monitoring/data/snapshots/pre_restore_backup/<stamp>/` then
  overwritten; master-only files are **added**; live-only files are **never
  deleted**. Docs are regenerated afterwards (`_run_docs_regeneration()`).
- `BASELINE_MANIFEST.json` is now excluded from comparisons so the master
  never reports itself as drift. Backups stay under the relocated
  `agent_monitoring/data/snapshots/pre_restore_backup/`.

### Changed — endpoints (`server/server.py`)

- `GET /api/interface/status` → `baseline` is now `RestoreManager().status()`
  (`{exists, folder, files, created, modified, modified_files, error}`).
- `POST /api/interface/snapshot` → `RestoreManager().snapshot()`.
- `POST /api/interface/restore` → real restore only, no payload; returns
  `{restored, added, backup_dir, docs_regenerated}`. Preview drift via the
  status endpoint instead of a dry-run flag.
- Dropped the unused `MANIFEST_NAME` import.

### Changed — frontend

- `dashboard/js/ui/interface-manager.js` — one **"↩ Restore to master copy"**
  button opens a warning dialog (overlay modal, Cancel / Restore now); the two
  dry-run/real buttons are gone. "❖ Snapshot" is now **"Save current state as
  master"**. Status card shows master copy freshness + drift and the master
  manifest line.
- `dashboard/js/ui/interface-indicator.js` — header dot now reads
  `baseline.modified` (new shape) instead of `baseline.drift`.
- `dashboard/js/api/api.js` — `restoreInterface()` is now payload-less
  (real restore); old `baseline/apply/dryRun` params removed.

### Changed — CLI

- `about/set_title.py` — removed the `apply`, `snapshot` and `restore`
  subcommands (they called the removed APIs). The interactive title editor and
  `create-module` remain.
- `README.md` + `docs/HOW_TO_USE.md` — recovery/how-to steps now reference the
  Settings card buttons and `/api/interface/*` instead of the removed CLI.

### Changed — master copy published

- `current-known-good-copy/` published from the current tree (94 files) with a
  fresh `BASELINE_MANIFEST.json`; it is git-ignored, so it never enters the
  repo.

The central runtime data directory moved from the project root (`data/`) into
the `agent_monitoring/` subsystem (`agent_monitoring/data/`). Every backend
logger and store reads its paths from `server/paths.py`, so changing the base
`DATA_DIR` default routed chat transcripts, `chatRecord.jsonl`, the
`toollog`, `interface_trace.log`, snapshots, exports and the RAG store to the
new home without touching individual loggers.

### Changed — path authority

- `server/paths.py` — `DATA_DIR` now defaults to
  `agent_monitoring/data` instead of project-root `data/` (docstring +
  comment updated). Explicit configuration still wins: `dataDir` /
  `dataDirWindows|Linux|Mac` in `app_settings.json` and the
  `GENESSIS_DATA_DIR` env var override the default exactly as before, so an
  existing external data folder is untouched. Everything derived
  (`CHATS_DIR`, `RECORDS_DIR`, `RAG_DB_DIR`, `CUSTOM_MODULES_DIR`,
  `TOOL_LOG_FILE`, `HISTORY_FILE`, `EXPORTS_DIR`, `LOG_FILE`) follows.
- The whole runtime tree still lives under one folder: `chatlog/`
  (transcripts + `chatRecord.jsonl`), `toollog/`, `monitoring/`,
  `rag_db/`, `exports/`, `snapshots/`, `custom_modules/`,
  `interface_archive/`, `interface_trace.log`.

### Changed — hardcoded `data/` reconcilers

- `interface/restore_manager.py` — `BACKUP_ROOT` now writes restore backups
  to `agent_monitoring/data/snapshots/pre_restore_backup/`; `EXCLUDED_TOP`
  gained `"agent_monitoring/data"` (the existing `"data"` segment rule also
  covers it) so the relocated runtime data never leaks into snapshots/restores.
- `interface/update_manager.py` — `ARCHIVE_DIR` → `agent_monitoring/data/interface_archive`.
- `interface/interface_dispatcher.py` — `TRACE_LOG_FILE` → `agent_monitoring/data/interface_trace.log`.
- `server/chat_store/logger.py` — import-failure fallback log path updated.
- `server/server.py` — legacy `/api/chat-save` escape-guard fallback updated.
- `memory/search.py` + `memory/main.py` — standalone-call fallback defaults
  updated (`agent_monitoring/data/rag_db`); the app runtime already passes
  `paths.RAG_DB_DIR`.
- `.gitignore` — explicit `agent_monitoring/data/` ignore line added.

### Migration & reconciliation

- Existing project-root `data/` contents (`chatlog/`, `snapshots/`,
  `custom_modules/`, `interface_archive/`, `interface_trace.log`) were copied
  into `agent_monitoring/data/` and the relocated `chatRecord.jsonl` is
  consistent with the transcripts after `chat_store.import_once()` (records
  reconciled, stale references pruned, no duplicates).
- `agent_monitoring/store.py` (JSONL metrics) and `backup.py` (snapshots +
  exports) verified under the relocated `monitoring/` folder; docs snapshots
  regenerated.

### Notes

- On machines with an explicit data folder (e.g. `dataDirWindows`),
  `DATA_DIR` keeps resolving to that external location - the relocation only
  changes the default.

## 2026-09-17 — Agent monitoring subsystem (`agent_monitoring/`)

A new top-level backend package records per-turn agent telemetry and exposes
it under `/api/monitoring/*`, without editing the engine or any existing
chat/tool route. Monitoring is wired in at the HTTP boundary only.

### Added — backend

- `agent_monitoring/store.py` — `MonitoringStore`: thread-safe, fail-safe
  JSONL persistence at `<dataDir>/monitoring/agent_metrics.jsonl`. Malformed
  lines are skipped on read, and a disk error never breaks the caller.
- `agent_monitoring/collector.py` — `MetricsCollector`: in-memory active
  session tracking (`turns_count`, `total_duration_ms`) plus cumulative
  system-turn math. Lock-guarded for the FastAPI threadpool.
- `agent_monitoring/backup.py` — `BackupManager`: timestamped snapshot copies
  under `<dataDir>/snapshots/monitoring/` and formatted JSON exports under
  `<dataDir>/exports/`.
- `agent_monitoring/manager.py` — `MonitoringService` facade (the sole entry
  point into the package) and the `get_monitoring_service()` process
  singleton. `safe_reset()` snapshots the log before clearing it.
- `agent_monitoring/router.py` — `APIRouter(prefix="/api/monitoring")`.
- `agent_monitoring/__init__.py` — package boundary.
- `server/server.py` — the router is mounted via `app.include_router(...)`.
  `POST /api/chat` now times `agent.think()` and records `session_start` +
  an `agent_turn` event (fail-safe: telemetry can never break a reply), and
  `POST /api/chats/end` closes the session.

### Added — API

- `GET /api/monitoring/status` — `{status, active_sessions, total_system_turns}`.
- `GET /api/monitoring/records` — every stored telemetry record.
- `POST /api/monitoring/export` — writes a JSON telemetry report to `exports/`.
- `POST /api/monitoring/reset` — snapshots the metrics log, then clears it.

### Notes

- Paths resolve through `server/paths.py` (`DATA_DIR` / `EXPORTS_DIR`), so the
  store follows the configured data folder like the rest of the app.
- In-memory session counters reset on restart; the JSONL log is the durable
  record.

## 2026-09-16 — Agent id no longer tied to the folder name

New agents could fail with `(unknown agent '<id>' - is the folder present in
agent_library/?)` when their `agent.json` `id` differed from their folder name
(e.g. folder `Feature Planner Agent/` with id `feature_planner_agent`). The
registry announced agents by their `agent.json` id, but `load_definition()`
looked up the folder by treating the id as the literal path, so the two new
agents (`feature_planner_agent`, `feature_clarifier_agent`) were listed yet
unusable in `/api/chat` and on the Settings agent cards.

### Fixed — backend

- `engine/agents/loader.py` — folder lookup is now **id-aware**:
  `agent_dir(agent_id)` first tries the literal `agent_library/<agent_id>`
  folder (fast path), then scans `agent_library/*/agent.json` and returns the
  first folder (sorted, deterministic) whose `meta["id"]` matches. Falls back
  to the literal path when nothing matches, so `save_markdown` can still
  create folders for brand-new ids. `load_definition()` uses the same
  resolver, fixing both `/api/chat` and `GET/PUT /api/agents/{id}/config`.
  Folder names with spaces / kebab-case / any case now work as long as
  `agent.json#id` is set.
- `server/server.py` — `_default_agent()` now resolves the no-`agent_id`
  chat default correctly: it reads `defaultAgentId` from
  `dashboard/config/app_settings.json` (the same value the Settings page's
  dropdown writes), then the legacy `config/settings.json` `default_agent`,
  falling back to `rag_assistant` instead of the deleted `basic_chat`.
- `dashboard/config/app_settings.json` — `defaultAgentId` updated from the
  deleted `dev_assistant` to the existing `rag_assistant`.

### Notes

- The previous demo agents (`basic_chat`, `dev_assistant`,
  `problem_discovery_agent`) were removed from `engine/agent_library/` in the
  working tree; `rag_assistant` is now the safe default.

## 2026-09-16 — Tool-usage tracker (console log monitor)

The console log monitor (`dashboard/logs.html`) now has a **Tool Usage** tab
next to **Console**: a structured, chronological feed of every tool call
agents make, with a full timestamp, the agent (id + name), model, tool name,
arguments, status and a result/error preview. Unlike the chat widget's
per-request `tool_events`, this feed is a running record that survives server
restarts.

### Added — backend

- `server/tool_log.py` — process-wide, append-only tool-usage log. Each event
  is written as one JSON line to `data/toollog/tool_usage.jsonl` (path resolved
  through `server/paths.py`, so it follows the configured dataDir like the rest
  of the chat data), AND kept in a bounded in-memory deque for live reads. The
  tail is seeded from disk once at import so a restarted server still shows
  recent history without duplicating fresh events. `append()` is thread-safe
  and fail-safe (a disk/serialization error never breaks the tool call).
  `tail(limit, tool, agent, since)` serves the feed with optional filters.
  Event shape: `{time (ISO), agentId, agentName, model, tool, args, status,
  result_preview | error, origin ("native tool_calls" | "TEXT reply")}`.
- `server/paths.py` — `TOOL_LOG_FILE` (`<dataDir>/toollog/tool_usage.jsonl`)
  and a `tool_log_file` field in `paths.about()`.
- `engine/core/agent.py` — `Agent.act()` now reports every success/error/missing
  tool call to `tool_log` via a new fail-safe `_log_tool_event()` helper (agent
  id/name + model + ISO timestamp are stamped there). `think()` passes the call
  origin through to `act()` for the `origin` field. `Agent.tool_events` (the
  chat drawer) is unchanged.
- `server/server.py` — new `GET /api/logs/tools?limit=&tool=&agent=&since=`
  endpoint returning `{events, total, captured}`, newest first.

### Added — frontend

- `dashboard/logs.html` — a `Console | Tool Usage` tab bar in the header plus
  a second `<pre>` body for the tool feed (both bodies live in the same main
  column, one visible at a time).
- `dashboard/js/classes/terminal-window-out.js` — `cleanPreview` and
  `formatArgs` are now exported for reuse by the logs page.
- `dashboard/js/logs-page.js` — polls `/api/logs/tools` every 2s alongside the
  console feed, appends only new events (chronologically), and renders each as
  `[<ISO-time>] [OK|ERR|MISS] <agent> - <tool>(<args>)` with a result/error
  preview. Pause/Clear/Copy operate on whichever tab is active.
- `dashboard/css/styles.css` — `.logs-page-tabs` / `.logs-page-tab(.active)`
  pill-toggle styles in SECTION 10.

### Testing note (incomplete — to be finished)

The live HTTP round-trip of `/api/logs/tools` was **not** completed: on this
machine port `8000` was already in use by an earlier server instance, so a
fresh boot of `server/server.py` could not bind there (the test was stopped on
purpose; the user will fix the port situation and re-run later). Everything
else was verified directly:

- `server/tool_log` appends + filters work: `tail()`, `tail(tool=...)`,
  `tail(agent=...)`, `tail(since=...)`, newest-first, no duplicates after the
  at-import seed fix.
- Full agent path verified without Ollama: `build_agent("dev_assistant")` +
  `agent.act()` (both a success and a missing-file read) produced correctly
  shaped events in the JSONL tail with agent id/name/model.
- `python -m py_compile` passes for every touched Python file.

To finish: start `server/server.py` on a free port, chat with a tool-using
agent, confirm rows appear in `data/toollog/tool_usage.jsonl`, `GET
/api/logs/tools` returns them, and the logs.html **Tool Usage** tab streams
them live.

## 2026-09-15 — Chat console output (tool logs + captured startup logs)

The tool calls an agent makes during a chat now surface in a console drawer
inside the floating chat window's MAIN BODY container (never as chat bubbles),
along with a filtered capture of the server's boot/dev output. A "Pop out"
button opens the same log stream in a standalone full-page viewer.

### Added — backend

- `server/console_log.py` — a small ring-buffer capture (500 lines) that tees
  `sys.stdout`/`sys.stderr` and installs a root-logger handler at import time.
  The uvicorn access/startup lines and every module `print()` (e.g. `[llm]`,
  `[paths]`, `[interface]`, `[wiring]`, `[custom-modules]`, `[Agent.act]`,
  `[SERVER]`) are therefore captured and served.
- `server/server.py` — new `GET /api/logs/console?limit=` endpoint returning
  `{logs, captured}`; `POST /api/chat` now also returns `tool_events`
  (the structured tool-execution log for that request).
- `engine/core/agent.py` — `Agent.tool_events` collects one entry per
  `act()` call while preserving the existing return contract and prints:
  `{time, tool, args, result_preview, status:"success"}`,
  `{time, tool, args, error, status:"error"}` and
  `{time, tool, args, status:"missing"}`.

### Added — frontend

- `dashboard/js/classes/chat-window.js` — lazy console drawer
  (`_ensureConsole`) docked below the message feed with collapse, Clear and
  Pop out controls; public `appendConsoleBlock` / `clearConsole` /
  `openConsolePage` methods, plus a `sendText(text)` method that pushes
  pre-written text through the normal send pipeline.
- Console toolbar now adds `Send to agent` (posts the console text as a user
  message via `sendConsoleToAgent`) and `Ask in input` (loads the console
  text into the composer so you can append your own query via
  `loadConsoleIntoInput`). `Pop out` opens `/static/logs.html` in its own
  independent fixed-size window (`console_logs`) instead of a new tab.
- Console drawer is now **resizable**: a `.cw-console-grip` strip sits on the
  drawer's top edge - drag it up to grow the console over the message feed
  (clamped 140px-85%, pointer-capture driven, `.cw-resizing` cursor).
- The drawer lists the active agents as **clickable chips**
  (`.cw-console-agent-chip`) in a `.cw-console-agents` strip below the
  header; the current chat agent is highlighted (`.cw-active`) and clicking a
  chip switches the chat to that agent (wired through
  `setConsoleAgents` / `setActiveConsoleAgent` / `onConsoleAgent`). The
  collapsed header shows a `· N agents` badge. The drawer is created on load
  (collapsed) and still auto-expands when the first logs arrive.
- The flyout widget is wider by default (`--cw-widget-width` = 920px instead
  of 380px in flyout mode), so the console reads comfortably; the small-screen
  full-screen fallback is unchanged.
- Console size presets now default taller: `Large` is 75% of the window body
  (was 60%) and `Compact` 60% (was 45%), so a full batch of log lines fits in
  `.cw-console-body` without scrolling; the un-configured CSS fallback matches
  at 75%. The drag grip still lets you pull it up to ~97%.
- The pop-out viewer (`/static/logs.html`) now uses larger text: it sets
  `--cw-console-font-size` pre-paint from the saved Appearance console-size
  preset (14px large / 12.5px compact) and its fallback is 14px instead of
  12px, so logs opened in the pop-out window read as big as in the drawer.
- Console log text no longer looks washed out on the dark background: the
  `.cw-console-body` color is brightened from `#b6c2cf` to `#e6edf3` (~14:1
  contrast), the CONSOLE OUTPUT toggle label, agent chips, and the whole
  pop-out page (`logs.html` body + `.logs-page-body`) were brightened to the
  same readable greys. The console log text itself is now `#ffffff`.
- Fixed the chat composer input showing BLACK text on the dark background
  (form controls don't inherit `color`, so `.cw-input` fell back to the
  browser default): `.cw-input` now sets `color` + `caret-color` to
  `var(--color-text)` and `.cw-input::placeholder` to `var(--color-text-soft)`,
  so typed text stays readable in both themes.
- The chat window header now has a **Fill the window** button (between the
  side-panel/Observe buttons and Minimize). It expands the chat to cover the
  whole browser viewport (`.cw-fullscreen`, inset 0 / 100vw / 100vh, no
  border-radius, above the regular z-index) and back. Works in both flyout
  and panel modes; Esc restores; header-drag, edge-resize and
  keep-in-viewport are all disabled while maximized; Minimize and Close
  restore first, and a fresh open always starts non-fullscreen.
- `dashboard/js/ui/appearance.js` — the Appearance config (the existing base
  font-size "size" feature) gains a 2-option **Console size** level (`compact`
  45%/12.5px, `large` 60%/14px, default `large`), persisted via
  `appearance.consoleSize` and applied to `--cw-console-height` /
  `--cw-console-font-size` - so the drawer (and matched logs page) resize per
  system without editing CSS.
- `dashboard/js/classes/terminal-window-out.js` — decoupled log
  formatting/filtering: `pushToolLogs(chat, toolEvents)`,
  `pushStartupLogs(chat, logs)` and the shared `filterConsoleLines()`.
- `dashboard/js/api/api.js` — `sendChat` returns `tool_events`; new
  `getConsoleLogs(limit)`.
- `dashboard/js/app.js` — boots by pushing captured startup logs into the
  chat window's console drawer (fail-soft), and pushes tool logs after every
  send.
- `dashboard/logs.html` + `dashboard/js/logs-page.js` — standalone pop-out
  terminal viewer: polls `/api/logs/console` every 2s, pause / clear / copy,
  and applies the same `filterConsoleLines()` so the drawer and the page
  agree on what counts as noise.
- `dashboard/css/styles.css` — console drawer styles in SECTION 8 and a new
  SECTION 10 for the standalone console page (both keep an always-dark
  terminal look in light and dark themes).

### Behavior notes

- The drawer stays collapsed until content arrives, so ordinary chats are
  visually unchanged; the "Clear" button clears the drawer, "Pop out" opens
  `/static/logs.html`. The widget drain toggle resets each session.
- Terminal ANSI color codes from uvicorn's colored log lines are stripped at
  capture time (`server/console_log.py`) and again defensively in
  `filterConsoleLines()`, so the drawer and logs page always render plain
  text (and `INFO:`/access lines still qualify as filterable noise even when
  a server captured them with escape prefixes).

### Verified

- `python -m py_compile` clean on `engine/core/agent.py`, `server/server.py`,
  `server/console_log.py`; `node --check` clean on `dashboard/js/app.js`,
  `dashboard/js/api/api.js`, `dashboard/js/classes/chat-window.js`,
  `dashboard/js/classes/terminal-window-out.js`, `dashboard/js/logs-page.js`.
- TestClient smoke test: `GET /api/logs/console` returns the captured boot
  lines, and an Agent with fake tools records success / error / missing
  `tool_events`.

## 2026-09-15 — Dynamic module UI actions + developer guide

The drop-in custom module system (Phase 1/2/3) grew from a single
`prompt_input` button into four full UI action types, backed by a new
copy-paste developer guide. A module's `UI_MANIFEST["buttons"]` can now open a
schema-driven modal, a multi-step Q&A wizard, or a dropdown of sub-actions, and
any executor can light a green status-dot when it succeeds.

### Added — UI action types (frontend)

- `dropdown_menu` — `dashboard/js/ui/header-nav.js`: a manifest button with
  `action: "dropdown_menu"` renders a flyout whose `items[]` are handed to the
  same click handler (each item can be any of the action types). One delegated
  `document` listener closes any open menu on an outside click; the status dot
  attaches to the parent button.
- `open_modal` — `dashboard/js/app.js` fetches `schema_endpoint` (a JSON schema
  of `input` / `select` / `checkbox` / `button` components) and builds a modal
  form; on submit it POSTs the filled values to `schema.target_endpoint`.
- `qa_survey` — a step-by-step wizard modal that POSTs `{step, answers}` to
  `qa_endpoint` until the server returns `completed: true` (an optional
  `record_path` is shown in the modal). Answers are keyed `step_1`, `step_2`, …
- `status_dot` — any executed action whose response includes
  `indicate_success: true` gets a green `.status-dot` appended to its trigger
  button.
- `dashboard/js/app.js` — new shared `openModal(title, builderFn)` helper
  (overlay card + close), and the `renderDynamicHeaderButtons` callback now
  receives `(btnConfig, parentBtn)`. `prompt_input` now POSTs `{"input": ...}`
  (generically, so any module route can read `payload.get("input")`;
  `project_name` is still accepted for compatibility).
- `dashboard/css/styles.css` — SECTION 9: header dropdown, modal overlay/card
  and `.status-dot` styles (reuses the `--shadow-modal` variable).

### Added — docs

- `docs/CUSTOM_MODULE_DEV_GUIDE.md` — full developer guide: the
  browser ↔ server ↔ module pipeline, module lifecycle, a minimal working
  module, all four action types with runnable backend code, dict-vs-pydantic
  endpoints, the `interface/wiring/` bridge (`execute_action("custom", ...)`),
  a frontend file map, curl + TestClient testing, troubleshooting and a quick
  reference. `README.md` and `docs/HOW_TO_USE.md` link to it, and README's
  custom-modules section now lists the button action types.

### Reference implementations

- `interactive_manager.py` and `project_manager.py` in the Custom Modules Path
  (`E:\data\moduels` on this machine) demonstrate all four action types end to
  end, including the Q&A record saver.

### Verified

- `python -m py_compile` clean on `server/server.py`, `server/paths.py`,
  `about/set_title.py`, `interface/custom_module_manager.py` and
  `interface/wiring/*.py`; `node --check` clean on `dashboard/js/app.js` and
  `dashboard/js/ui/header-nav.js`.

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