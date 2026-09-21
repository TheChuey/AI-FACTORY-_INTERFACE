# GenV1 — Current State

> **Location:** `docs/living/CURRENT_STATE.md`
> **Next:** `docs/living/KNOWN_ISSUES.md` · **Prev:** `docs/living/CHANGELOG.md`

> Answers: *"If I started working on GenV1 today, what does the application
> currently look like?"*

Last updated: 2026-09-20.

---

## Identity

- **Name:** GenV1 (project root `genV2_Interface_projectManager/`).
- **Purpose:** local lab for building and testing AI agents; FastAPI backend +
  vanilla-JS dashboard + Ollama local LLMs.
- **One-line model:** Agent = reusable Python runtime; behavior = `agent.md`;
  config = `agent.json`; capabilities = registered tools; discovery = filesystem
  scan; construction = factory; frontend = selector.

## Current architecture (at a glance)

```text
server/            FastAPI app + chat store + logs + paths authority
engine/            Agent runtime (think/act/observe) + pipeline + library
tools/             Tool registry (7 tools) + FileSession
memory/            RAG store (Chroma)
interface/         Update modules + traced dispatcher + master-copy restore +
                   custom drop-in modules + wiring bridge
agent_monitoring/  Retired telemetry; its data folder is the default runtime
                   data location
dashboard/         Frontend (index, chat, config, logs pages)
config/            models.json (auto), pipeline.json (3-step chain)
about/             Site identity + title editor / create-module generator
docs/              This documentation system (see docs/INDEX.md)
scripts/           CLI + documentation generators
current-known-good-copy/  master copy for the restore feature
```

## Active subsystems

| Subsystem | Entry file | Notes |
|---|---|---|
| HTTP boundary | `server/server.py` | ~35 endpoints; static mount of `dashboard/` |
| Path/config authority | `server/paths.py` | env → per-OS → plain → default |
| Chat store | `server/chat_store/store.py` | one active session per agent, versioned `.txt` |
| Console capture | `server/console_log.py` | ring buffer, `/api/logs/console` |
| Tool log | `server/tool_log.py` | JSONL + tail, `/api/logs/tools` |
| Agent engine | `engine/core/agent.py` | think/act/observe + loop guard |
| LLM client | `engine/core/llm.py` | fallback model resolution, tools-capability check |
| Prompt builder | `engine/core/prompt.py` | agent.md sections + tool docs |
| Pipeline | `engine/pipeline.py` | 3-step chain from `config/pipeline.json` |
| Registry/loader/factory | `engine/agents/` | id-aware folder lookup |
| Tools | `tools/registry.py` | 7 tools; FileSession; deletion gate |
| RAG | `memory/` | Chroma store; rebuild/purge/status |
| Update modules | `interface/update_manager.py` | `interface/updates/<domain>/` |
| Custom modules | `interface/custom_module_manager.py` | flat `*.py` drop-ins |
| Restore | `interface/restore_manager.py` | one master copy; overlay restore |
| Wiring bridge | `interface/wiring/bridges.py` | virtual `custom` domain |
| Monitoring (retired) | `agent_monitoring/` | HTTP endpoints remain; data dir reused |

## Active agents (4)

| id | name | mode | model | tools |
|---|---|---|---|---|
| `rag_assistant` | RAG Assistant | agent | gemma4:e2b | 6 (files, dates, search) |
| `feature_planner_agent` (folder `Planner/`) | Feature Planner Agent | chat | qwen2.5-coder:latest | none |
| `execute_engineer_agent` (folder `Enginner/`) | Execute Engineer Agent | agent | qwen2.5-coder:latest | read_file |
| `module_builder_agent` (folder `Builder/`) | Module Builder Agent | agent | qwen2.5-coder:latest | map/read/write |

Pipeline: `feature_planner_agent` → `execute_engineer_agent` →
`module_builder_agent` (module-generation chain).

## Active tools (7)

`map_files`, `read_file`, `write_text_file`, `delete_files`,
`get_current_date`, `tell_me_the_date_and_time`, `search_chat_logs`.

## Current data locations (defaults)

- Base data folder: `agent_monitoring/data/` (overridable).
- Chats: `<dataDir>/chatlog/agent-text-records/*.txt`.
- Chat log: `<dataDir>/chatlog/chatRecord.jsonl`.
- Tool usage: `<dataDir>/toollog/tool_usage.jsonl`.
- RAG store: `<dataDir>/rag_db/chroma.sqlite3`.
- History: `<dataDir>/history.json`. Exports: `<dataDir>/exports/`.
- Custom modules: `<dataDir>/custom_modules/`.
- Interface archive: `<dataDir>/interface_archive/`.
- Restore backups: `<dataDir>/snapshots/pre_restore_backup/`.
- Monitoring: `<dataDir>/monitoring/agent_metrics.jsonl`.
- Master copy: `current-known-good-copy/`.

## Current configuration

- Settings file: `dashboard/config/app_settings.json` (paths + per-OS keys +
  `rag`, `defaultAgentId`, chat tests, versioning/header flags).
- Env vars: `GENESSIS_DATA_DIR`, `GENESSIS_CHAT_SAVE_PATH`,
  `GENESSIS_RAG_DB_PATH`, `GENESSIS_CUSTOM_MODULES_PATH`, `GENESSIS_PLATFORM`.
- Models: `config/models.json` (auto-scanned from Ollama at boot).
- Pipeline: `config/pipeline.json`.
- Server: `PORT` (default 8000), `HOST` (default 127.0.0.1).

## Current API surface

35 endpoints under `/api/*` — see `docs/reference/API.md`. Highlights:
`/api/chat`, `/api/chats/*`, `/api/agents/*`, `/api/models`, `/api/tools`,
`/api/pipeline`, `/api/rag/*`, `/api/logs/*`, `/api/settings`, `/api/about`,
`/api/history`, `/api/discussions`, `/api/exports`,
`/api/interface/{status,apply,snapshot,restore,run,toggle-run}`.

## Current documentation system

- Entry point: `docs/INDEX.md` (path-annotated map + reading order).
- Generated: `docs/generated/APP_STRUCTURE.md`, `docs/generated/APP_CODE_SNAPSHOT.md`.
- Regenerable with `venv\Scripts\python scripts\update_documentation.py`.
- Living docs (`docs/living/`) are hand-maintained and never auto-overwritten.

## Current known limitations

- Tool-usage HTTP round-trip still not re-verified on a free port (stalled by a
  port-8000 conflict; see `docs/living/KNOWN_ISSUES.md`).
- `agent_monitoring/` telemetry is retained but considered retired; in-memory
  counters reset on restart.
- `interface/updates/` domains currently hold only `__init__.py` (seeded
  examples were archived) — the loader handles an empty catalog.
- No packaged test suite; verification is per-file `py_compile`/`node --check`
  + manual/tool smoke checks.

## Related documentation

- `docs/INDEX.md`
- `docs/living/CHANGELOG.md`
- `docs/living/KNOWN_ISSUES.md`
- `docs/living/TODO.md`