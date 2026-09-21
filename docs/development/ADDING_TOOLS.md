# GenV1 — Adding a New Tool

> **Location:** `docs/development/ADDING_TOOLS.md`
> **Next:** `docs/development/TESTING.md` · **Prev:** `docs/development/ADDING_AGENTS.md`

Three steps to expose a new capability to agents.

---

## 1. Write the function in `tools/tools.py`

The docstring is the schema the LLM sees — write a clear one:

```python
def get_weather(city: str) -> str:
    """Fetch the current weather for a city.

    Args:
        city: the city name, e.g. "Paris".
    """
    return "sunny, 21°C"
```

Keep the signature simple: primitive parameters are much easier for local
models to fill correctly.

## 2. Register it in `tools/registry.py`

Import it and add one line to `_TOOL_REGISTRY`:

```python
from tools.tools import get_weather

_TOOL_REGISTRY: dict[str, Callable] = {
    ...
    "get_weather": get_weather,
}
```

Registry helpers: `get(name)`, `list_tools()`, `available_tool_ids()`,
`resolve_tools(ids)` (unknown ids skipped with a warning), `get_session()`.

## 3. Reference the ID in an agent

Add the id to an agent's `agent.json#tools`:

```json
"tools": ["map_files", "read_file", "get_weather"]
```

Agent modes: `chat` mode attaches **no** tools (only the LLM); `agent` mode
uses `agent.json#tools`.

---

## Notes on tool design

- **Session awareness**: `engine/agents/factory.py` wraps tools with
  `_session_aware`, so results are recorded into the shared `FileSession`
  (`tools/state.py`).
- **Deletion safety**: if you add a destructive tool, follow the two-step
  pattern of `delete_files` (propose with `approved=False`; delete only paths
  already in `FileSession.pending_deletion`).
- **Logging**: `Agent.act()` forwards every call to `server.tool_log`
  (`<dataDir>/toollog/tool_usage.jsonl`) automatically — no extra work needed.

## Verify

```bash
venv\Scripts\python -c "from tools.registry import list_tools; print(list_tools())"
```

`GET /api/tools` will include the new id for the Settings checkboxes.

## Related documentation

- `docs/architecture/TOOLS.md`
- `docs/reference/TOOL_REFERENCE.md`
- `docs/reference/AGENT_REFERENCE.md`
- `docs/GLOSSARY.md` (Tool, Tool event)