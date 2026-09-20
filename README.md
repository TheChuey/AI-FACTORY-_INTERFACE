# Terminator1 (Genessis)

A local lab for building and testing AI agents: **FastAPI** backend + vanilla JS
frontend + **Ollama** local LLMs.

The core idea:

```
Agent      = one reusable Python runtime (think / act / observe)
Markdown   = behavior        (engine/agent_library/*/agent.md)
JSON       = configuration   (engine/agent_library/*/agent.json)
Tools      = capabilities    (tools/, wired by ID)
Registry   = discovery       (engine/agent_library/ is scanned automatically)
Factory    = construction    (agent_id -> ready Agent)
Frontend   = selection       (GET /api/agents -> agent selector)
```

You can build 10, 20, or 100 agents without ever writing a new Python class:
a new agent is just a folder with `agent.md` + `agent.json` (+ tool IDs).

## One place for configuration

Open **/static/config.html** (the "Settings" button on the dashboard and in the
chat header) for EVERY configuration in one screen:

- **App defaults** — default agent (with a jump-link to that agent's card),
  default model, chat save path, data folder, RAG database path, chat
  versioning, and the RAG memory defaults. Stored in
  `dashboard/config/app_settings.json`.
- **Appearance** — one theme + font set for all pages.
- **Agents** — one card per agent, consolidating its whole config in one place:
  metadata + model + tools (its `agent.json`), its behavior prose (editable
  `agent.md`), and that agent's chat tests + an inline runner.
- **Shared tests** — tests with no agent that run for every agent.
- **Models** — read-only snapshot of the installed Ollama models.

Per-agent data lives with the agent (`engine/agent_library/<id>/agent.json` now
holds `tests`; `agent.md` is the behavior). The default agent for `/api/chat`
is read from the same `defaultAgentId` the dashboard uses.

## Quickstart (Windows PowerShell)

```powershell
py -3 -m venv venv
venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python server.py
```

## Quickstart (Linux / Chromebook Linux)

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
python server.py
```

`python server.py` can be run from ANY directory — the project root or
`server/` both work (the file bootstraps `sys.path` itself). Override the port
with `$env:PORT=9000` (PowerShell) or `PORT=9000 python server.py` (Linux).
The equivalent uvicorn launch (from the project root):

```powershell
venv\Scripts\python -m uvicorn server.server:app --host 127.0.0.1 --port 8000
```

Linux uses the same package layout in the venv, so the equivalent is:

```bash
venv/bin/python -m uvicorn server.server:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000** (Chrome/Edge).

## Running on Linux / macOS / ChromeOS (Chromebook)

The app is cross-platform - the same folder runs on Windows, Linux and macOS.
On a Chromebook, use the **Linux container** (`Settings -> Developers -> Linux
development environment`), then install Python and the venv module once:

```sh
sudo apt update && sudo apt install -y python3 python3-venv python3-pip
```

Then, in the project folder:

```sh
python3 -m venv venv
source venv/bin/activate          # Linux/macOS (Windows: venv\Scripts\Activate.ps1)
python -m pip install -r requirements.txt
python server.py
```

That is it - no path configuration is required. By default everything is saved
under the project's own `data/` folder (chat transcripts, the chat log, the RAG
store, exports, history). If you need Ollama too, follow its Linux install
(`curl -fsSL https://ollama.com/install.sh | sh` on Linux/Chromebook).

> Tip: `python server.py` can be started from ANY directory - it bootstraps
> `sys.path` itself. Port override: `PORT=9000 python server.py` (Unix) or
> `$env:PORT=9000; python server.py` (PowerShell).

## Changing where data is saved

All runtime storage (chat transcripts, the chat log, history, exports and the
RAG store) is controlled by **three path settings** resolved by
`server/paths.py`: `dataDir`, `chatSavePath`, `ragDbPath`. From highest to
lowest precedence:

1. **Environment variables** - the most portable option for a second machine /
   Chromebook. Set them before launching (e.g. in `~/.bashrc` or a `run.sh`):

   ```sh
   export GENESSIS_DATA_DIR="$HOME/genessis-data"        # instead of /dataDir
   export GENESSIS_CHAT_SAVE_PATH="$HOME/genessis-chats" # instead of /chatSavePath
   export GENESSIS_RAG_DB_PATH="$HOME/genessis-rag"      # instead of /ragDbPath
   ```

   `~` and `$VAR` are expanded, so `~/genessis-data` works too. Blank env vars
   are ignored.

2. **The Settings page** (`Config -> App defaults -> Data folder / Chat save
   path / RAG database path`), stored in `dashboard/config/app_settings.json`.
   Path changes need a server restart (the page shows a banner until you do).
   When you save, any path that is a **Windows absolute path** (`E:\...`,
   `\\server\share`) is automatically cleared back to the default so the
   settings file stays portable - a confirmation window lists what was reset.

3. **Defaults** - project-relative `<project>/data` (empty settings).

If you copy the app between machines, either leave the path fields empty (the
default `data/` folder travels with the project) or pin them via the
`GENESSIS_*` env vars. Saved files are never in the way: `data/` is gitignored.

## Folder structure

```
terminator1/
├── server/                   # Thin glue: FastAPI app + chat log + path config
│   ├── server.py             # HTTP endpoints, static mount, lifespan. The ONLY
│   │                         # thing the browser talks to. `python server.py`
│   │                         # runs from any directory.
│   ├── paths.py              # Config-driven runtime path authority: dataDir /
│   │                         # chatSavePath / ragDbPath / customModulesPath
│   │                         # (incl. per-OS *Linux overrides) / RAG switches.
│   ├── console_log.py        # Ring-buffer capture of stdout/stderr + logging
│   │                         # (GET /api/logs/console -> logs.html + chat drawer).
│   ├── tool_log.py           # Append-only tool-usage log (JSONL + in-memory
│   │                         # tail): every tool call agents make, with agent,
│   │                         # timestamp, args, status (GET /api/logs/tools).
│   └── chat_store/           # Server-side chat session + chat log
│       ├── store.py          # ensure_session / append_turn / finalize_session,
│       │                     # the one-active-chat state, .txt transcripts,
│       │                     # chatRecord.jsonl (create/read/delete).
│       └── logger.py         # Small helpers the store uses to log rows.
│
├── agent_monitoring/         # Top-level telemetry subsystem (HTTP-boundary only)
│   ├── __init__.py           # Package boundary: re-exports the public facade
│   ├── store.py              # MonitoringStore: fail-safe JSONL persistence
│   ├── collector.py          # MetricsCollector: in-memory session + turn metrics
│   ├── backup.py             # BackupManager: snapshots + JSON exports
│   ├── manager.py            # MonitoringService facade + get_monitoring_service()
│   └── router.py             # APIRouter -> /api/monitoring/* (status/records/export/reset)
│
├── engine/                   # The agent engine
│   ├── core/
│   │   ├── agent.py          # AgentProfile + the reusable Agent: think/act/observe
│   │   ├── llm.py            # ask_llm(), model resolution (fallback to a
│   │   │                     # detected model), context window, Ollama scan
│   │   └── prompt.py         # PromptManager: agent.md sections + tools -> system prompt
│   ├── agents/
│   │   ├── loader.py         # Read/parse engine/agent_library/{id}/agent.md + agent.json,
│   │   │                     # save_markdown / save_meta / save_tests (Settings page).
│   │   ├── registry.py       # Scans engine/agent_library/ -> available agents.
│   │   └── factory.py        # build_agent(agent_id, model) -> ready-to-use Agent.
│   └── agent_library/        # THE AGENTS - filesystem is the source of truth
│       ├── basic_chat/       # agent.md + agent.json  (mode: chat, no tools)
│       ├── dev_assistant/    # agent.md + agent.json  (mode: agent, tools)
│       ├── problem_discovery_agent/  # agent.md + agent.json (mode: agent)
│       └── rag_assistant/    # agent.md + agent.json  (mode: agent, chat-memory search)
│
├── tools/                    # Capabilities available to agents (per-agent IDs)
│   ├── registry.py           # TOOL_REGISTRY: tool ID -> Python function; resolve_tools/get_session
│   ├── state.py              # FileSession: shared/persisted file-working state
│   └── tools.py              # map_files, read_file, write_text_file, delete_files,
│                             # get_current_date, tell_me_the_date_and_time, search_chat_logs
│
├── memory/                   # RAG memory store
│   ├── ingest.py             # Transcript chunking (ingest_file / ingest_directory)
│   ├── search.py             # RAGStorage: Chroma store + fallback vector DB
│   ├── main.py               # Standalone RAG CLI / cognitive loop experiment
│   └── rag_commit.py         # status / rebuild_store / purge_store for the store
│
├── dashboard/                # Frontend (was "static/")
│   ├── index.html            # UI shell: agent cards + floating chat widget
│   ├── chat.html             # Standalone self-contained chat page
│   ├── config.html           # THE consolidated settings page (see above)
│   ├── config/               # app_settings.json (frontend-owned settings storage)
│   ├── css/styles.css
│   └── js/
│       ├── app.js            # index.html boot module (widget, sessions, agents)
│       ├── config-page.js    # config.html boot module (all settings sections)
│       ├── api/api.js        # All HTTP calls (chats, settings, agents, RAG, ...)
│       ├── classes/          # chat-window.js (widget UI), ChatSession.js (state)
│       ├── logic/            # models.js (model dropdown), chat-formatter.js
│       └── ui/               # markdown.js, appearance.js, config-form.js,
│                             # agents.js, agent-editor.js, header-nav.js
│                             # (+ renderDynamicHeaderButtons for custom modules),
│                             # interface-indicator.js, interface-manager.js
│
├── scripts/                  # CLI utilities
│   ├── rebuild_rag.py        # python scripts/rebuild_rag.py [build|purge|status]
│   ├── version_chats.py      # list | import | bump | versioning on|off
│   └── update_docs.py        # Regenerates APP_STRUCTURE.md + APP_CODE_SNAPSHOT.md
│
├── interface/                # Modular update & restore layer (no core edits needed)
│   ├── update_manager.py     # Discover/import interface/updates/<domain>/*.py
│   │                         # get_active_module() + move_module_to_external_archive()
│   ├── interface_dispatcher.py  # trace_and_execute(): logs caller file+line
│   ├── restore_manager.py    # ONE master copy (current-known-good-copy/):
│   │                         # snapshot() publish / status() drift / restore()
│   ├── custom_module_manager.py  # Drop-in .py loader for data/custom_modules/
│   │                         # (default Custom Modules Path)
│   ├── wiring/               # The connection layer: registers custom-module
│   │   │                     # routes + bridges custom modules into the update
│   │   │                     # catalog under the virtual 'custom' domain, so
│   │   │                     # core code can call them via execute_action()
│   │   └── bridges.py
│   └── updates/              # Active update modules, grouped by domain
│       ├── engine/
│       ├── tools/
│       └── server/
│
├── about/                    # Site identity
│   ├── about.json            # title + subtitle served by GET /api/about
│   └── set_title.py          # Edits about.json + 'create-module' generator
│
├── config/
│   └── models.json           # AUTO-GENERATED at startup from installed Ollama models
├── docs/
│   ├── CHANGELOG.md          # Every recent change
│   ├── HOW_TO_USE.md         # Day-to-day custom modules guide
│   ├── CUSTOM_MODULE_DEV_GUIDE.md  # Full dev guide: HTML <-> server.py <-> modules,
│   │                         # all UI action types + wiring bridge (real code)
│   ├── phase-1-2-3-update/   # Drop-in custom modules install kit (was applied)
│   ├── APP_STRUCTURE.md      # AUTO-GENERATED folder-tree snapshot
│   └── APP_CODE_SNAPSHOT.md  # AUTO-GENERATED per-file source snapshot
├── current-known-good-copy/  # GENERATED master copy: complete copy of the last
│                             # good source ("Save current state as master" in
│                             # Settings -> Updates/Interface, or snapshot())
├── data/                     # RUNTIME data (gitignored): chatlog, RAG store,
│                             # interface_archive/, snapshots/pre_restore_backup/,
│                             # custom_modules/ (drop-in .py modules)
├── requirements.txt
└── README.md
```

> **Keep the docs fresh:** `docs/APP_STRUCTURE.md` and `docs/APP_CODE_SNAPSHOT.md`
> are generated, not hand-maintained. After code changes run
> `venv/bin/python scripts/update_docs.py` and commit the regenerated files.

## How an answer is produced

```
Browser
  ↓ POST /api/chat {message, model, agent_id, history, session_id, title, new_chat, rag}
server.py
  ↓ chat_store.ensure_session()          server/chat_store/store.py (ONE active chat)
  ↓ build_agent(agent_id)                engine/agents/factory.py
loader: agent.md + agent.json            engine/agents/loader.py
tools:  IDs -> functions                 tools/registry.py
prompt: sections + tool docs -> system msg   engine/core/prompt.py
  ↓
Agent.think()                            engine/core/agent.py
  ↓ ask_llm()                            engine/core/llm.py
Ollama
  ↓
server.py appends the turn to the active chat and returns {reply, session_id, title}
  ↓ (on "Save chat" / new chat)
chat_store.finalize_session() writes data/chatlog/agent-text-records/<title>[-v].txt
+ logs it in data/chatlog/chatRecord.jsonl
```

### Model selection

- `config/models.json` is **auto-scanned at startup** (`refresh_models()`) from
  THIS machine's Ollama — it always mirrors what is installed, and the model
  dropdown only lists detected models.
- A requested model that is **not installed** (for example a per-agent pin or
  default written on another OS) is never used blindly: the server logs an
  `[ask_llm]` warning and falls back to a detected model instead of failing
  with a 404. So Windows-authored settings keep working on Linux or any
  machine, regardless of its Ollama install.
- Agents that use tools get a model Ollama reports as **`tools`-capable** when
  possible (confirmed no-tools models are skipped). Only if no tool-capable
  model exists does the agent answer without tool use.
- Empty `defaultModel` (`""`) means "resolve to the first detected model" —
  changes to your defaults apply after a server restart.

## Chats: one server-side session at a time

The server tracks exactly ONE active chat session (it has its own start, middle
and end):

- First message of a chat (or `new_chat: true`) finalizes any previous chat and
  starts a new one; the server owns the conversation, so a page refresh never
  loses it.
- `data/chatlog/.active-chat.json` holds the live session (updates after every
  turn).
- Ending a chat (`POST /api/chats/end`, the "Save chat" button, or starting a
  new chat) writes ONE transcript per chat to
  `data/chatlog/agent-text-records/<title>.txt` — and on a name collision the
  NEXT version (`<title>-2.txt`, ...). Re-saving a chat you kept typing in
  produces the next version; old versions stay on disk.
- `data/chatlog/chatRecord.jsonl` is the LOG of those transcripts (title, agent,
  model, version, message/interaction counts, timestamps) used by the frontend
  drop-down — one line per chat VERSION; the drop-down shows the newest version
  of each chat. Existing `.txt` files are imported into the log once at startup.

Version helpers: `python scripts/version_chats.py list | import | bump
<id-or-title> [version] | versioning on|off`.

Agent modes:

- `chat`  — User → LLM → Response. The factory attaches no tools, so no tool loop can happen.
- `agent` — User → Agent → LLM → Tool? → Observation → LLM → Response. Same `Agent` class; only its configuration differs.

## API

| Endpoint | Purpose |
|---|---|
| `GET /api/models` | Model dropdown options (scanned from Ollama at startup) |
| `GET /api/agents` | All discovered agents: `{id, name, description, mode}` |
| `GET /api/tools` | Every tool ID an agent can pick (feeds the Settings checkboxes) |
| `GET /api/agents/{id}/config` | One agent's consolidated config (meta + `agent.md` + tests + shared tests) |
| `PUT /api/agents/{id}/config` | Partial update of one agent's config (`meta` / `markdown` / `tests`) |
| `GET /api/about` | Site identity (title + tagline from `about/about.json`) |
| `GET /api/interface/status` | Interface status: module catalog, custom modules (folder + `ui_manifests`), archive, trace-log tail, master copy + drift |
| `POST /api/interface/apply` | Reload update modules from disk + regenerate the docs snapshots |
| `POST /api/interface/snapshot` | Publish the current tree as the known-good master copy |
| `POST /api/interface/restore` | Roll every app file back to the master copy (backup first, then regen docs) |
| `POST /api/interface/run` | Execute an update-module function (`{domain, module, function, args?, kwargs?}`) |
| `POST /api/interface/toggle-run` | `{enabled}` — arm/disarm module execution for the process |
| `GET /api/logs/console` | Tail of the captured console output (feeds the chat console drawer + `logs.html`) |
| `GET /api/logs/tools` | Structured tool-usage feed (newest first; filter by `tool`, `agent`, `since`; from `data/toollog/tool_usage.jsonl`) |
| `GET /api/monitoring/status` | Agent telemetry status: active sessions + cumulative system turns |
| `GET /api/monitoring/records` | Every stored telemetry record (`<dataDir>/monitoring/agent_metrics.jsonl`) |
| `POST /api/monitoring/export` | Write a JSON telemetry report to `<dataDir>/exports/` |
| `POST /api/monitoring/reset` | Snapshot the metrics log, then clear it (safe reset) |
| `POST /api/chat` | `{message, model, agent_id, history, session_id?, title?, new_chat?, rag?}` → `{reply, session_id, title}` |
| `GET /api/chats` | Chat log + the active chat (feeds the chats drop-down) |
| `GET /api/chats/{id}` | One chat: log row + `.txt` content + parsed messages |
| `POST /api/chats/end` | Finalize the active chat into a versioned `.txt` + log it (`rag` bool overrides committing it to memory) |
| `DELETE /api/chats/{id}` | Permanently erase a chat (transcripts + log records) |
| `POST /api/chat-save` | Finalize the active chat (kept for legacy clients) |
| `GET /api/rag/status` | RAG store location + indexed chunk count + resolved paths |
| `POST /api/rag/rebuild` | Re-index every saved transcript into the RAG store |
| `POST /api/rag/reset` | Delete the RAG store so it starts empty (transcripts kept) |
| `GET/POST/DELETE /api/discussions` | CRUD over the same chat log (chatRecord.jsonl records) |
| `GET/POST/DELETE /api/history` | Saved message snapshots (`data/history.json`) |
| `GET/POST /api/settings` | The stored browser defaults (`dashboard/config/app_settings.json`) |
| `POST /api/exports` | Save one wizard prompt as `{name}.md` + `{name}.json` (data/exports) |

There is no `/api/activity` endpoint anymore — the Agent Monitor feature was
removed (see `docs/CHANGELOG.md`). Anything polling it will get a 404.

### RAG memory store

Saved chats can be committed to a persistent RAG store so agents using the
`search_chat_logs` tool can recall them. Controls:

- **Per chat:** flip the "Save to memory" toggle in the chat header before
  sending/saving (both the index.html flyout and the standalone `chat.html`
  page have it).
- **Default:** the "Commit saved chats to memory by default" toggle in
  Configuration → RAG memory (`rag.commitOnSave`).
- **Auto-loading:** when the store is empty, the first search ingests every
  transcript automatically unless "Auto-load transcripts..." is off
  (`rag.autoIngest`).
- **Paths:** Configuration → Data folder / RAG database path / Chat save path,
  stored in `dashboard/config/app_settings.json` and resolved by
  `server/paths.py` (absolute paths are used verbatim; relative paths resolve
  against the project root). Path changes apply after a server restart — the
  configuration page shows a "restart the server" banner until you do.
  Transcripts follow **Chat save path**, not the Data folder; blank means
  `<dataDir>/chatlog/agent-text-records`.
- **Cross-platform paths:** the same settings file works on Windows *and*
  Linux. Add `dataDirLinux`, `chatSavePathLinux` and `ragDbPathLinux` (set
  from Configuration → "Linux paths" on a non-Windows machine) to point the
  app at a second, Linux-specific layout; each override falls back to a
  project default when blank. A Windows-only drive path (`E:\data\...`) left
  without a Linux override is ignored on Linux rather than becoming a literal
  `E:\data\...` folder. `GET /api/settings` and `GET /api/rag/status` both
  report the detected `platform` (`"win"` / `"nix"`).
- **Manual maintenance:** `python scripts/rebuild_rag.py [build|purge|status]`,
  the "Rebuild memory"/"Forget everything" buttons in Configuration, or the
  "Clear Memory" button in the chat header (`chat.html`) — clear resets the
  store to zero entries.

The store lives at `data/rag_db/chroma.sqlite3` by default. The store keeps
embeddings even if the original transcripts are deleted, so recall keeps
working until you wipe it.

## Creating a new agent

No Python required: create a folder under `engine/agent_library/` containing
`agent.json` (configuration) + `agent.md` (behavior), pick tool IDs, and
refresh — the agent appears automatically in `GET /api/agents` and the frontend
selector.

Full field reference, tool catalog, copy-paste example, and troubleshooting:
see **`docs/CHANGELOG.md`** for the project history and architecture (the older
`docs/documentation_CREATING_AGENTS.md` guide was removed).

## Adding a new tool

1. Write the function in `tools/tools.py` with a clear docstring — Ollama turns
   docstrings into the tool schema the LLM sees.
2. Add one line to `TOOL_REGISTRY` in `tools/registry.py`.
3. Reference the ID in any agent's `agent.json`.

## Modular interface: add / apply / master-copy recovery

New or experimental logic can live outside the core modules under
`interface/updates/<domain>/` (domains: `engine`, `tools`, `server`). Nothing
in the core app is edited.

- **Add a feature**: drop a `.py` file in `interface/updates/<domain>/`, then
  press **Apply** on the Settings → Updates/Interface card (or restart) — it is
  discovered, imported, and the docs snapshots are regenerated.
- **Use it natively (Option B)**:
  ```python
  from interface.update_manager import UpdateManager
  mod = UpdateManager().get_active_module("engine", "newfunction")
  mod.execute_new_logic("Input Data")
  ```
  or wrapped with caller tracing (logs `file:line -> module.function` to
  `data/interface_trace.log`):
  ```python
  from interface.interface_dispatcher import InterfaceDispatcher
  InterfaceDispatcher().trace_and_execute(mod.run_example)
  InterfaceDispatcher().execute_action("engine", "newfunction",
                                       "secondary_engine_action", 5)
  ```
  The server discovers update modules and builds both managers at startup,
  exposed on `app.state.update_manager` / `app.state.interface_dispatcher`.
- **Retire a module**: `UpdateManager().move_module_to_external_archive("engine", "hello_update")`
  moves the file out of the repo into `data/interface_archive/engine/`.
- **Set the master copy**: "Save current state as master" on the
  Updates/Interface card publishes a complete working copy of the current
  source into `current-known-good-copy/`.
- **Recover / roll back**: "Restore to master copy" (warning dialog first)
  overwrites every tracked file whose SHA-256 differs from the master copy.
  Files only in the live tree or only in the master are added, never deleted.
  Overwritten files are first copied to `agent_monitoring/data/snapshots/
  pre_restore_backup/`. User data (`agent_monitoring/data/`, `venv/`, `.git/`,
  `dashboard/config/app_settings.json`, `about/about.json`) is never touched,
  and the docs snapshots are regenerated afterwards.

### Drop-in custom modules (the flat `data/custom_modules/` loader)

> **Step-by-step guide:** see **[docs/HOW_TO_USE.md](docs/HOW_TO_USE.md)** for
> the day-to-day "generate → edit → activate → click" loop, the full anatomy
> of a module file, and how to disable or inspect modules.

A **second** extension channel from the `interface/updates/` domain system —
its own manager, `interface/custom_module_manager.py`, scans a single flat
folder (**Custom Modules Path**, default `data/custom_modules/`; set it in
Settings → App defaults) for standalone `.py` files and imports each with
`importlib.util`. The two loaders stay separate and idle modules never touch
each other, but `interface/wiring/` connects them: a loaded custom module is
**bridged** into the update catalog under the virtual `custom` domain, so core
code can ALSO call its functions through the traced dispatcher — see below.

A custom module is just a `.py` file declaring a `UI_MANIFEST` and a
`register_routes(app)` function:

- **Generate one:** `python about/set_title.py create-module analytics_builder`
  writes `data/custom_modules/analytics_builder.py` pre-wired with a
  "＋ Analytics Builder" header button (`UI_MANIFEST`) and a
  `POST /api/analytics_builder/execute` endpoint (`register_routes(app)`).
- **Activate:** restart the server (`python server.py`) — simplest — or, for a
  brand-new module only, press **Apply** on the Settings → Updates/Interface
  card. Already-loaded modules pick up edits on a restart.
- **See it:** reload the dashboard. Each active module's `UI_MANIFEST` button
  appears in the header automatically (via `renderDynamicHeaderButtons` in
  `dashboard/js/ui/header-nav.js`) — no `index.html`, `header-nav.js` or
  `server.py` edits. Clicking prompts for input and POSTs to the module's
  endpoint.
- **Button actions:** a manifest `buttons[]` entry can declare one of:
  - `action: "prompt_input"` — legacy: a `window.prompt` whose text is POSTed
    as `{ "input": ... }` to `api_endpoint`.
  - `action: "dropdown_menu"` — a flyout button whose `items[]` carry the real
    actions (any of the below). Selecting an item runs it against the parent
    button.
  - `action: "open_modal"` — fetches `schema_endpoint` (a JSON schema of
    `input` / `select` / `checkbox` / `button` components) and builds a modal
    form; on submit it POSTs to the schema's `target_endpoint`.
  - `action: "qa_survey"` — a step-by-step wizard that POSTs
    `{ step, answers }` to `qa_endpoint` until `completed: true`.
  - `status_dot` — when any executed action returns `indicate_success: true`,
    a green `status-dot` appears on the trigger button. See the bundled
    `interactive_manager` module in your Custom Modules Path for a full
    reference impl of all four.
- **Where files live:** blank path = `<dataDir>/custom_modules`; relative
  paths resolve from the project root; absolute paths are used as-is;
  `GENESSIS_CUSTOM_MODULES_PATH` overrides everything. Path changes apply after
  a restart. The folder is created automatically on first boot.
- `GET /api/interface/status` returns `custom_modules` (folder + active names),
  `ui_manifests` so the frontend knows what to render, and `bridge` — the names
  also reachable from core code (see below).

#### The wiring bridge: calling a custom module from core code

`interface/wiring/` is the connection layer. When modules load, it registers
each custom module's FastAPI routes (once per process) and mirrors the module
into the update manager's catalog under the virtual domain **`custom`**. Once
loaded, any public function in a drop-in module is callable from anywhere in
the app through the same traced dispatcher used for update modules — logged to
`data/interface_trace.log`:

```python
from interface.interface_dispatcher import InterfaceDispatcher

InterfaceDispatcher().execute_action("custom", "analytics_builder",
                                     "execute_logic", "some input")
```

So a feature is exposed to BOTH the browser (header button → route) and the
Python core (traced function call) from one file. Apply/restart re-asserts
the bridge after every reload.

### In the browser

The Settings page (`Dashboard -> Settings`) has an **Updates / Interface**
card below Models: live module catalog, archive, master-copy freshness +
drift, the trace-log tail, and Apply / Save current state as master /
Restore to master copy buttons (restore asks for confirmation in a warning
dialog first). A small **"N updates" pill** also sits in the page header
(amber dot when the master copy has drifted) and links back to that card.

Module execution from the UI is **disabled by default**: the card's
"Enable module execution" toggle arms `/api/interface/run` (backed server-side
by `INTERFACE_RUN_ENABLED`, flipped via `/api/interface/toggle-run`). On by
your own risk — it runs arbitrary functions from `interface/updates/`.

## Recent changes

See **[docs/CHANGELOG.md](docs/CHANGELOG.md)** for the full history. The most
recent entry covers the **`agent_monitoring/` telemetry subsystem**: a
top-level, HTTP-boundary-only package that records per-turn agent duration and
tool-call counts to `<dataDir>/monitoring/agent_metrics.jsonl`, tracks active
sessions, and exposes `GET /api/monitoring/status|records` plus
`POST /api/monitoring/export|reset` (reset snapshots before clearing). Before
that, the entry covering the **dynamic module UI actions + developer guide**: a
manifest button can now be a `dropdown_menu` (flyout), `open_modal`
(schema-driven form), `qa_survey` (step wizard) or `prompt_input`, any response
with `indicate_success: true` lights a green status-dot, and the new
[`docs/CUSTOM_MODULE_DEV_GUIDE.md`](docs/CUSTOM_MODULE_DEV_GUIDE.md) documents
all of it with copy-paste code. Earlier entries cover the **drop-in custom
modules** system (Phase 1/2/3): drop a `.py` file with a `UI_MANIFEST` +
`register_routes(app)` into **Custom Modules Path** (default
`data/custom_modules/`) and its header button + FastAPI routes go live
automatically — scaffold one with `python about/set_title.py create-module
<name>`. Before that: the cross-platform path system (per-OS keys +
`GENESSIS_*` overrides), the "Settings saved" response window, resilient model
selection, and the Modular Interface wiring (`/api/interface/*` + the Settings
card). Older entries cover the Agent Monitor removal, and the recovery of
`engine/core/agent.py` + `server/server.py` to their working originals.

Recovery artifacts to be aware of:

- `current-known-good-copy/` — the generated master copy (see the Modular
  Interface section above). Not part of the running app.
- `server/server.py.infected.bak` and `engine/core/agent.py.infected.bak` —
  copies of the pre-rollback monitor-era files, kept in case you need to
  diff/inspect them.

## Notes

- The backend tracks one active chat session at a time (see "Chats" above);
  `history` is still accepted for backwards compatibility.
- `/api/chat` is intentionally a sync endpoint so blocking LLM calls run in
  FastAPI's threadpool instead of stalling the event loop.
- Chat transcripts live in `data/chatlog/agent-text-records/` as `.txt` files;
  `data/chatlog/chatRecord.jsonl` is the header log that points at them.
- **`ModuleNotFoundError: No module named 'fastapi'`** when starting the
  server means the shell is not using the project venv. Linux has no bare
  `python` — activate it (`source venv/bin/activate`) or launch directly
  (`venv/bin/python server/server.py`).
