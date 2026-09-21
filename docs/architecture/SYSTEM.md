# GenV1 — System Architecture (Overview)

> **Location:** `docs/architecture/SYSTEM.md`
> **Next:** `docs/architecture/BACKEND.md` · **Prev:** `docs/BLUEPRINT.md`

## Purpose

Describe GenV1 at the system level: what it is, its layers, its major
components, how requests flow through it, how it is extended, where data goes,
and how its documentation is maintained.

## Responsibilities

- Give a whole-system mental model before reading any subsystem doc.
- Name every subsystem and its entry file.
- Show the primary runtime flow (user → frontend → API → backend → agent →
  LLM → tool → observation → response → logging).
- Show the extension model (agents, tools, update modules, custom modules).

## Does Not Own

- Per-component detail (see each subsystem doc under `docs/architecture/`).
- Endpoint-by-endpoint catalogue (see `docs/reference/API.md`).

## Components

```text
server/            FastAPI app, HTTP endpoints, chat store, console/tool logs,
                   paths authority, lifespan wiring (the ONLY thing the browser
                   talks to).
engine/            Agent engine: think/act/observe loop (engine/core/agent.py),
                   LLM client (engine/core/llm.py), prompt builder
                   (engine/core/prompt.py), loaders/registry/factory
                   (engine/agents/), the 3-step pipeline (engine/pipeline.py),
                   and the agent library (engine/agent_library/*).
tools/             Tool registry (ID -> function), FileSession state, tool
                   implementations.
memory/            RAG memory: ingest, Chroma search, rebuild/reset CLI logic.
interface/         Update modules, traced dispatcher, restore/master-copy
                   manager, custom drop-in module loader, wiring bridge.
agent_monitoring/  Retired telemetry package; its data folder is the default
                   runtime data location. Monitoring HTTP endpoints remain.
dashboard/         Frontend: index/chat/config/logs pages + JS modules.
config/            models.json (auto-scanned), pipeline.json (agent chain).
about/             Site identity (about.json) + title editor / module generator.
scripts/           CLI utilities incl. the documentation generators.
current-known-good-copy/  Generated master copy for the restore feature.
data/ (runtime)    chat transcripts, chat record log, toollog, RAG store,
                   history, exports, snapshots, custom modules, interface
                   archive, interface trace log. Under agent_monitoring/data/.
docs/              This documentation system.
```

## Inputs

- Human chat messages from the dashboard (`POST /api/chat`).
- Ollama local models (the LLM runtime).
- Settings/config written to `dashboard/config/app_settings.json`.
- Drop-in custom module files and update module files on disk.

## Processing

Layered processing: the browser issues HTTP requests; `server/server.py` builds
an `Agent` (factory), which runs its think/act/observe loop against Ollama,
optionally calling registered tools; results are appended to the server-side
chat session; logs capture console output, tool usage and interface-trace
events; saved chats may be committed to the RAG store.

## Outputs

- Chat replies (`{reply, session_id, title, tool_events}`; pipeline mode adds
  `pipeline.outputs`).
- Versioned `.txt` transcripts + `chatRecord.jsonl` rows.
- Tool-usage JSONL feed, console log tail, interface trace log, telemetry
  records (monitoring).
- RAG store embeddings, exports, generated docs snapshots.

## Dependencies

- Ollama (LLM backend); FastAPI/uvicorn; the packages in `docs/DEPENDENCIES.md`.

## Consumers

- Human users of the dashboard.
- AI agents built on the same runtime.
- AI documentation agents reading this `docs/` tree.

## Extension Points

- **New agents**: add `engine/agent_library/<id>/agent.md` + `agent.json`.
- **New tools**: add to `tools/tools.py` + register in `tools/registry.py`.
- **Update modules**: drop `.py` into `interface/updates/<domain>/`.
- **Custom modules**: drop a `UI_MANIFEST` + `register_routes(app)` `.py` into
  the Custom Modules Path.
- **Pipeline**: edit `config/pipeline.json` step ids.

## Rules

- Source-of-truth order: running code → config → filesystem → tests →
  generated snapshots → architecture docs → README → changelog.
- The agent runtime is a single reusable class; behavior is data
  (`agent.md`), configuration is JSON (`agent.json`).
- Module execution (`/api/interface/run`) is disabled unless armed.

## Failure Behavior

- A broken update/custom module never blocks server boot (logged, skipped).
- Telemetry and logging are fail-safe: they never break a reply or tool call.
- An uninstalled requested model falls back to a detected model.
- The tool loop is bounded (`MAX_TOOL_ROUNDS = 6`, `REPEAT_LIMIT = 3`).

## Runtime Flow

```text
User
 ↓
Frontend (dashboard/)                POST /api/chat
 ↓
API (server/server.py)
 ↓
Backend (server/)                    chat_store, factory
 ↓
Agent (engine/core/agent.py)         think() -> ask_llm()
 ↓
LLM (Ollama)
 ↓
Tool? (tools/)                       act() -> observe()
 ↓
Observation                          (tool result fed back to the LLM)
 ↓
Response                             appended to chat session, returned
 ↓
Logging                              console_log / tool_log / trace / telemetry
```

## Configuration

See `docs/architecture/CONFIGURATION.md` and `server/paths.py`.

## APIs

The system exposes the HTTP API documented in `docs/reference/API.md`.

## Source Files

```text
server/server.py
server/paths.py
engine/core/agent.py
engine/core/llm.py
engine/core/prompt.py
engine/pipeline.py
tools/registry.py
interface/update_manager.py
interface/custom_module_manager.py
```

## Related Documentation

- `docs/INDEX.md`
- `docs/BLUEPRINT.md`
- `docs/architecture/BACKEND.md`
- `docs/reference/WORKFLOWS.md`