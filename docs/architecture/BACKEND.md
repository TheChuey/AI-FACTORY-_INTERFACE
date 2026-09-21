# GenV1 — Backend Architecture

> **Location:** `docs/architecture/BACKEND.md`
> **Next:** `docs/architecture/FRONTEND.md` · **Prev:** `docs/architecture/SYSTEM.md`

## Purpose

Describe the FastAPI backend: the HTTP boundary, the chat store, the console
and tool logs, and how the backend wires the rest of GenV1 at startup.

## Responsibilities

- Own `server/server.py`, the only component the browser talks to.
- Serve the HTTP API (see `docs/reference/API.md`).
- Track **one active chat session per agent** and finalize chats into
  versioned `.txt` transcripts + `chatRecord.jsonl`.
- Resolve all runtime paths via `server/paths.py` (see
  `docs/architecture/CONFIGURATION.md`).
- Capture console output and tool-usage events.
- Wire the engine, module loaders and telemetry at startup (lifespan).

## Does Not Own

- The agent runtime (that is `engine/`).
- Tool implementations (that is `tools/`).
- The RAG store (that is `memory/`).
- The frontend rendering (that is `dashboard/`).

## Components

- `server/server.py` — FastAPI app; `lifespan()`; all endpoints; static mount
  of `dashboard/`; pydantic request models.
- `server/paths.py` — path/config authority (see CONFIGURATION doc).
- `server/chat_store/store.py` — session/record/transcript lifecycle.
- `server/chat_store/logger.py` — append-only JSONL chat index (`ChatLogger`).
- `server/chat_store/consolidate.py` — AI consolidation of multi-version chats.
- `server/console_log.py` — ring-buffer capture of stdout/stderr + logging.
- `server/tool_log.py` — append-only JSONL tool-usage log.

## Inputs

- HTTP requests (JSON bodies for chat, settings, interface actions, etc.).
- `dashboard/config/app_settings.json` (settings), `about/about.json`
  (identity), `config/models.json` + Ollama scan.

## Processing

- `POST /api/chat`: build agent → ensure session → `agent.think(message)` →
  append turn → return `{reply, session_id, title, tool_events}`. With
  `run_pipeline: true` it runs `engine.pipeline.run_pipeline(...)` instead.
- `POST /api/chats/end`: finalize active chat → appended `# VERSION N` section
  → `ChatLogger` row → optional RAG commit.
- Boot (`lifespan`): `refresh_models()` (Ollama → `config/models.json`),
  `chat_store.import_once()`, build `UpdateManager` + `InterfaceDispatcher`,
  wire custom modules (`WiringManager`). Fail-soft everywhere.

## Outputs

- JSON replies, `chatRecord.jsonl` rows, `.txt` transcripts, tool-usage JSONL,
  console log tail, settings/platform/restart-need flags.

## Dependencies

- `engine/`, `tools/`, `memory/`, `interface/`, `agent_monitoring/`.
- FastAPI, uvicorn, pydantic (see `docs/DEPENDENCIES.md`).

## Consumers

- `dashboard/` frontend (all pages), `scripts/`, AI agents via the API.

## Extension Points

- HTTP endpoints are added in `server/server.py` (or by custom modules via
  `register_routes(app)`).
- New chat-store record types follow `RECORD_KEYS`.

## Rules

- `/api/chat` is intentionally **sync** so blocking LLM calls run in FastAPI's
  threadpool.
- The workspace static dir is `dashboard/` mounted at `/static`.
- Path-changing settings need a server restart (`restart_needed()`).

## Failure Behavior

- Unknown agent ids return an error string in the reply, not a crash.
- Legacy `/api/chat-save` falls back to a raw-blob write when no active session
  exists; the output dir is sandboxed inside `BASE_DIR`.
- Module reload failures return 500 with the module skipped.

## Runtime Flow

```text
Browser
  ↓ POST /api/chat
server.py
  ↓ chat_store.ensure_session()
  ↓ build_agent(agent_id, model)          engine/agents/factory.py
  ↓ Agent.think(message)                  engine/core/agent.py
  ↓ ask_llm()                             engine/core/llm.py -> Ollama
  ↓ append_turn()                         server/chat_store/store.py
  ↓ {reply, session_id, title, tool_events}
```

## Configuration

- Settings keys (`dataDir`, `chatSavePath`, `ragDbPath`, `customModulesPath`,
  `rag`, `defaultAgentId`, `disableVersioning`, `metadataHeader`) — resolved by
  `server/paths.py`, stored in `dashboard/config/app_settings.json`.
- `PORT` (default 8000) / `HOST` env vars.

## APIs

Full endpoint list: `docs/reference/API.md`.

## Source Files

```text
server/server.py
server/paths.py
server/console_log.py
server/tool_log.py
server/chat_store/store.py
server/chat_store/logger.py
server/chat_store/consolidate.py
```

## Related Documentation

- `docs/architecture/CONFIGURATION.md`
- `docs/architecture/DATA.md`
- `docs/architecture/LOGGING.md`
- `docs/reference/API.md`
- `docs/reference/FILES.md`