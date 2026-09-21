# GenV1 — Tool Reference

> **Location:** `docs/reference/TOOL_REFERENCE.md`
> **Next:** `docs/reference/WORKFLOWS.md` · **Prev:** `docs/reference/MODULE_REFERENCE.md`

Every tool registered in `tools/registry.py#_TOOL_REGISTRY`. Docstrings are the
LLM schema, so the summaries below mirror the delivered behavior.

---

## File management

### `map_files`
```text
Signature:  map_files()
Behavior:   Discovers the workspace file tree and records it in FileSession
            (discovered_files). Grounds agents so they stop guessing paths.
Side effects: updates FileSession.discovered_files.
```

### `read_file`
```text
Signature:  read_file(path)
Behavior:   Reads a file and records it in FileSession (read_files).
Side effects: updates FileSession.read_files.
```

### `write_text_file`
```text
Signature:  write_text_file(path, content)
Behavior:   Writes content to path; records the output file in FileSession.
Side effects: updates FileSession.output_files, writes to disk.
```

### `delete_files`
```text
Signature:  delete_files(files, approved=False)
Behavior:   Two-step deletion gate. approved=False proposes the files for
            deletion (records them in FileSession.pending_deletion);
            approved=True deletes ONLY files already proposed. Fabricated
            paths are rejected and surfaced in a `rejected` list.
Side effects: deletes files only when approved against pending_deletion.
```

## Date / time

### `get_current_date`
```text
Signature:  get_current_date()
Behavior:   Returns the current date string for the agent.
```

### `tell_me_the_date_and_time`
```text
Signature:  tell_me_the_date_and_time()
Behavior:   Returns the current date and time string for the agent.
```

## RAG / search

### `search_chat_logs`
```text
Signature:  search_chat_logs(query)
Behavior:   Searches the RAG memory store (memory/) for past-session context
            and returns matching transcript chunks. Used by rag_assistant for
            recall.
Dependencies: RAG store (memory/rag_commit, memory/search.py).
```

---

## Resolution behavior

```text
registry.get(tool_name)          -> callable or None
registry.list_tools()            -> 7 registered ids
registry.resolve_tools(ids)      -> callables (unknown ids skipped + warning)
registry.get_session()           -> the shared FileSession instance
```

## Session state (`tools/state.py`)

`FileSession` fields: `discovered_files`, `selected_files`, `read_files`,
`working_content`, `output_files`, `pending_deletion`. Injected into agents as
a replaceable `CURRENT FILE SESSION STATE` system message by
`engine/core/agent.py`.

## Failure behavior

- Unknown ID → skipped with `[registry] WARNING` (agent defs may reference
  tools not installed).
- Tool exception → `Agent.act()` records `status: "error"` and returns an
  "Error executing tool" message; never crashes the agent.

## Related documentation

- `docs/architecture/TOOLS.md`
- `docs/development/ADDING_TOOLS.md`
- `docs/reference/AGENT_REFERENCE.md` (which agents use which tools)