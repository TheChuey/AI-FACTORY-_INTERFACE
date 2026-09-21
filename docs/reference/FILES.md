# GenV1 — File Map

> **Location:** `docs/reference/FILES.md`
> **Next:** `docs/reference/API.md`

Important files and their responsibilities. This is a curated map — the
complete filesystem snapshot is `docs/generated/APP_STRUCTURE.md`.

---

## Backend (`server/`)

### `server/server.py`
```text
Purpose:
Main FastAPI application and API routing.

Responsibilities:
- All /api/* endpoints (see docs/reference/API.md).
- lifespan() wiring: models refresh, chat-store import, interface managers.
- Static mount of dashboard/; module execution switch (INTERFACE_RUN_ENABLED).
- Legacy /api/chat-save fallback, exports, chat-store integration.

Used by:   the browser (all pages); scripts via subprocess for docs regen.
Related:   server/chat_store/*, server/paths.py, engine/*, interface/*.
```

### `server/paths.py`
```text
Purpose:
Config-driven runtime path authority.

Responsibilities:
- Resolve dataDir / chatSavePath / ragDbPath / customModulesPath.
- Per-OS keys + GENESSIS_* env overrides + Windows drive-path guard.
- restart_needed(), platform(), rag_config(), about().

Used by:   every logger/store; GET /api/settings; GET /api/rag/status.
Related:   dashboard/config/app_settings.json.
```

### `server/chat_store/store.py`
```text
Purpose:
Server-side chat session + transcript lifecycle.

Responsibilities:
- ensure_session / append_turn / finalize_session; one active chat per agent.
- Versioned .txt transcripts (# VERSION N / # CONSOLIDATED).
- create/read/delete chat records; import_once() boot migration.

Used by:   server/server.py; POST /api/chats/end.
Related:   server/chat_store/logger.py, consolidate.py.
```

### `server/chat_store/logger.py`
```text
Purpose:
Append-only JSONL chat index (ChatLogger).

Responsibilities:
- add/update/replace_all/add_missing/prune/remove/get/list_all.
- Shared RECORD_KEYS schema; optional CAPS metadata header.

Used by:   store.py.
```

### `server/chat_store/consolidate.py`
```text
Purpose:
AI consolidation of multi-version chats into a # CONSOLIDATED section.

Responsibilities:
- consolidate_chat(chat_id) via ask_llm; never mutates on failure.

Used by:   server/server.py (POST /api/chats/consolidate).
```

### `server/console_log.py`
```text
Purpose:
Ring-buffer capture of stdout/stderr + logging (500 lines).

Responsibilities:
- install() tees sys.stdout/stderr, strips ANSI, adds a root logger handler.
- tail() / captured().

Used by:   logs.html; the chat console drawer.
```

### `server/tool_log.py`
```text
Purpose:
Append-only structured tool-usage log.

Responsibilities:
- append() -> <dataDir>/toollog/tool_usage.jsonl + in-memory tail.
- tail(limit, tool, agent, since); seeded from disk at import.

Used by:   engine/core/agent.py; GET /api/logs/tools.
```

## Engine (`engine/`)

### `engine/core/agent.py`
```text
Purpose:
The reusable Agent runtime: think/act/observe.

Responsibilities:
- think(): LLM round-trip + tool rounds (MAX_TOOL_ROUNDS=6, REPEAT_LIMIT=3).
- act()/observe(): run tools, record tool_events, forward to tool_log.
- Session-context injection; text tool-call extraction fallback.

Used by:   factory.build_agent(); /api/chat; consolidate.py.
```

### `engine/core/llm.py`
```text
Purpose:
Ollama client + model resolution.

Responsibilities:
- ask_llm(); model fallback (warn + first detected); tools-capability check.
- Context window cap (MAX_NUM_CTX=32768); scan/refresh_models() -> config/models.json.

Used by:   agent.py, consolidate.py.
```

### `engine/core/prompt.py`
```text
Purpose:
PromptManager: agent.md sections + tools -> system prompt.

Used by:   factory.build_agent().
```

### `engine/agents/loader.py`
```text
Purpose:
Read/parse agent_library/{id}/agent.md + agent.json; id-aware folder lookup.

Used by:   registry, factory, server (agent config endpoints).
```

### `engine/agents/registry.py`
```text
Purpose:
Scan agent_library/ -> available agents. Used by: /api/agents.
```

### `engine/agents/factory.py`
```text
Purpose:
build_agent(agent_id, model): definition -> tools -> prompt -> Agent.
Session-aware tool wrappers + deletion safety gate + grounding block.

Used by:   /api/chat, pipeline.py.
```

### `engine/pipeline.py`
```text
Purpose:
3-step agent chain from config/pipeline.json; run_pipeline() records to
<dataDir>/chatlog/pipeline_runs.jsonl.

Used by:   /api/chat (run_pipeline).
```

## Tools (`tools/`)

### `tools/registry.py`
```text
Purpose:
Central tool registry (ID -> callable), resolve_tools, get_session.
Related:   tools/tools.py, tools/state.py.
```

### `tools/tools.py`
```text
Purpose:
The 7 tool implementations (docstrings are the LLM schema).

Used by:   registry.py -> Agent.act().
```

### `tools/state.py`
```text
Purpose:
FileSession: shared/persisted file-working state for agents.
```

## Interface (`interface/`)

### `interface/update_manager.py`
```text
Purpose:
UpdateManager: discover/import interface/updates/<domain>/*.py; archive.
Related:   interface/updates/{engine,tools,server}/.
```

### `interface/interface_dispatcher.py`
```text
Purpose:
InterfaceDispatcher: trace_and_execute / execute_action with caller tracing
to <dataDir>/interface_trace.log.
```

### `interface/restore_manager.py`
```text
Purpose:
RestoreManager: ONE master copy (current-known-good-copy/) — snapshot() /
status() / restore(); SHA-256 diff; pre-restore backups; docs regeneration.
```

### `interface/custom_module_manager.py`
```text
Purpose:
CustomModuleManager: flat-folder .py loader (Custom Modules Path),
active_modules_catalog, ui_manifests(), reload_all().
```

### `interface/wiring/bridges.py`
```text
Purpose:
CustomModuleBridge: register_routes(app) once per process; mirror custom
modules into the update catalog under the virtual 'custom' domain.
Related:   interface/wiring/__init__.py (rewire).
```

## Memory (`memory/`)

- `memory/ingest.py` — transcript chunking.
- `memory/search.py` — RAGStorage (Chroma + fallback).
- `memory/rag_commit.py` — status / rebuild_store / purge_store.
- `memory/main.py` — standalone RAG CLI.

## Monitoring (`agent_monitoring/`)

- `store.py` — MonitoringStore (fail-safe JSONL).
- `collector.py` — MetricsCollector (in-memory session/turn metrics).
- `backup.py` — BackupManager (snapshots + exports).
- `manager.py` — MonitoringService facade + singleton.
- `router.py` — APIRouter -> /api/monitoring/*.

## Frontend (`dashboard/`)

- `index.html` — UI shell (agent cards + floating chat widget).
- `chat.html` — standalone self-contained chat page.
- `config.html` — consolidated settings page.
- `logs.html` — console + tool-usage viewer.
- `js/api/api.js` — all HTTP calls.
- `js/app.js` — index.html boot module.
- `js/config-page.js` — config.html boot module.
- `js/logs-page.js` — logs.html boot module.
- `js/classes/chat-window.js` — widget UI (console drawer, resize, fullscreen).
- `js/classes/ChatSession.js` — chat state.
- `js/classes/terminal-window-out.js` — formatting/filtering shared.
- `js/logic/models.js` — model dropdown.
- `js/logic/chat-formatter.js` — message formatting.
- `js/ui/` — markdown, appearance, config-form, agents, agent-editor,
  header-nav (renderDynamicHeaderButtons), interface-indicator,
  interface-manager.
- `css/styles.css` — all styles.
- `config/app_settings.json` — frontend-owned settings storage.

## Config / identity

- `config/models.json` — auto-generated at startup from installed Ollama models.
- `config/pipeline.json` — the 3-step agent chain config.
- `about/about.json` — site identity (title + subtitle), `GET /api/about`.
- `about/set_title.py` — title editor + `create-module` generator + retired
  apply/snapshot/restore CLI.

## Scripts

- `scripts/update_docs.py` — generates `docs/generated/APP_STRUCTURE.md` +
  `docs/generated/APP_CODE_SNAPSHOT.md`.
- `scripts/update_blueprint.py` — assembles `docs/BLUEPRINT.md`.
- `scripts/update_documentation.py` — preferred docs update entry point.
- `scripts/rebuild_rag.py` — RAG build/purge/status.
- `scripts/version_chats.py` — chat versioning list/import/bump/on/off.

## Roots / leaves

- `current-known-good-copy/` — generated master copy (restore baseline).
- `agent_monitoring/data/` — default runtime data folder (runtime only).
- `README.md` — user quickstart (points to this docs tree).
- `requirements.txt` — Python dependencies.
- `.gitignore` — excludes runtime data, venv, known-good copy, drive paths.

## Related documentation

- `docs/generated/APP_STRUCTURE.md` (full tree)
- `docs/generated/APP_CODE_SNAPSHOT.md` (source)
- `docs/reference/API.md`