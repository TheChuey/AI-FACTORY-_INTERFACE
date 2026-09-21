# GenV1 — Blueprint

> **Location:** `docs/BLUEPRINT.md`
>
> Master architectural blueprint. Assembled by `scripts/update_blueprint.py` from the maintained documents in `docs/architecture/` — sections are extracted verbatim, nothing is invented. Contract and required sections: `docs/BLUEPRINT_SPEC.md`.

---

## What GenV1 is

Describe GenV1 at the system level: what it is, its layers, its major
components, how requests flow through it, how it is extended, where data goes,
and how its documentation is maintained.

## Architecture (Layers)

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

## Extension Model

- **New agents**: add `engine/agent_library/<id>/agent.md` + `agent.json`.
- **New tools**: add to `tools/tools.py` + register in `tools/registry.py`.
- **Update modules**: drop `.py` into `interface/updates/<domain>/`.
- **Custom modules**: drop a `UI_MANIFEST` + `register_routes(app)` `.py` into
  the Custom Modules Path.
- **Pipeline**: edit `config/pipeline.json` step ids.

## Data Flow

- **Chat record** (`chatRecord.jsonl`, one line per chat version): `id`,
  `title`, `version`, `fileName`, `status`, `messageCount`,
  `interactionCount`, `startedAt`, `endedAt`, `model`, `agent`, `agentId`,
  `agentName`, `tags`.
- **Transcript** (`.txt`): single file per chat with `# VERSION N` and
  `# CONSOLIDATED` sections; optional CAPS metadata header block.
- **Active session** (`.active-chat.json`): `{agentId: session}` map.
- **Tool usage** (`tool_usage.jsonl`): `{time, agentId, agentName, model, tool,
  args, status}` + optional `error`/`result_preview`/`op_ok`/`op_error`/`origin`.
- **Settings** (`dashboard/config/app_settings.json`): frontend-owned defaults
  including per-OS path keys.
- **Pipeline runs** (`pipeline_runs.jsonl`): history of pipeline executions.

## Durable vs in-memory

- Durable: JSONL/JSON/`.txt` above, RAG store, master copy
  (`current-known-good-copy/`), generated docs.
- In-memory only: `Agent.messages` (per request), `FileSession`
  (`tools/state.py`), telemetry session counters, console ring buffer
  (`server/console_log.py`), tool-log tail buffer (seeded from disk).

## Configuration

- `server/paths.py` — constants, resolution functions, `about()` report,
  `restart_needed()`, `rag_config()`.
- `dashboard/config/app_settings.json` — the stored settings file.

## Inputs

- `dashboard/config/app_settings.json`
- Environment variables (`GENESSIS_DATA_DIR`, `GENESSIS_CHAT_SAVE_PATH`,
  `GENESSIS_RAG_DB_PATH`, `GENESSIS_CUSTOM_MODULES_PATH`,
  `GENESSIS_PLATFORM`).
- OS detection (`platform()`: `win` / `linux` / `mac`).

## Processing — precedence chain

For each path setting, from highest to lowest:

```text
1. Environment variable (GENESSIS_*)             [highest]
2. Per-OS key for the current platform          (dataDirWindows/Linux/Mac)
3. Plain key                                    (dataDir)
4. Project-relative default                     (agent_monitoring/data)
```

Details:

- Env values pass through `expanduser`/`expandvars` (`~` and `$VAR` expand).
- Relative values resolve against the project root (`BASE_DIR`).
- Absolute values are used as-is.
- A Windows drive path (`E:\...`, `\\server\share`) in the *plain* key is
  ignored on non-Windows hosts so a literal `E:\...` folder is never created.
- Path changes need a **server restart**; `restart_needed()` compares the
  stored keys against a snapshot taken at import time.

## Outputs

- Path constants used across the app (see `docs/architecture/DATA.md`).
- `paths.about()` exposed via `GET /api/settings` and `/api/rag/status`
  (including `platform` and the per-key override `sources` map).
- `rag_config()` (`{commitOnSave, autoIngest}`).

## Dependencies

- `dashboard/config/app_settings.json`; Python `os`/`pathlib`.

## Consumers

- Every logger, store, the chat store, memory, the interface layer, and the
  frontend settings page.

## Extension Points

- New path settings: add a key + env var + resolved constant in
  `server/paths.py`, expose in `about()`, surface in
  `dashboard/js/ui/config-form.js`.

## Rules

- `GENESSIS_*` env-var names are **compatibility identifiers** and are kept
  even though the documentation identity is GenV1.
- Stored path values are not rewritten by `GET/POST /api/settings` (merges
  only).

## Failure Behavior

- Blank env vars are ignored; missing files fall back to defaults gracefully.
- Unknown models/config keys never break boot.

## Logging

| Channel | Implementation | Storage |
|---|---|---|
| Console capture | `server/console_log.py` | in-memory ring buffer (500 lines), exported via `GET /api/logs/console` |
| Tool usage | `server/tool_log.py` | `<dataDir>/toollog/tool_usage.jsonl` + in-memory tail (1000), `GET /api/logs/tools` |
| Interface trace | `interface/interface_dispatcher.py` | `<dataDir>/interface_trace.log` |
| Monitoring telemetry | `agent_monitoring/` (retired) | `<dataDir>/monitoring/agent_metrics.jsonl`, `/api/monitoring/*` |
| Chat store log | `server/chat_store/logger.py` | `chatRecord.jsonl` |

## Major Components

Every subsystem documented under `docs/architecture/`: its purpose, extracted verbatim from its architecture document.

### Agents

Source: `docs/architecture/AGENTS.md`

Describe the agent engine: the reusable think/act/observe runtime, the prompt
builder, the loaders/registry/factory, the tool-loop guard, and the 3-step
pipeline.

### Backend

Source: `docs/architecture/BACKEND.md`

Describe the FastAPI backend: the HTTP boundary, the chat store, the console
and tool logs, and how the backend wires the rest of GenV1 at startup.

### Configuration

Source: `docs/architecture/CONFIGURATION.md`

Describe the single path/config authority (`server/paths.py`): which settings
exist, how they resolve, and which environment variables override them.

### Data

Source: `docs/architecture/DATA.md`

Describe where GenV1 stores runtime data at rest: the resolved folders, the
record formats, and which runtime artifacts are durable vs in-memory.

### Frontend

Source: `docs/architecture/FRONTEND.md`

Describe the dashboard frontend: the pages served, the JS module layout, and
how UI actions (header buttons, modals, menu dropdowns, status dots) are
driven by custom-module manifests.

### Interface

Source: `docs/architecture/INTERFACE.md`

Describe the modular interface layer: update modules, the traced dispatcher,
the restore/master-copy manager, drop-in custom modules, and the wiring bridge
that connects the two.

### Logging

Source: `docs/architecture/LOGGING.md`

Describe every logging/telemetry channel in GenV1: console capture, structured
tool usage, the interface trace log, and the retired monitoring telemetry.

### Memory

Source: `docs/architecture/MEMORY.md`

Describe the RAG memory store: transcript ingestion, Chroma-backed search, and
the memory endpoints/CLI.

### System

Source: `docs/architecture/SYSTEM.md`

Describe GenV1 at the system level: what it is, its layers, its major
components, how requests flow through it, how it is extended, where data goes,
and how its documentation is maintained.

### Tools

Source: `docs/architecture/TOOLS.md`

Describe the tool system: the registry (ID → function), the shared
`FileSession` state, and the tool implementations, including the deletion
safety gate.

## Documentation Flow

GenV1's documentation is its own subsystem: `docs/INDEX.md` is the navigation map, the 10 documents in `docs/architecture/` describe the subsystems, `docs/reference/*` lists concrete files/APIs/agents/tools/modules/workflows, `docs/development/*` explains extension and documentation discipline, and `docs/living/*` records the changelog, current state, known issues, planned work and decisions. Two documents are generated output: `docs/generated/APP_STRUCTURE.md` (filesystem tree) and `docs/generated/APP_CODE_SNAPSHOT.md` (source snapshot), produced by `scripts/update_docs.py`. `scripts/update_documentation.py` is the preferred entry point: it regenerates the generated docs, validates references against the live tree, assembles this blueprint, and reports status. Living documents (`docs/living/*`) are never overwritten by automation.

---

## Related documentation

- `docs/INDEX.md`
- `docs/BLUEPRINT_SPEC.md` — the contract this document must satisfy
- `docs/architecture/SYSTEM.md` — system overview source
- `scripts/update_blueprint.py` — the assembler
- `docs/development/DOCUMENTATION_RULES.md`
