# GenV1 — Tools Architecture

> **Location:** `docs/architecture/TOOLS.md`
> **Next:** `docs/architecture/INTERFACE.md` · **Prev:** `docs/architecture/AGENTS.md`

## Purpose

Describe the tool system: the registry (ID → function), the shared
`FileSession` state, and the tool implementations, including the deletion
safety gate.

## Responsibilities

- Map tool IDs (used in `agent.json`) to Python callables.
- Expose tool docstrings as the schema the LLM sees.
- Provide a shared, persisted file-working state for agents.
- Guard destructive operations (file deletion) with an explicit two-step flow.

## Does Not Own

- The agent loop (see `docs/architecture/AGENTS.md`).
- Agent/tool selection UI (frontend reads `/api/tools`).

## Components

- `tools/registry.py` — canonical `_TOOL_REGISTRY` (id → callable),
  `get/get_list/resolve_tools/get_session`.
- `tools/state.py` — `FileSession`: `discovered_files`, `selected_files`,
  `read_files`, `working_content`, `output_files`, `pending_deletion`.
- `tools/tools.py` — the 7 implementations.

## Inputs

- Tool IDs from an agent's `agent.json#tools`.
- Call arguments produced by the LLM (normalized by `Agent.act()`).

## Processing

`resolve_tools(tool_ids)` turns IDs into callables (unknown IDs skipped with a
warning). `Agent.act()` normalizes args and invokes the callable; results are
recorded into `FileSession` (reads/writes/deletes/proposals) by the
session-aware wrapper in `engine/agents/factory.py`.

## Outputs

- Tool results (strings) and side-effect state in `FileSession`; tool-usage
  events forwarded to `server.tool_log`.

## Dependencies

- `engine/core/agent.py` (invocation + normalization).
- `server/tool_log.py` (event logging).
- RAG store via the `search_chat_logs` tool (`memory/`).

## Consumers

- Agents (tool-armed mode) and anything calling `resolved_tools()`.

## Extension Points

1. Write the function in `tools/tools.py` with a clear docstring.
2. Add one line to `_TOOL_REGISTRY` in `tools/registry.py`.
3. Reference the ID in any agent's `agent.json`.

## Rules

- Docstrings are the LLM schema — keep them descriptive.
- Unknown tool IDs resolve silently with a warning (definitions may reference
  tools not installed).
- Deletion requires two steps: `delete_files(..., approved=False)` proposes;
  `delete_files(paths, approved=True)` executes only paths already in
  `pending_deletion`.

## Failure Behavior

- Unknown ID → skipped with `[registry] WARNING` (never a crash).
- Tool exceptions → `Agent.act()` records `status: "error"` and returns an
  "Error executing tool" message; logging stays fail-safe.

## Runtime Flow

```text
Agent.think -> tool_calls
  -> Agent.act(tool_call)
     -> _normalize_args
     -> tools[<name>](**args)          registry -> tools.py
     -> record tool_event -> server.tool_log
     -> return str(result)
  -> Agent.observe(name, result)
```

## Configuration

Not applicable (no dedicated configuration). Tool availability is per-agent
via `agent.json`.

## APIs

- `GET /api/tools` — every tool ID an agent can pick (frontend checkboxes).

## Source Files

```text
tools/registry.py
tools/state.py
tools/tools.py
```

## Related Documentation

- `docs/architecture/AGENTS.md`
- `docs/reference/TOOL_REFERENCE.md`
- `docs/development/ADDING_TOOLS.md`