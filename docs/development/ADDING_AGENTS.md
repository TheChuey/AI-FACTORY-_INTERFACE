# GenV1 — Adding a New Agent

> **Location:** `docs/development/ADDING_AGENTS.md`
> **Next:** `docs/development/ADDING_TOOLS.md` · **Prev:** `docs/development/CUSTOM_MODULES.md`

No Python required. An agent is data: a folder under `engine/agent_library/`
with `agent.json` (configuration) + `agent.md` (behavior).

---

## 1. Create the folder + files

```
engine/agent_library/<id>/
├── agent.json      # configuration
└── agent.md        # behavior
```

### `agent.json`

```json
{
  "id": "my_new_agent",
  "name": "My New Agent",
  "description": "Short description shown in the selector.",
  "mode": "agent",
  "model": "qwen2.5-coder:latest",
  "tools": ["map_files", "read_file", "write_text_file"]
}
```

Fields:

| Field | Meaning |
|---|---|
| `id` | The agent's public id, used in `/api/chat`, `/api/agents/{id}` and `config/pipeline.json`. |
| `name` | Display name. |
| `description` | Selector/listing text. |
| `mode` | `"chat"` (no tools) or `"agent"` (tools enabled). |
| `model` | Preferred model; falls back to a detected model if not installed. |
| `tools` | Tool IDs from `tools/registry.py` (`GET /api/tools` lists them). |

### `agent.md`

Behavior prose split into `## <section>` blocks. Sections consumed by the
prompt builder (`engine/core/prompt.py`):

```markdown
## Role
## Purpose
## Personality
## Boundaries
## Communication
## Principles
## Decision Style
## Priorities          (documentation only — not put in the prompt)
```

Unknown `##` sections become extra UPPERCASE-titled prompt blocks.
`## Skills` and `## Identity` are excluded from the prompt.

## 2. Folder name vs id

The loader (`engine/agents/loader.py#agent_dir`) tries the literal folder
`agent_library/<id>` first, then scans `agent_library/*/agent.json` and returns
the first (sorted) folder whose `meta["id"]` matches. So the folder name may
differ from the id (e.g. folder `Enginner/` → id `execute_engineer_agent`).
Spaces, kebab-case, any case all work.

## 3. Refresh

The agent appears automatically in `GET /api/agents` and the frontend selector
and the Settings agent cards — no code edits, no restart of the engine.

## 4. Add it to the pipeline (optional)

To run it as one step of the 3-step chain, add its id to
`config/pipeline.json` `steps`:

```json
{
  "name": "module-generation",
  "steps": ["feature_planner_agent", "execute_engineer_agent", "module_builder_agent"]
}
```

Steps run in order; each later step receives the user message plus the earlier
steps' labeled replies.

## 5. Verify

```bash
venv\Scripts\python -c "from engine.agents.registry import list_agents; print(list_agents())"
```

Or start the server and check `GET /api/agents`.

## Related documentation

- `docs/architecture/AGENTS.md`
- `docs/reference/AGENT_REFERENCE.md`
- `docs/reference/WORKFLOWS.md` (workflow 8)