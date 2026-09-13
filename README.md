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

- **App defaults** â€” default agent (with a jump-link to that agent's card),
  default model, chat save path, data folder, RAG database path, chat
  versioning, and the RAG memory defaults. Stored in
  `dashboard/config/app_settings.json`.
- **Appearance** â€” one theme + font set for all pages.
- **Agents** â€” one card per agent, consolidating its whole config in one place:
  metadata + model + tools (its `agent.json`), its behavior prose (editable
  `agent.md`), and that agent's chat tests + an inline runner.
- **Shared tests** â€” tests with no agent that run for every agent.
- **Models** â€” read-only snapshot of the installed Ollama models.

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

`python server.py` can be run from ANY directory â€” the project root or
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
â”œâ”€â”€ server/                   # Thin glue: FastAPI app + chat log + path config
â”‚   â”œâ”€â”€ server.py             # HTTP endpoints, static mount, lifespan. The ONLY
â”‚   â”‚                         # thing the browser talks to. `python server.py`
â”‚   â”‚                         # runs from any directory.
â”‚   â”œâ”€â”€ paths.py              # Config-driven runtime path authority: dataDir /
â”‚   â”‚                         # chatSavePath / ragDbPath (incl. per-OS
â”‚   â”‚                         # *Linux overrides) / RAG switches.
â”‚   â””â”€â”€ chat_store/           # Server-side chat session + chat log
â”‚       â”œâ”€â”€ store.py          # ensure_session / append_turn / finalize_session,
â”‚       â”‚                     # the one-active-chat state, .txt transcripts,
â”‚       â”‚                     # chatRecord.jsonl (create/read/delete).
â”‚       â””â”€â”€ logger.py         # Small helpers the store uses to log rows.
â”‚
â”œâ”€â”€ engine/                   # The agent engine
â”‚   â”œâ”€â”€ core/
â”‚   â”‚   â”œâ”€â”€ agent.py          # AgentProfile + the reusable Agent: think/act/observe
â”‚   â”‚   â”œâ”€â”€ llm.py            # ask_llm(), model resolution (fallback to a
â”‚   â”‚   â”‚                     # detected model), context window, Ollama scan
â”‚   â”‚   â””â”€â”€ prompt.py         # PromptManager: agent.md sections + tools -> system prompt
â”‚   â”œâ”€â”€ agents/
â”‚   â”‚   â”œâ”€â”€ loader.py         # Read/parse engine/agent_library/{id}/agent.md + agent.json,
â”‚   â”‚   â”‚                     # save_markdown / save_meta / save_tests (Settings page).
â”‚   â”‚   â”œâ”€â”€ registry.py       # Scans engine/agent_library/ -> available agents.
â”‚   â”‚   â””â”€â”€ factory.py        # build_agent(agent_id, model) -> ready-to-use Agent.
â”‚   â””â”€â”€ agent_library/        # THE AGENTS - filesystem is the source of truth
â”‚       â”œâ”€â”€ basic_chat/       # agent.md + agent.json  (mode: chat, no tools)
â”‚       â”œâ”€â”€ dev_assistant/    # agent.md + agent.json  (mode: agent, tools)
â”‚       â”œâ”€â”€ problem_discovery_agent/  # agent.md + agent.json (mode: agent)
â”‚       â””â”€â”€ rag_assistant/    # agent.md + agent.json  (mode: agent, chat-memory search)
â”‚
â”œâ”€â”€ tools/                    # Capabilities available to agents (per-agent IDs)
â”‚   â”œâ”€â”€ registry.py           # TOOL_REGISTRY: tool ID -> Python function; resolve_tools/get_session
â”‚   â”œâ”€â”€ state.py              # FileSession: shared/persisted file-working state
â”‚   â””â”€â”€ tools.py              # map_files, read_file, write_text_file, delete_files,
â”‚                             # get_current_date, tell_me_the_date_and_time, search_chat_logs
â”‚
â”œâ”€â”€ memory/                   # RAG memory store
â”‚   â”œâ”€â”€ ingest.py             # Transcript chunking (ingest_file / ingest_directory)
â”‚   â”œâ”€â”€ search.py             # RAGStorage: Chroma store + fallback vector DB
â”‚   â”œâ”€â”€ main.py               # Standalone RAG CLI / cognitive loop experiment
â”‚   â””â”€â”€ rag_commit.py         # status / rebuild_store / purge_store for the store
â”‚
â”œâ”€â”€ dashboard/                # Frontend (was "static/")
â”‚   â”œâ”€â”€ index.html            # UI shell: agent cards + floating chat widget
â”‚   â”œâ”€â”€ chat.html             # Standalone self-contained chat page
â”‚   â”œâ”€â”€ config.html           # THE consolidated settings page (see above)
â”‚   â”œâ”€â”€ config/               # app_settings.json (frontend-owned settings storage)
â”‚   â”œâ”€â”€ css/styles.css
â”‚   â””â”€â”€ js/
â”‚       â”œâ”€â”€ app.js            # index.html boot module (widget, sessions, agents)
â”‚       â”œâ”€â”€ config-page.js    # config.html boot module (all settings sections)
â”‚       â”œâ”€â”€ api/api.js        # All HTTP calls (chats, settings, agents, RAG, ...)
â”‚       â”œâ”€â”€ classes/          # chat-window.js (widget UI), ChatSession.js (state)
â”‚       â”œâ”€â”€ logic/            # models.js (model dropdown), chat-formatter.js
â”‚       â””â”€â”€ ui/               # markdown.js, appearance.js, config-form.js,
â”‚                             # agents.js, agent-editor.js, header-nav.js,
â”‚                             # interface-indicator.js, interface-manager.js
â”‚
â”œâ”€â”€ scripts/                  # CLI utilities
â”‚   â”œâ”€â”€ rebuild_rag.py        # python scripts/rebuild_rag.py [build|purge|status]
â”‚   â”œâ”€â”€ version_chats.py      # list | import | bump | versioning on|off
â”‚   â””â”€â”€ update_docs.py        # Regenerates APP_STRUCTURE.md + APP_CODE_SNAPSHOT.md
â”‚
â”œâ”€â”€ interface/                # Modular update & restore layer (no core edits needed)
â”‚   â”œâ”€â”€ update_manager.py     # Discover/import interface/updates/<domain>/*.py
â”‚   â”‚                         # get_active_module() + move_module_to_external_archive()
â”‚   â”œâ”€â”€ interface_dispatcher.py  # trace_and_execute(): logs caller file+line
â”‚   â”œâ”€â”€ restore_manager.py    # Baseline compare/restore + snapshot_baseline()
â”‚   â””â”€â”€ updates/              # Active update modules, grouped by domain
â”‚       â”œâ”€â”€ engine/           # e.g. hello_update.py, newfunction.py (examples)
â”‚       â”œâ”€â”€ tools/
â”‚       â””â”€â”€ server/
â”‚
â”œâ”€â”€ about/                    # Site identity
â”‚   â”œâ”€â”€ about.json            # title + subtitle served by GET /api/about
â”‚   â””â”€â”€ set_title.py          # Edits about.json + 'apply'/'snapshot'/'restore' triggers
â”‚
â”œâ”€â”€ config/
â”‚   â””â”€â”€ models.json           # AUTO-GENERATED at startup from installed Ollama models
â”œâ”€â”€ docs/
â”‚   â”œâ”€â”€ CHANGELOG.md          # Every recent change
â”‚   â”œâ”€â”€ RESTRUCTURE_README.md # History of the current package layout
â”‚   â”œâ”€â”€ 01_IDEA_AND_ARCHITECTURE.md       # Modular Interface architecture design
â”‚   â”œâ”€â”€ APP_STRUCTURE.md      # AUTO-GENERATED folder-tree snapshot
â”‚   â””â”€â”€ APP_CODE_SNAPSHOT.md  # AUTO-GENERATED per-file source snapshot
â”œâ”€â”€ current-known-good-copy/  # GENERATED restore baseline: complete copy of the
â”‚                             # last good source (python about/set_title.py snapshot)
â”œâ”€â”€ data/                     # RUNTIME data (gitignored): chatlog, RAG store,
â”‚                             # interface_archive/, snapshots/pre_restore_backup/
â”œâ”€â”€ requirements.txt
â””â”€â”€ README.md
```

> **Keep the docs fresh:** `docs/APP_STRUCTURE.md` and `docs/APP_CODE_SNAPSHOT.md`
> are generated, not hand-maintained. After code changes run
> `venv/bin/python scripts/update_docs.py` and commit the regenerated files.

## How an answer is produced

```
Browser
  â†“ POST /api/chat {message, model, agent_id, history, session_id, title, new_chat, rag}
server.py
  â†“ chat_store.ensure_session()          server/chat_store/store.py (ONE active chat)
  â†“ build_agent(agent_id)                engine/agents/factory.py
loader: agent.md + agent.json            engine/agents/loader.py
tools:  IDs -> functions                 tools/registry.py
prompt: sections + tool docs -> system msg   engine/core/prompt.py
  â†“
Agent.think()                            engine/core/agent.py
  â†“ ask_llm()                            engine/core/llm.py
Ollama
  â†“
server.py appends the turn to the active chat and returns {reply, session_id, title}
  â†“ (on "Save chat" / new chat)
chat_store.finalize_session() writes data/chatlog/agent-text-records/<title>[-v].txt
+ logs it in data/chatlog/chatRecord.jsonl
```

### Model selection

- `config/models.json` is **auto-scanned at startup** (`refresh_models()`) from
  THIS machine's Ollama â€” it always mirrors what is installed, and the model
  dropdown only lists detected models.
- A requested model that is **not installed** (for example a per-agent pin or
  default written on another OS) is never used blindly: the server logs an
  `[ask_llm]` warning and falls back to a detected model instead of failing
  with a 404. So Windows-authored settings keep working on Linux or any
  machine, regardless of its Ollama install.
- Agents that use tools get a model Ollama reports as **`tools`-capable** when
  possible (confirmed no-tools models are skipped). Only if no tool-capable
  model exists does the agent answer without tool use.
- Empty `defaultModel` (`""`) means "resolve to the first detected model" â€”
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
  `data/chatlog/agent-text-records/<title>.txt` â€” and on a name collision the
  NEXT version (`<title>-2.txt`, ...). Re-saving a chat you kept typing in
  produces the next version; old versions stay on disk.
- `data/chatlog/chatRecord.jsonl` is the LOG of those transcripts (title, agent,
  model, version, message/interaction counts, timestamps) used by the frontend
  drop-down â€” one line per chat VERSION; the drop-down shows the newest version
  of each chat. Existing `.txt` files are imported into the log once at startup.

Version helpers: `python scripts/version_chats.py list | import | bump
<id-or-title> [version] | versioning on|off`.

Agent modes:

- `chat`  â€” User â†’ LLM â†’ Response. The factory attaches no tools, so no tool loop can happen.
- `agent` â€” User â†’ Agent â†’ LLM â†’ Tool? â†’ Observation â†’ LLM â†’ Response. Same `Agent` class; only its configuration differs.

## API

| Endpoint | Purpose |
|---|---|
| `GET /api/models` | Model dropdown options (scanned from Ollama at startup) |
| `GET /api/agents` | All discovered agents: `{id, name, description, mode}` |
| `GET /api/tools` | Every tool ID an agent can pick (feeds the Settings checkboxes) |
| `GET /api/agents/{id}/config` | One agent's consolidated config (meta + `agent.md` + tests + shared tests) |
| `PUT /api/agents/{id}/config` | Partial update of one agent's config (`meta` / `markdown` / `tests`) |
| `GET /api/about` | Site identity (title + tagline from `about/about.json`) |
| `GET /api/interface/status` | Interface status: module catalog, archive, trace-log tail, baseline + drift |
| `POST /api/interface/apply` | Reload update modules from disk + regenerate the docs snapshots |
| `POST /api/interface/snapshot` | Publish the current tree as the new known-good baseline |
| `POST /api/interface/restore` | `{baseline?, apply?, dryRun?}` â€” roll back (dry-run by default) |
| `POST /api/interface/run` | Execute an update-module function (`{domain, module, function, args?, kwargs?}`) |
| `POST /api/interface/toggle-run` | `{enabled}` â€” arm/disarm module execution for the process |
| `POST /api/chat` | `{message, model, agent_id, history, session_id?, title?, new_chat?, rag?}` â†’ `{reply, session_id, title}` |
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

There is no `/api/activity` endpoint anymore â€” the Agent Monitor feature was
removed (see `docs/CHANGELOG.md`). Anything polling it will get a 404.

### RAG memory store

Saved chats can be committed to a persistent RAG store so agents using the
`search_chat_logs` tool can recall them. Controls:

- **Per chat:** flip the "Save to memory" toggle in the chat header before
  sending/saving (both the index.html flyout and the standalone `chat.html`
  page have it).
- **Default:** the "Commit saved chats to memory by default" toggle in
  Configuration â†’ RAG memory (`rag.commitOnSave`).
- **Auto-loading:** when the store is empty, the first search ingests every
  transcript automatically unless "Auto-load transcripts..." is off
  (`rag.autoIngest`).
- **Paths:** Configuration â†’ Data folder / RAG database path / Chat save path,
  stored in `dashboard/config/app_settings.json` and resolved by
  `server/paths.py` (absolute paths are used verbatim; relative paths resolve
  against the project root). Path changes apply after a server restart â€” the
  configuration page shows a "restart the server" banner until you do.
  Transcripts follow **Chat save path**, not the Data folder; blank means
  `<dataDir>/chatlog/agent-text-records`.
- **Cross-platform paths:** the same settings file works on Windows *and*
  Linux. Add `dataDirLinux`, `chatSavePathLinux` and `ragDbPathLinux` (set
  from Configuration â†’ "Linux paths" on a non-Windows machine) to point the
  app at a second, Linux-specific layout; each override falls back to a
  project default when blank. A Windows-only drive path (`E:\data\...`) left
  without a Linux override is ignored on Linux rather than becoming a literal
  `E:\data\...` folder. `GET /api/settings` and `GET /api/rag/status` both
  report the detected `platform` (`"win"` / `"nix"`).
- **Manual maintenance:** `python scripts/rebuild_rag.py [build|purge|status]`,
  the "Rebuild memory"/"Forget everything" buttons in Configuration, or the
  "Clear Memory" button in the chat header (`chat.html`) â€” clear resets the
  store to zero entries.

The store lives at `data/rag_db/chroma.sqlite3` by default. The store keeps
embeddings even if the original transcripts are deleted, so recall keeps
working until you wipe it.

## Creating a new agent

No Python required: create a folder under `engine/agent_library/` containing
`agent.json` (configuration) + `agent.md` (behavior), pick tool IDs, and
refresh â€” the agent appears automatically in `GET /api/agents` and the frontend
selector.

Full field reference, tool catalog, copy-paste example, and troubleshooting:
see **`docs/CHANGELOG.md`** and `docs/01_IDEA_AND_ARCHITECTURE.md` for the
project history and architecture (the older `docs/documentation_CREATING_AGENTS.md`
guide was removed).

## Adding a new tool

1. Write the function in `tools/tools.py` with a clear docstring â€” Ollama turns
   docstrings into the tool schema the LLM sees.
2. Add one line to `TOOL_REGISTRY` in `tools/registry.py`.
3. Reference the ID in any agent's `agent.json`.

## Modular interface: add / apply / snapshot / restore

New or experimental logic can live outside the core modules under
`interface/updates/<domain>/` (domains: `engine`, `tools`, `server`). Nothing
in the core app is edited.

- **Add a feature**: drop a `.py` file in `interface/updates/<domain>/`, then
  `python about/set_title.py apply` â€” it is discovered, imported, and the
  docs snapshots are regenerated. `apply --snapshot` also refreshes the
  baseline.
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
- **Re-baseline**: `python about/set_title.py snapshot` publishes a complete
  working copy of the current source into `current-known-good-copy/`.
- **Roll back**: `python about/set_title.py restore --dry-run` previews, then
  `python about/set_title.py restore` overwrites any file whose SHA-256
  differs from the baseline (files only in the baseline or only in the live
  tree are reported, never copied/deleted). Overwritten files are first
  copied to `data/snapshots/pre_restore_backup/`. User data (`data/`,
  `venv/`, `.git/`, `dashboard/config/app_settings.json`, `about/about.json`)
  is never touched, and the docs snapshots are regenerated afterwards.

Design reference: `docs/01_IDEA_AND_ARCHITECTURE.md`.

### In the browser

The Settings page (`Dashboard -> Settings`) has an **Updates / Interface**
card below Models: live module catalog, archive, baseline freshness + drift,
the trace-log tail, and Apply / Snapshot / Restore buttons (restore is dry-run
first). A small **"N updates" pill** also sits in the page header (amber dot
when the baseline has drifted) and links back to that card.

Module execution from the UI is **disabled by default**: the card's
"Enable module execution" toggle arms `/api/interface/run` (backed server-side
by `INTERFACE_RUN_ENABLED`, flipped via `/api/interface/toggle-run`). On by
your own risk â€” it runs arbitrary functions from `interface/updates/`.

## Recent changes

See **[docs/CHANGELOG.md](docs/CHANGELOG.md)** for the full history. The most
recent entry covers the cross-platform path system â€” per-OS path keys for
Windows/Linux/macOS plus `GENESSIS_*` environment overrides (each machine picks
its own folder, so one settings file travels between OSes), the "Settings saved"
response window, resilient model selection, and the Modular Interface wiring
(`/api/interface/*` + the Settings card). Earlier entries cover the Agent Monitor
removal, and the recovery of `engine/core/agent.py` + `server/server.py` to their
working originals.

Recovery artifacts to be aware of:

- `current-known-good-copy/` â€” the generated restore baseline (see the Modular
  Interface section above). Not part of the running app.
- `server/server.py.infected.bak` and `engine/core/agent.py.infected.bak` â€”
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
  `python` â€” activate it (`source venv/bin/activate`) or launch directly
  (`venv/bin/python server/server.py`).
