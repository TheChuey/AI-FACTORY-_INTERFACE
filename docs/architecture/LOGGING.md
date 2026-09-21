# GenV1 — Logging Architecture

> **Location:** `docs/architecture/LOGGING.md`
> **Next:** `docs/reference/FILES.md` · **Prev:** `docs/architecture/CONFIGURATION.md`

## Purpose

Describe every logging/telemetry channel in GenV1: console capture, structured
tool usage, the interface trace log, and the retired monitoring telemetry.

## Responsibilities

- Capture the server's console output (stdout/stderr + the root logger) for
  the chat console drawer and the logs page.
- Record every tool call an agent makes as a structured, restart-surviving
  feed.
- Trace module executions (caller file + line).
- Record per-turn agent telemetry (monitoring, HTTP boundary only).

## Does Not Own

- The chat transcript log (`chatRecord.jsonl`) — that is the chat store
  (`docs/architecture/BACKEND.md`).

## Components

| Channel | Implementation | Storage |
|---|---|---|
| Console capture | `server/console_log.py` | in-memory ring buffer (500 lines), exported via `GET /api/logs/console` |
| Tool usage | `server/tool_log.py` | `<dataDir>/toollog/tool_usage.jsonl` + in-memory tail (1000), `GET /api/logs/tools` |
| Interface trace | `interface/interface_dispatcher.py` | `<dataDir>/interface_trace.log` |
| Monitoring telemetry | `agent_monitoring/` (retired) | `<dataDir>/monitoring/agent_metrics.jsonl`, `/api/monitoring/*` |
| Chat store log | `server/chat_store/logger.py` | `chatRecord.jsonl` |

## Inputs

- Module `print()` output and `logging` records (console capture).
- `Agent.act()` calls (tool usage).
- Dispatcher executions (trace).
- Per-turn agent duration/tool counts (telemetry).

## Processing

- **Console**: `install()` tees `sys.stdout`/`sys.stderr` through `_Tee`,
  strips ANSI escapes, and adds a root `logging.Handler`. Idempotent at import.
- **Tool log**: `append(event)` normalizes one JSONL line under a lock;
  `tail(limit, tool, agent, since)` serves newest-first with filters. The tail
  is seeded from disk at import so restarts keep recent history without
  duplicating events.
- **Trace**: `execute_action`/`trace_and_execute` log
  `file:line -> module.function` to the trace file.
- **Monitoring**: `MetricsCollector` tracks in-memory active sessions and
  cumulative turns; `MonitoringStore` persists JSONL fail-safe; `safe_reset()`
  snapshots before clearing.

## Outputs

- `GET /api/logs/console`, `GET /api/logs/tools`, trace-log tail in
  `GET /api/interface/status`, `/api/monitoring/status|records`.

## Dependencies

- `server/paths.py` (log file locations), `engine/core/agent.py` (tool events).

## Consumers

- `dashboard/logs.html`, the chat-window console drawer, the Settings
  Updates/Interface card (trace tail).

## Extension Points

- New feeds follow the JSONL + in-memory tail pattern
  (`server/tool_log.py` is the template).
- New log viewers are standalone pages under `dashboard/` polling
  `/api/logs/*`.

## Rules

- All loggers are **fail-safe**: a disk/serialization/emit error never breaks
  a chat reply or tool call.
- ANSI escape sequences are stripped at capture and defensively at render.
- In-memory counters reset on restart; durable records live in the JSONL files.

## Failure Behavior

- Malformed JSONL lines are skipped on read.
- Capture not installed → logs simply show as not captured.
- Port conflicts cannot crash the app (see `docs/living/KNOWN_ISSUES.md`).

## Runtime Flow

```text
Tool call        -> _log_tool_event -> tool_log.append -> JSONL + tail
Server boot/dev  -> console_log.install -> ring buffer
Module execution -> trace_and_execute -> interface_trace.log
Chat turn        -> monitoring collector -> agent_metrics.jsonl
Viewer           -> logs.html polls /api/logs/console|tools
```

## Configuration

Log locations follow `DATA_DIR` via `server/paths.py` (no separate settings).

## APIs

- `GET /api/logs/console`
- `GET /api/logs/tools`
- `GET /api/monitoring/status`, `GET /api/monitoring/records`,
  `POST /api/monitoring/export|reset`

## Source Files

```text
server/console_log.py
server/tool_log.py
interface/interface_dispatcher.py
agent_monitoring/store.py
agent_monitoring/collector.py
agent_monitoring/backup.py
agent_monitoring/manager.py
agent_monitoring/router.py
```

## Related Documentation

- `docs/architecture/DATA.md`
- `docs/architecture/BACKEND.md`
- `docs/reference/API.md`
- `docs/living/CHANGELOG.md` (tool-usage tracker, agent monitoring entries)