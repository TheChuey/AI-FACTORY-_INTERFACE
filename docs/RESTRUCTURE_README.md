# Terminator1 â€” Reorganized Layout

This is your original app, regrouped into four clear domains. All import
paths were rewritten to match â€” this isn't just a file shuffle, it's a
working package layout.

```
terminator1/
â”œâ”€â”€ engine/                 # The agent factory ("engine")
â”‚   â”œâ”€â”€ core/
â”‚   â”‚   â”œâ”€â”€ agent.py        # Agent runtime: think/act/observe loop
â”‚   â”‚   â”œâ”€â”€ llm.py          # ask_llm(), model resolution (falls back to a
â”‚   â”‚   â”‚                   # detected model; prefers tools-capable), Ollama scan
â”‚   â”‚   â””â”€â”€ prompt.py       # agent.md sections + tools -> system prompt
â”‚   â”œâ”€â”€ agents/
â”‚   â”‚   â”œâ”€â”€ loader.py       # Reads agent_library/{id}/agent.md + agent.json
â”‚   â”‚   â”œâ”€â”€ registry.py     # Scans agent_library/ -> available agents
â”‚   â”‚   â””â”€â”€ factory.py      # build_agent(agent_id, model) -> ready Agent
â”‚   â””â”€â”€ agent_library/      # Agent definitions (data, not code)
â”‚       â”œâ”€â”€ basic_chat/
â”‚       â”œâ”€â”€ dev_assistant/
â”‚       â”œâ”€â”€ problem_discovery_agent/
â”‚       â””â”€â”€ rag_assistant/
â”‚
â”œâ”€â”€ tools/                  # Tools available to agents (per-agent capabilities)
â”‚   â”œâ”€â”€ registry.py         # TOOL_REGISTRY: tool IDs -> Python functions
â”‚   â”œâ”€â”€ state.py            # FileSession: shared/persisted file-working state
â”‚   â””â”€â”€ tools.py            # map/read/write/delete + date/time + search tools
â”‚
â”œâ”€â”€ memory/                 # RAG memory store (was "rag/")
â”‚   â”œâ”€â”€ ingest.py           # Transcript chunking (ingest_file / ingest_directory)
â”‚   â”œâ”€â”€ search.py           # RAGStorage: Chroma store + fallback vector DB
â”‚   â”œâ”€â”€ main.py             # Standalone RAG CLI / cognitive loop experiment
â”‚   â””â”€â”€ rag_commit.py       # Commit, purge, rebuild, status for the store
â”‚
â”œâ”€â”€ dashboard/               # Frontend (was "static/")
â”‚   â”œâ”€â”€ index.html          # Main UI shell (agent cards, floating chat)
â”‚   â”œâ”€â”€ chat.html           # Standalone self-contained chat page
â”‚   â”œâ”€â”€ config.html         # NEW: consolidated settings page (one place for
â”‚   â”‚                       #      app defaults, appearance, every agent,
â”‚   â”‚                       #      shared tests, models)
â”‚   â”œâ”€â”€ config/app_settings.json
â”‚   â”œâ”€â”€ css/styles.css
â”‚   â””â”€â”€ js/
â”‚       â”œâ”€â”€ app.js
â”‚       â”œâ”€â”€ config-page.js  # NEW: boot module for config.html
â”‚       â”œâ”€â”€ api/api.js
â”‚       â”œâ”€â”€ classes/ (ChatSession.js, chat-window.js)
â”‚       â”œâ”€â”€ logic/  (models.js, chat-formatter.js)
â”‚       â””â”€â”€ ui/     (markdown.js, agents.js, appearance.js, config-form.js,
â”‚                    agent-editor.js, header-nav.js,
â”‚                    interface-indicator.js,   # header "N updates" pill
â”‚                    interface-manager.js)     # Settings "Updates/Interface" card
â”‚
â”œâ”€â”€ server/                  # Thin glue: FastAPI app + chat log + path config
â”‚   â”œâ”€â”€ server.py            # HTTP endpoints, static mount, lifespan; also
â”‚   â”‚                        # discovers interface/updates at startup and
â”‚   â”‚                        # exposes update_manager + dispatcher on app.state;
â”‚   â”‚                        # /api/interface/{status,apply,snapshot,restore,
â”‚   â”‚                        # run,toggle-run} wire the UI to the update system
â”‚   â”œâ”€â”€ paths.py             # Config-driven runtime path authority (dataDir /
â”‚   â”‚                         # chatSavePath / ragDbPath, incl. per-OS Windows /
â”‚   â”‚                         # Linux / macOS keys + GENESSIS_* env overrides)
â”‚   â””â”€â”€ chat_store/
â”‚       â”œâ”€â”€ logger.py
â”‚       â””â”€â”€ store.py
â”‚
â”œâ”€â”€ config/
â”‚   â””â”€â”€ models.json          # auto-generated model snapshot (the old
â”‚                            # settings.json is gone - one default now lives
â”‚                            # in app_settings.json#defaultAgentId)
â”œâ”€â”€ scripts/
â”‚   â”œâ”€â”€ rebuild_rag.py
â”‚   â”œâ”€â”€ version_chats.py
â”‚   â””â”€â”€ update_docs.py        # NEW: regenerates APP_STRUCTURE.md + APP_CODE_SNAPSHOT.md
â”œâ”€â”€ interface/                # NEW: modular update & restore layer
â”‚   â”œâ”€â”€ update_manager.py     #    discover/import interface/updates/<domain>/*
â”‚   â”œâ”€â”€ interface_dispatcher.py  # trace_and_execute() caller line tracing
â”‚   â”œâ”€â”€ restore_manager.py    #    baseline compare/restore + snapshot_baseline()
â”‚   â””â”€â”€ updates/              #    engine/ | tools/ | server/
â”œâ”€â”€ about/
â”‚   â”œâ”€â”€ about.json           # title/subtitle served by GET /api/about
â”‚   â””â”€â”€ set_title.py         # + 'apply' / 'snapshot' / 'restore' CLI triggers
â”œâ”€â”€ docs/
â”‚   â”œâ”€â”€ CHANGELOG.md
â”‚   â”œâ”€â”€ RESTRUCTURE_README.md
â”‚   â”œâ”€â”€ 01_IDEA_AND_ARCHITECTURE.md   # NEW: design doc for the update/restore layer
â”‚   â”œâ”€â”€ APP_STRUCTURE.md              # AUTO-GENERATED
â”‚   â””â”€â”€ APP_CODE_SNAPSHOT.md          # AUTO-GENERATED
â”œâ”€â”€ current-known-good-copy/ # GENERATED restore baseline (python about/set_title.py snapshot)
â”œâ”€â”€ requirements.txt
â””â”€â”€ README.md                 # Original project README (kept up to date)
```

## Launching

`python server.py` now works from any directory (a `sys.path` bootstrap at the
top of the file adds the project root and drops the script's own folder so the
`server` package is never shadowed). Equivalent launch from the project root:

```
# Windows
venv\Scripts\python -m uvicorn server.server:app

# Linux
venv/bin/python -m uvicorn server.server:app
```

The app is cross-platform (Windows / Linux / macOS / ChromeOS Linux). All
runtime storage is resolved by `server/paths.py` from `dataDir` /
`chatSavePath` / `ragDbPath` (defaults = project-relative `data/`), with
`GENESSIS_DATA_DIR` / `GENESSIS_CHAT_SAVE_PATH` / `GENESSIS_RAG_DB_PATH` env
overrides taking precedence. Windows absolute paths (`E:\...`) saved in
`app_settings.json` are auto-mapped to project-relative folders on non-Windows
OSes, and cleared on save from the Settings page. See the README's "Changing
where data is saved".

> The Agent Monitor feature (`dashboard/monitor.html`, `dashboard/js/monitor.js`,
> `server/activity.py` and the `/api/activity*` endpoints) was removed in
> 2026-09-12. See `docs/CHANGELOG.md`.

> Since 2026-09-12 the app also runs cross-platform: per-OS path overrides
> (`dataDirLinux` / `chatSavePathLinux` / `ragDbPathLinux`) keep one settings
> file working on Windows and Linux, and `engine/core/llm.py` falls back to a
> detected model when a requested one is not installed. See `docs/CHANGELOG.md`.

## What changed under the hood

Every cross-module import was rewritten to match the new folder names:

| Old import | New import |
|---|---|
| `from app.core.agent import Agent` | `from engine.core.agent import Agent` |
| `from app.core.llm import ask_llm` | `from engine.core.llm import ask_llm` |
| `from app.agents.factory import build_agent` | `from engine.agents.factory import build_agent` |
| `from app.tools.registry import resolve_tools` | `from tools.registry import resolve_tools` |
| `from app.tools.state import FileSession` | `from tools.state import FileSession` |
| `from rag.ingest import ingest_directory` | `from memory.ingest import ingest_directory` |
| `from rag.search import RAGStorage` | `from memory.search import RAGStorage` |
| `from app.rag_commit import status` | `from memory.rag_commit import status` |
| `from app.chat_store import store` | `from server.chat_store import store` |
| `from app import paths` | `from server import paths` |

`server/server.py`'s `STATIC_DIR` now points at `dashboard/` instead of
`static/`, and `server/paths.py`'s `APP_SETTINGS_FILE` now points at
`dashboard/config/app_settings.json`.

The dashboard's **Settings** page (`dashboard/config.html` +
`dashboard/js/config-page.js`) consolidates all configuration into one
place: app defaults, appearance, every agent's metadata/behavior/tests
(via `GET/PUT /api/agents/{id}/config`, writing the agent's own
`agent.json` / `agent.md`), the shared test pool, and the model list.

`engine/agents/loader.py`'s `AGENT_LIBRARY_DIR` now resolves to
`engine/agent_library/` (previously the project-root `agent_library/`).

## Verified

- Every `.py` file compiles (`python3 -m py_compile`).
- `engine.agents.registry.list_agents()` runs end-to-end and correctly
  discovers all four agents from `engine/agent_library/`.
- The only remaining import failures are missing third-party packages
  (`ollama`, `chromadb`, `docling`) â€” install with
  `pip install -r requirements.txt`, then run:

  ```
  python -m uvicorn server.server:app --reload
  ```

  (run this from the project root, i.e. the folder containing `server/`,
  `engine/`, `tools/`, `memory/`, `dashboard/`).

## Note on scope

This reorganization is based on `APP_SNAPSHOT.md` (the v1-11 era of your
project â€” before "Genessis Step 1/2" added `app/core/environment.py`,
`app/core/project_creator.py`, `app/contracts/`, and `app/engine/`). If
you want those newer modules folded into this same layout, upload the
current `APP_SNAPSHOT.md` (or the actual project files) for
`app/core/environment.py`, `app/core/project_creator.py`,
`app/contracts/*`, and `app/engine/*`, and I'll fold them in â€” they'd
naturally slot into `engine/` (project provisioning) and a new
`engine/contracts/` (the host class-library contracts) respectively.

## About the "dashboard" idea

The frontend files are copied over as-is (functionally identical, just
relocated). If you want an actual visual refresh â€” nicer typography, a
real dashboard layout with sidebar navigation between agents/memory/tools
status â€” say the word and I'll rework `dashboard/index.html` +
`styles.css` on top of this structure rather than just relocating files.
