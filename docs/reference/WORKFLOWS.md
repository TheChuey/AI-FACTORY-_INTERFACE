# GenV1 — Workflows Reference

> **Location:** `docs/reference/WORKFLOWS.md`
> **Next:** `docs/development/CUSTOM_MODULES.md` · **Prev:** `docs/reference/TOOL_REFERENCE.md`

Important workflows from request to result. Each flow cites the real files it
passes through.

---

## 1. Single chat turn (mode `chat`)

```text
User
  -> POST /api/chat {message, model, agent_id}            server/server.py
  -> _default_agent() if no agent_id                      server/server.py
  -> chat_store.ensure_session(agent_id)                  server/chat_store/store.py
  -> build_agent(agent_id, model)                          engine/agents/factory.py
       loader.load_definition -> agent.md + agent.json     engine/agents/loader.py
       resolve_tools(ids) -> callables                     tools/registry.py
       PromptManager.build -> system prompt                engine/core/prompt.py
  -> Agent.think(message)                                  engine/core/agent.py
       ask_llm(messages, model, tools) -> Ollama           engine/core/llm.py
  -> chat_store.append_turn(...)                           server/chat_store/store.py
  -> {reply, session_id, title, tool_events}               back to browser
```
Mode `chat` attaches no tools → no tool loop can occur.

## 2. Agent turn with tools (mode `agent`) + tool-loop guard

```text
-> Agent.think(message)
     ask_llm(messages, model, tools)
     tool_calls?  (native tool_calls OR text-JSON _extract_text_tool_calls)
        act(tool_call, origin)
           _normalize_args -> tools[name](**args)
           -> tool event -> server/tool_log.append          server/tool_log.py
        observe(name, result)   {role:"tool"} appended
        ask_llm() again
     round guard: MAX_TOOL_ROUNDS = 6                       engine/core/agent.py
     repeat guard: same round >= REPEAT_LIMIT = 3 ->
        warning/feedback message, stop issuing tools
-> final reply (empty -> "(I ran my tools but did not produce a final answer...)")
```

## 3. Three-step agent pipeline

```text
User -> POST /api/chat {message, run_pipeline: true}
  -> engine.pipeline.run_pipeline(message, model)
     step 1: build_agent("feature_planner_agent").think(message)
             -> functional spec (no tools)
     step 2: build_agent("execute_engineer_agent")
             .think(message + step1 output labeled)
             -> reads skills/ux_module_designer_skills.md via read_file
             -> blueprint + pseudo-code
     step 3: build_agent("module_builder_agent")
             .think(message + step1 + step2 outputs)
             -> compiled drop-in Python module (UI_MANIFEST + register_routes)
  -> {reply (last step), tool_events, pipeline.outputs [...]}
  -> run recorded to <dataDir>/chatlog/pipeline_runs.jsonl   engine/pipeline.py
```

## 4. Save a chat (finalize)

```text
Save chat / new chat / POST /api/chats/end {agentId}
  -> chat_store.finalize_session(agent_id)
  -> appends "# VERSION N" section to the single .txt transcript
  -> ChatLogger.update -> chatRecord.jsonl row              server/chat_store/logger.py
  -> optional RAG commit (commitOnSave / rag override)      memory/
  -> consolidation offered when version >= 3
Delete: DELETE /api/chats/{id} -> records + every versioned .txt removed
```

## 5. RAG memory lifecycle

```text
Build:     POST /api/rag/rebuild | python scripts/rebuild_rag.py build
           -> ingest transcripts -> Chroma store (<dataDir>/rag_db)
Purge:     POST /api/rag/reset | python scripts/rebuild_rag.py purge
           (transcripts kept)
Recall:    rag_assistant -> search_chat_logs(query) -> RAGStorage.search
Status:    GET /api/rag/status | python scripts/rebuild_rag.py status
Auto-load: empty store -> first search ingests every transcript
           (unless rag.autoIngest off)
```

## 6. Custom module — generate → activate → click

```text
1. Generate:  python about/set_title.py create-module <name>
              -> writes <Custom Modules Path>/<name>.py (UI_MANIFEST +
                 register_routes(app) + POST /api/<name>/execute)
2. Activate:  restart python server.py   (or POST /api/interface/apply for
              brand-new modules only)
3. Wire:      lifespan -> CustomModuleManager.reload_all()
              -> bridges.register_routes(app) (once per process)
              -> bridges.activate()  (custom modules mirrored under 'custom')
4. Click:     dashboard reload -> GET /api/interface/status
              -> renderDynamicHeaderButtons(ui_manifests) -> button
              -> action handler -> POST api_endpoint
              -> {status, message, indicate_success} -> alert / modal / dot
Bridge call from core:
  InterfaceDispatcher().execute_action("custom", "<name>", "<func>", args)
  -> traced to <dataDir>/interface_trace.log
```

## 7. Master-copy recovery (Save / Restore)

```text
Save current state as master  -> POST /api/interface/snapshot
  -> RestoreManager.snapshot() -> publish tree into current-known-good-copy/
       + fresh BASELINE_MANIFEST.json
Restore to master copy        -> POST /api/interface/restore
  -> RestoreManager.restore()
       status() diff (SHA-256) -> differing files backed up to
         <dataDir>/snapshots/pre_restore_backup/<stamp>/
       master-only files added; live-only files preserved
       user data excluded (agent_monitoring/data, venv, .git, settings,
         about.json)
       -> docs snapshots regenerated (scripts/update_docs.py)
Preview drift: GET /api/interface/status -> baseline.modified_files
```

## 8. Adding a new agent

```text
1. Create folder engine/agent_library/<id>/ with agent.json (id/name/
   description/mode/model/tools) + agent.md (## sections)
2. (Optional) id != folder name -> loader resolves by scanning agent.json#id
3. Refresh -> GET /api/agents + Settings cards pick it up automatically
4. (Optional) add to config/pipeline.json steps for the pipeline
See docs/development/ADDING_AGENTS.md
```

## 9. Adding a new tool

```text
1. Write the function in tools/tools.py (clear docstring = LLM schema)
2. Add one line to _TOOL_REGISTRY in tools/registry.py
3. Reference the ID in any agent's agent.json#tools
See docs/development/ADDING_TOOLS.md
```

## 10. Regenerating documentation

```powershell
venv\Scripts\python scripts\update_documentation.py
  -> update_docs.py      (docs/generated/*)
  -> reference validation (files/endpoints/agents/tools/modules exist)
  -> update_blueprint.py (docs/BLUEPRINT.md assembled)
```
`docs/living/*` (CHANGELOG, DECISIONS, TODO, KNOWN_ISSUES, CURRENT_STATE) is
never overwritten by automation. See `docs/development/DOCUMENTATION_RULES.md`.

## Related documentation

- `docs/architecture/AGENTS.md`
- `docs/architecture/INTERFACE.md`
- `docs/development/CUSTOM_MODULES.md`
- `docs/reference/API.md`