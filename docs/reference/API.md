# GenV1 — API Reference

> **Location:** `docs/reference/API.md`
> **Next:** `docs/reference/AGENT_REFERENCE.md` · **Prev:** `docs/reference/FILES.md`

Every HTTP endpoint defined in `server/server.py`. Stack: FastAPI, mounted on
`/api/*`; static dashboard at `/static`; all CORS allowed. `POST /api/chat` is a
sync endpoint so blocking LLM calls run in the threadpool.

Per-endpoint fields: Method · Path · Purpose · Input · Output · Dependencies ·
Side Effects · Related Source File.

---

## UI / discovery

### `GET /api/models`
```text
Purpose:  Model dropdown options (from config/models.json, scanned from Ollama).
Input:    none.
Output:   {"models": [{"id", "name"}, ...]}   (empty list when missing).
Dependencies: engine/core/llm.py (scan at boot).
Related:  server/server.py (get_models).
```

### `GET /api/agents`
```text
Purpose:  Every discovered agent.
Input:    none.
Output:   {"agents": [{"id", "name", "description", "mode", "model"}, ...]}.
Dependencies: engine/agents/registry.py.
Related:  server/server.py (get_agents).
```

### `GET /api/tools`
```text
Purpose:  Every tool ID an agent can pick (feeds Settings checkboxes).
Input:    none.
Output:   {"tools": [7 tool id strings]}.
Dependencies: tools/registry.py.
Related:  server/server.py (get_tools).
```

### `GET /api/pipeline`
```text
Purpose:  The configured agent chain for the frontend "Run pipeline" button.
Input:    none.
Output:   {"steps": [agent_id, ...], "configured": bool}.
Dependencies: config/pipeline.json.
Related:  server/server.py (get_pipeline).
```

## Agent config editor

### `GET /api/agents/{agent_id}/config`
```text
Purpose:  One agent's consolidated config.
Input:    path: agent_id.
Output:   {"agent": {id,name,description,mode}, "meta": {...}, "markdown": str,
          "tests": [...], "sharedTests": [...], "file": str, "markdownFile": str}.
          HTTP 404 (AgentNotFoundError) for unknown agents.
Dependencies: engine/agents/loader.py.
Related:  server/server.py (get_agent_config).
```

### `PUT /api/agents/{agent_id}/config`
```text
Purpose:  Partial update of one agent's config.
Input:    path: agent_id; body: {meta?, markdown?, tests?} (normalized).
Output:   Same shape as GET config; 404 for unknown agents.
Side Effects: writes agent.json / agent.md.
Dependencies: loader.save_meta / save_markdown / save_tests.
Related:  server/server.py (save_agent_config).
```

## Chat I/O

### `POST /api/chat`
```text
Purpose:  Handle a chat message (builds the agent per request; per-agent
          server-side sessions). SYNC endpoint.
Input:    ChatRequest {message, model="", agent_id="", history=[], session_id="",
          title="", new_chat=false, rag=false, run_pipeline=false}.
Output:   {"reply", "session_id", "title", "tool_events"}. With run_pipeline:
          + {"pipeline": {"outputs": [{agent_id, agent_name, output}, ...]}}.
          Unknown agent: {"reply": "(unknown agent '<id>' ...)"}.
Dependencies: factory.build_agent, chat_store, engine/pipeline.py.
Side Effects: chat session updates; tool events logged to tool_usage.jsonl;
          pipeline runs appended to pipeline_runs.jsonl.
Related:  server/server.py (chat).
```

### `GET /api/chats`
```text
Purpose:  Chat log + active chats (feeds the chats drop-down).
Input:    none.
Output:   {"chats": [chat record rows, newest first]}.
Dependencies: chat_store.list_log.
Related:  server/server.py (list_chats).
```

### `GET /api/chats/active`
```text
Purpose:  Resume ONE agent's currently open chat (registered before {chat_id}).
Input:    query: agent_id="".
Output:   Chat dict with "active": true, content, messages; 404 when nothing active.
Dependencies: chat_store.
Related:  server/server.py (active_chat).
```

### `GET /api/chats/{chat_id}`
```text
Purpose:  One chat: record + .txt content + parsed messages (latest section).
Input:    path: chat_id.
Output:   {...row, "content": str, "messages": [...]}; 404 "Chat '<id>' not found".
Dependencies: chat_store.get_chat.
Related:  server/server.py (get_chat).
```

### `POST /api/chats/end`
```text
Purpose:  Finalize the active chat for an agent (versioned .txt + log row).
Input:    {agentId?, discard?, rag?}.
Output:   Saved: {finalized, saved, file, id, version, consolidation_offered}.
          Discard: {finalized, saved:false, discarded, id}.
          Nothing: {finalized:false, saved:false, error}.
Side Effects: transcript version bump; optional RAG commit; log row update.
Dependencies: chat_store.finalize_session, memory rag_commit.
Related:  server/server.py (end_chat).
```

### `POST /api/chats/consolidate`
```text
Purpose:  AI-consolidate a finalized chat (requires 2+ versions).
Input:    {chat_id, model?}.
Output:   {ok, summary_preview, file, version: "C"}; 400 on errors.
Side Effects: appends # CONSOLIDATED section; best-effort RAG commit.
Dependencies: server/chat_store/consolidate.py.
Related:  server/server.py (consolidate_chat).
```

### `DELETE /api/chats/{chat_id}`
```text
Purpose:  Permanently erase a chat (records + transcripts + active session).
Input:    path: chat_id.
Output:   {deleted, id, recordsRemoved, filesRemoved, wasActive}; 404 when nothing.
Dependencies: chat_store.delete_chat.
Related:  server/server.py (delete_chat).
```

### `POST /api/chat-save`
```text
Purpose:  Finalize the ACTIVE chat (legacy clients); raw-blob fallback.
Input:    {message?, etc.} (legacy payload).
Output:   {saved, file, id} or {saved:false, error}.
Side Effects: transcript written (sanitized + sandboxed to BASE_DIR).
Related:  server/server.py (save_chat_session).
```

## Logs

### `GET /api/logs/console`
```text
Purpose:  Tail of captured console output.
Input:    query: limit=300.
Output:   {"logs": [str], "captured": bool}.
Dependencies: server/console_log.py.
Related:  server/server.py (console_logs).
```

### `GET /api/logs/tools`
```text
Purpose:  Structured tool-usage feed, newest first.
Input:    query: limit=500, tool="", agent="", since="".
Output:   {"events": [...], "total": int, "captured": bool}.
Side Effects: none (reads <dataDir>/toollog/tool_usage.jsonl).
Dependencies: server/tool_log.py.
Related:  server/server.py (tool_logs).
```

## RAG memory

### `GET /api/rag/status`
```text
Purpose:  Store location + indexed chunk count + resolved paths.
Output:   {"status": {...}}.
Dependencies: memory/rag_commit.status, server/paths.py.
Related:  server/server.py (rag_status).
```

### `POST /api/rag/rebuild`
```text
Purpose:  Re-index every saved transcript into the RAG store.
Output:   {"message": str}.
Dependencies: memory/rag_commit.rebuild_store.
Related:  server/server.py (rag_rebuild).
```

### `POST /api/rag/reset`
```text
Purpose:  Purge the RAG store (transcripts kept).
Output:   {"message": str}.
Dependencies: memory/rag_commit.purge_store.
Related:  server/server.py (rag_reset).
```

## Discussions (legacy chat-log wrappers)

### `GET /api/discussions`
```text
Purpose:  List discussions (chat log rows).
Output:   {"discussions": chat_store.list_log()}.
Related:  server/server.py (list_discussions).
```

### `POST /api/discussions`
```text
Purpose:  Upsert a discussion by id (server stamps updatedAt).
Input:    {id, ...}.
Output:   {"saved": true} ({"saved": false, "error"} without id).
Related:  server/server.py (save_discussion).
```

### `DELETE /api/discussions/{discussion_id}`
```text
Purpose:  Delete a discussion.
Output:   {"deleted": true, "id"}; 404 when unknown.
Related:  server/server.py (delete_discussion).
```

## History snapshots

### `GET /api/history`
```text
Purpose:  Saved message snapshots.
Output:   {"history": [...]}.
Related:  server/server.py (list_history).
```

### `POST /api/history`
```text
Purpose:  Upsert a message snapshot (auto-id when missing).
Input:    {id?, ...}.
Output:   {"saved": true}.
Side Effects: writes <dataDir>/history.json.
Related:  server/server.py (save_history).
```

### `DELETE /api/history/{message_id}`
```text
Purpose:  Delete a snapshot.
Output:   {"deleted": true, "id"}; 404 when unknown.
Related:  server/server.py (delete_history).
```

## Settings / identity

### `GET /api/about`
```text
Purpose:  Site identity.
Output:   {"title", "subtitle"} (defaults "Terminator 2" / subtitle).
Dependencies: about/about.json.
Related:  server/server.py (get_about).
```

### `GET /api/settings`
```text
Purpose:  Stored browser defaults.
Output:   {"settings": {...}, "restartNeeded": bool, "platform": "win"|"nix"}.
Dependencies: dashboard/config/app_settings.json, server/paths.py.
Related:  server/server.py (get_app_settings).
```

### `POST /api/settings`
```text
Purpose:  Merge partial settings (path values stored verbatim).
Input:    partial settings dict.
Output:   Same as GET.
Side Effects: writes dashboard/config/app_settings.json.
Related:  server/server.py (save_app_settings).
```

## Wizard exports

### `POST /api/exports`
```text
Purpose:  Save one wizard prompt as {name}.md + {name}.json.
Input:    {name?, prompt?, ...}.
Output:   {"saved": true, "files": [<name>.md, <name>.json]} or error.
Side Effects: writes <dataDir>/exports/.
Related:  server/server.py (save_export).
```

## Modular interface

### `GET /api/interface/status`
```text
Purpose:  Everything the Settings Updates/Interface card needs.
Input:    none.
Output:   {"ok", "run_enabled", "updates_dir", "archive_dir", "trace_log",
          "catalog", "archived", "trace_tail", "baseline",
          "custom_modules": {dir, active}, "ui_manifests", "bridge"}.
Dependencies: UpdateManager, CustomModuleManager, RestoreManager, bridges.
Related:  server/server.py (interface_status).
```

### `POST /api/interface/apply`
```text
Purpose:  Reload module loaders + re-wire bridge + regenerate docs snapshots.
Output:   {"ok", "catalog", "custom_modules", "bridge", "docs_regenerated"};
          500 on reload failure.
Side Effects: calls scripts/update_docs.py.
Related:  server/server.py (interface_apply).
```

### `POST /api/interface/snapshot`
```text
Purpose:  Publish current tree as the known-good master copy.
Output:   {"ok": true, "files", "baseline"}; 500 on failure.
Side Effects: writes current-known-good-copy/.
Related:  server/server.py (interface_snapshot).
```

### `POST /api/interface/restore`
```text
Purpose:  Roll the live tree back to the master copy (backup first).
Input:    none (payload-less; real restore only).
Output:   {"ok": true, ...result}; 500 on failure.
Side Effects: pre-restore backups + overwrite + docs regeneration.
Related:  server/server.py (interface_restore).
```

### `POST /api/interface/run`
```text
Purpose:  Execute an update-module function (gated).
Input:    InterfaceRunRequest {domain, module, function, args=[], kwargs={}}.
Output:   {"ok", "domain", "module", "function", "result"}; 403 when disabled;
          404 unknown module; 500 otherwise.
Side Effects: traced execution to <dataDir>/interface_trace.log.
Related:  server/server.py (interface_run).
```

### `POST /api/interface/toggle-run`
```text
Purpose:  Arm/disarm /api/interface/run for the process.
Input:    InterfaceToggleRequest {enabled}.
Output:   {"ok": true, "run_enabled": bool}.
Side Effects: flips INTERFACE_RUN_ENABLED; traces the flip.
Related:  server/server.py (interface_toggle_run).
```

## Home

### `GET /`
```text
Purpose:  Serve the dashboard shell.
Output:   FileResponse(dashboard/index.html).
Related:  server/server.py (home).
```

---

## Notes

- There is **no `/api/activity`** endpoint — the Agent Monitor feature was
  removed (see `docs/living/CHANGELOG.md`).
- Module-external routes added by custom modules (`register_routes(app)`) are
  module-defined and not listed here; see `docs/reference/MODULE_REFERENCE.md`.

## Related documentation

- `docs/architecture/BACKEND.md`
- `docs/reference/MODULE_REFERENCE.md`
- `docs/living/CURRENT_STATE.md`