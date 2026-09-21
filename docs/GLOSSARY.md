# GenV1 — Glossary

> **Location:** `docs/GLOSSARY.md`
> **Next:** `docs/DEPENDENCIES.md`

GenV1 terminology. Alphabetical. Terms are grounded in the source code.

---

## A

### Agent
A runnable Python runtime (think / act / observe), defined entirely by a folder
in `engine/agent_library/<id>/` containing `agent.md` (behavior prose) and
`agent.json` (configuration). The same `Agent` class powers every agent; only
its configuration differs. Source: `engine/core/agent.py`.

### Agent mode
`chat` — user → LLM → response; the factory attaches **no tools**, so no tool
loop can happen. `agent` — user → agent → LLM → tool? → observation → LLM →
response. Stored in `agent.json#mode`.

### Agent id resolution
`engine/agents/loader.py#agent_dir()` finds an agent folder by literal path
first, then by scanning `agent_library/*/agent.json` for a matching `id`. This
is why folder names (`Enginner`, `Builder`) may differ from agent ids
(`execute_engineer_agent`, `module_builder_agent`).

## B

### Bridge (`custom` domain)
`interface/wiring/bridges.py` mirrors every active custom module into the
update manager's catalog under the virtual domain `custom`, making module
functions reachable from core code via
`InterfaceDispatcher().execute_action("custom", <name>, <func>, ...)`.

### Build / factory
`engine/agents/factory.py#build_agent(agent_id, model)` — loads the agent
definition, resolves tools, builds the prompt, and returns a ready `Agent`.

## C

### Chat record
One line in `data/chatlog/chatRecord.jsonl` (referenced by the app as the
"chat log"): id, title, version, fileName, counts, timestamps, model, agent.

### Chat version
A `# VERSION N` section appended to a chat's single `.txt` transcript each time
the active chat is finalized. On name collision the NEXT version is used
(`<title>-2.txt`, ...).

### CONSOLIDATED section
A `# CONSOLIDATED` summary appended to a finalized chat by
`server/chat_store/consolidate.py` when a chat has 2+ versions.

### Custom module / drop-in module
A single standalone `.py` file (default folder `data/custom_modules/`) declaring
`UI_MANIFEST` + `register_routes(app)`. Loaded by
`interface/custom_module_manager.py` with `importlib.util`. Get a scaaffold via
`python about/set_title.py create-module <name>`.

### Custom Modules Path
Configurable folder scanned for drop-in modules; blank = `<dataDir>/custom_modules`;
overridable with `GENESSIS_CUSTOM_MODULES_PATH`.

## D

### Data folder / dataDir
Base runtime data folder. Default `agent_monitoring/data/` (relocated in the
2026-09-18 changelog entry). Resolved by `server/paths.py`: env var → per-OS
key → plain key → default.

### Drift
Live files whose SHA-256 differs from the master copy
(`current-known-good-copy/`). Reported by the restore baseline status.

## F

### FileSession
`tools/state.py` — shared, persisted file-working state
(`discovered_files`, `read_files`, `working_content`, `output_files`,
`pending_deletion`). Injected into agents as a replaceable system message by
`engine/core/agent.py`.

## I

### Interface dispatcher
`interface/interface_dispatcher.py` — `InterfaceDispatcher.trace_and_execute()`
runs a module function with caller file+line traced to
`<dataDir>/interface_trace.log`.

### Interface module / update module
A `.py` file under `interface/updates/<domain>/` (domains: `engine`, `tools`,
`server`) discovered and imported by `interface/update_manager.py`. Executed
directly or via the traced dispatcher.

## M

### Master copy
`current-known-good-copy/` — one published, complete copy of the last good
source. `RestoreManager.snapshot()` publishes it; `restore()` rolls the live
tree back; interface_archive/ stores retired modules.

### Monitor / monitoring
Retired `agent_monitoring/` telemetry subsystem (2026-09-17) whose data folder
(`agent_monitoring/data/`) became the default runtime data location
(2026-09-18). The HTTP endpoints still route via `router.py`; in-memory
session counters reset on restart.

## P

### Pipeline
`engine/pipeline.py` — the 3-step agent chain defined in `config/pipeline.json`
(`feature_planner_agent` → `execute_engineer_agent` → `module_builder_agent`).
Each later step receives the user message plus every earlier step's reply.
Run with `POST /api/chat` (`run_pipeline: true`) or the frontend "Run pipeline"
button.

### Prompt manager
`engine/core/prompt.py` — assembles the system prompt from agent.md sections.

## R

### RAG store
Persistent memory store (`data/rag_db/chroma.sqlite3` by default) built from
saved transcripts. Agents use the `search_chat_logs` tool to recall them.

### Restore
`interface/restore_manager.py` — overlay-restore semantics: differing live
files are backed up to `<dataDir>/snapshots/pre_restore_backup/<stamp>/` then
overwritten; master-only files are added; live-only files are never deleted.

## S

### Skills
`skills/ux_module_designer_skills.md` — atomic implementation skills consumed by
the pipeline's Enginner agent via `read_file`.

### Static dir
The dashboard (`dashboard/`) mounted as `/static`.

## T

### Tool
A Python function registered by ID in `tools/registry.py#_TOOL_REGISTRY`, with a
docstring that serves as the schema the LLM sees.

### Tool event
One structured tool-execution entry collected by `Agent.tool_events` and, for
the persistent feed, written to `<dataDir>/toollog/tool_usage.jsonl` by
`server/tool_log.py`.

### Tool-loop guard
`engine/core/agent.py` — `MAX_TOOL_ROUNDS = 6` caps tool rounds; `REPEAT_LIMIT = 3`
stops identical repeated tool calls with a warning/feedback message.

### Trace log
`<dataDir>/interface_trace.log` — append-only log of dispatcher executions.

## U

### UI_MANIFEST
Data structure a custom module declares to get dashboard header buttons.
Supported action types: `prompt_input`, `dropdown_menu`, `open_modal`,
`qa_survey`, plus the `status_dot` success indicator.

### Update module
See *Interface module*.

## Related documentation

- `docs/INDEX.md`
- `docs/BLUEPRINT.md`
- `docs/reference/AGENT_REFERENCE.md`
- `docs/reference/TOOL_REFERENCE.md`
- `docs/reference/MODULE_REFERENCE.md`