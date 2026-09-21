# GenV1 — Agent Reference

> **Location:** `docs/reference/AGENT_REFERENCE.md`
> **Next:** `docs/reference/MODULE_REFERENCE.md` · **Prev:** `docs/reference/API.md`

Every agent catalogued from `engine/agent_library/` (source of truth: the
agent folders). Fields per agent: id · display name · folder · model · mode ·
tools · purpose.

Notes:

- **id ≠ folder**: the loader resolves the folder by scanning
  `agent_library/*/agent.json#id` when the literal folder path does not match
  (`engine/agents/loader.py`). Pipeline step ids use the `id`, so
  `Enginner/` → `execute_engineer_agent`, `Builder/` → `module_builder_agent`.
- `mode: chat` attaches no tools; `mode: agent` uses `agent.json#tools`.

---

## `rag_assistant`

```text
id:            rag_assistant
display name:  RAG Assistant
folder:        engine/agent_library/rag_assistant/
mode:          agent
model:         gemma4:e2b
tools:         map_files, read_file, write_text_file, delete_files,
               get_current_date, search_chat_logs
purpose:       Secure workspace file-manager and memory-retrieval specialist.
               Uses search_chat_logs for past-session queries, map_files /
               read_file for grounded discovery (never assumes paths),
               write_text_file for results, and a strict two-step deletion
               protocol (delete_files(approved=False) proposes, approved=True
               only after explicit confirmation).
```

## `feature_planner_agent` (folder `Planner/`)

```text
id:            feature_planner_agent
display name:  Feature Planner Agent
folder:        engine/agent_library/Planner/
mode:          chat            (no tools; tool loop disabled)
model:         qwen2.5-coder:latest
tools:         []              (none)
purpose:       Step 1 pipeline agent. Converts raw feature ideas into a
               structured functional specification: module ID, one of the 4 UX
               action patterns (prompt_input, dropdown_menu, open_modal,
               qa_survey), GET schema / POST execute endpoint contracts, and
               storage needs. Boundaries: no code/pseudo-code, no
               hallucinations, never ends on a clarifying question.
```

## `execute_engineer_agent` (folder `Enginner/`)

```text
id:            execute_engineer_agent
display name:  Execute Engineer Agent
folder:        engine/agent_library/Enginner/
mode:          agent
model:         qwen2.5-coder:latest
tools:         read_file
purpose:       Step 2 pipeline agent. Reads
               skills/ux_module_designer_skills.md exactly ONCE via read_file,
               translates the Step 1 functional plan into section-by-section
               pseudo-code and Python blueprints (UI_MANIFEST,
               register_routes(app), status contracts, server.paths authority).
               Input contract: the Step 1 Feature Plan is always in the
               incoming message; never ask for it.
```

## `module_builder_agent` (folder `Builder/`)

```text
id:            module_builder_agent
display name:  Module Builder Agent
folder:        engine/agent_library/Builder/
mode:          agent
model:         qwen2.5-coder:latest
tools:         map_files, read_file, write_text_file   (must only use these 3)
purpose:       Step 3 pipeline agent. Compiles the Stage 2 blueprint into a
               single complete drop-in Python custom module: Phase 1
               UI_MANIFEST, Phase 2 register_routes(app) (all @app.get/@app.post
               inside the function, real-time print(f"[<module>] ...") logging,
               {status, message, indicate_success} contracts), Phase 3 variable
               map + _extension_pre_process_hook / _extension_post_process_hook.
               Anti-hallucination: never fabricate UI actions/decorators; always
               import path authority from server.paths.
```

---

## Pipeline mapping

`config/pipeline.json` `steps` → agents:

```text
feature_planner_agent    ->  Planner/    (Step 1: functional spec)
execute_engineer_agent   ->  Enginner/   (Step 2: blueprints)
module_builder_agent     ->  Builder/    (Step 3: module compile)
```

## How agents are discovered / built

```text
/GET /api/agents  ->  registry.list_agents()   (scans agent_library/)
/GET /api/chat    ->  loader.load_definition   (id-aware folder lookup)
                      -> factory.build_agent  (mode -> tools -> prompt -> Agent)
```

## Related documentation

- `docs/architecture/AGENTS.md`
- `docs/development/ADDING_AGENTS.md`
- `docs/reference/WORKFLOWS.md`
- `docs/architecture/MEMORY.md` (RAG assistant's search_chat_logs)