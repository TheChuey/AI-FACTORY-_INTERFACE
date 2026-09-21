# GenV1 — Runtime Data Architecture

> **Location:** `docs/architecture/DATA.md`
> **Next:** `docs/architecture/CONFIGURATION.md` · **Prev:** `docs/architecture/MEMORY.md`

## Purpose

Describe where GenV1 stores runtime data at rest: the resolved folders, the
record formats, and which runtime artifacts are durable vs in-memory.

## Responsibilities

- Document every runtime data location resolved by `server/paths.py`.
- Document the on-disk record formats (JSONL, transcript `.txt`, JSON files).
- Distinguish durable records from in-memory state.

## Does Not Own

- How paths are *chosen* (that is `docs/architecture/CONFIGURATION.md`).
- How each file is produced (see the owning subsystem docs).

## Base data folder

`DATA_DIR` defaults to **`agent_monitoring/data/`** (project-relative) and
follows any explicit `dataDir` setting / `GENESSIS_DATA_DIR` env var. The README
often calls the resolved location `data/` generically; the *default* is under
`agent_monitoring/data/`.

## Resolved locations

| Path constant | Default (under DATA_DIR) | Contents |
|---|---|---|
| `CHATS_DIR` | `<DATA_DIR>/chatlog` | `chatRecord.jsonl`, `.active-chat.json`, `pipeline_runs.jsonl` |
| `RECORDS_DIR` / `CHAT_RECORDS_DIR` | `<DATA_DIR>/chatlog/agent-text-records` | one `.txt` per chat (versioned sections); follows `chatSavePath` |
| `RAG_DB_DIR` | `<DATA_DIR>/rag_db` | Chroma store (`chroma.sqlite3`) |
| `CUSTOM_MODULES_DIR` | `<DATA_DIR>/custom_modules` | drop-in `.py` modules |
| `TOOL_LOG_FILE` | `<DATA_DIR>/toollog/tool_usage.jsonl` | append-only tool-usage feed |
| `HISTORY_FILE` | `<DATA_DIR>/history.json` | saved message snapshots |
| `EXPORTS_DIR` | `<DATA_DIR>/exports` | wizard/exporter `{name}.md` + `.json` |
| `LOG_FILE` | `<DATA_DIR>/chatlog/chatRecord.jsonl` | same as `CHATS_DIR` row |
| `ACTIVE_SESSION_FILE` | `<DATA_DIR>/chatlog/.active-chat.json` | per-agent live sessions |
| interface archive | `<DATA_DIR>/interface_archive/<domain>` | retired update modules |
| snapshots | `<DATA_DIR>/snapshots/pre_restore_backup/<stamp>/` | restore backups |
| monitoring | `<DATA_DIR>/monitoring/agent_metrics.jsonl` | telemetry records |
| trace log | `<DATA_DIR>/interface_trace.log` | dispatcher executions |

## Record formats

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

## Processing

Writes are append/finalize oriented: chat turns update the active session;
`finalize_session` writes a transcript section + a log row; tool events append
one JSONL line; restore writes timestamped backups before overwriting.

## Outputs

Durable artifacts consumed by the frontend (history drop-down, logs feed,
settings), by agents (`search_chat_logs`), and by the restore feature.

## Dependencies

- `server/paths.py` (all locations), `server/chat_store/*`.

## Consumers

- Frontend (`dashboard/js/api/api.js`), `scripts/`, restore manager, RAG store.

## Rule

`agent_monitoring/data/`, `venv/`, `.git/`, `app_settings.json`, `about.json`
are excluded from master-copy snapshots/restores and from generated doc walks
(at their conventional locations).

## Failure Behavior

- Loggers are fail-safe: a disk/serialization error never breaks a chat reply
  or tool call.
- Malformed JSONL lines are skipped on read.

## Runtime Flow

```text
Chat turn  -> .active-chat.json (live)          [store]
Chat end   -> {title}.txt  #VERSION N           [store]
             + chatRecord.jsonl row             [logger]
Tool call  -> tool_usage.jsonl line             [tool_log]
Delete chat-> records + every transcript removed [store]
```

## Configuration

Not applicable to this document beyond `server/paths.py` — see
`docs/architecture/CONFIGURATION.md`.

## APIs

Read/modify surfaces: `/api/chats`, `/api/chats/{id}`, `/api/history`,
`/api/exports`, `/api/logs/tools`, `/api/monitoring/records`.

## Source Files

```text
server/paths.py
server/chat_store/store.py
server/chat_store/logger.py
server/tool_log.py
memory/rag_commit.py
```

## Related Documentation

- `docs/architecture/CONFIGURATION.md`
- `docs/architecture/LOGGING.md`
- `docs/reference/API.md`