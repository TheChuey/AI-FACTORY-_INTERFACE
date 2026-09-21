# GenV1 — Module Reference

> **Location:** `docs/reference/MODULE_REFERENCE.md`
> **Next:** `docs/reference/TOOL_REFERENCE.md` · **Prev:** `docs/reference/AGENT_REFERENCE.md`

Custom modules and interface modules. Two separate loader worlds connected by
the wiring bridge:

```text
interface/updates/<domain>/*.py   UpdateManager      (domain-based)
Custom Modules Path *.py          CustomModuleManager (flat, drop-in)
        \               /
         \             /
    interface/wiring/ CustomModuleBridge -> virtual 'custom' domain
```

---

## Update modules (`interface/updates/<domain>/`)

Domains: `engine`, `tools`, `server`. Discovered/imported by
`interface/update_manager.py`. Executed directly
(`UpdateManager.get_active_module(domain, module)`), traced
(`InterfaceDispatcher.trace_and_execute(fn, ...)`), or by name
(`InterfaceDispatcher.execute_action(domain, module, function, *args)`).

```text
Example module contract:
  class / functions with docstrings:
    execute_new_logic("Input Data") -> ...
    secondary_engine_action(5) = 50
Retirement:
  UpdateManager.move_module_to_external_archive(domain, module)
      -> moves the file to <dataDir>/interface_archive/<domain>/
```

Note: as of this documentation the `interface/updates/` domains contain only
`__init__.py` files (the earlier seeded examples were archived). The loader
handles an empty catalog fine.

## Custom modules (drop-in, flat folder)

A single standalone `.py` file in the **Custom Modules Path** (blank =
`<dataDir>/custom_modules`; relative → project root; absolute → as-is;
`GENESSIS_CUSTOM_MODULES_PATH` overrides everything). Scaffold:

```bash
python about/set_title.py create-module <name>
```

### Module anatomy

```python
UI_MANIFEST = {
    "module_id": "<name>",
    "buttons": [
        {
            "label": "…",
            "action": "prompt_input",      # or dropdown_menu/open_modal/qa_survey
            "prompt_message": "…",
            "api_endpoint": "/api/<name>/execute",
        },
    ],
}

def register_routes(app):
    @app.post("/api/<name>/execute")
    def execute(payload: dict):
        return {"status": "ok", "message": "…", "indicate_success": True}
```

Loaded with `importlib.util` by `interface/custom_module_manager.py`. A broken
import is logged and skipped; one bad file never blocks boot.

### UI action types

| Action | Behavior |
|---|---|
| `prompt_input` | window prompt; POST `{"input": ...}` to `api_endpoint` |
| `dropdown_menu` | flyout whose `items[]` are any action type; status dot attaches to the parent |
| `open_modal` | fetch `schema_endpoint` (components: input/select/checkbox/button); POST filled values to `schema.target_endpoint` |
| `qa_survey` | step wizard POSTing `{step, answers}` to `qa_endpoint` until `completed: true` |
| `status_dot` | any response with `indicate_success: true` lights a green dot on the trigger |

### Activation

- Restart `server/server.py` — simplest, for everything.
- `POST /api/interface/apply` — brand-new modules go live without a restart
  (routes register at most once per process); route edits to loaded modules
  still need a restart.

### Reachability

```python
from interface.interface_dispatcher import InterfaceDispatcher

InterfaceDispatcher().execute_action("custom", "<name>", "<func>", "input")
```

Logged to `<dataDir>/interface_trace.log`.

## Restore / master copy

`interface/restore_manager.py` — one master copy in
`current-known-good-copy/`:

| Method | Behavior |
|---|---|
| `snapshot()` | publish the current tree as the master |
| `status()` | master info + drift count (SHA-256 diff) |
| `restore()` | overlay master files (backup differing first → restore); add master-only files; never delete live-only files; regenerate docs snapshots afterwards |

## Wiring bridge

`interface/wiring/bridges.py` (`CustomModuleBridge`):
- `register_routes(app)` — once per process.
- `activate()` / `deactivate()` — mirror custom modules into the update
  catalog under the virtual domain `custom`.

## Identifiers

| Manager | Discovery root | Public methods |
|---|---|---|
| `UpdateManager` | `interface/updates/<domain>/` | `reload_all()`, `get_active_module()`, `list_domain_modules()`, `move_module_to_external_archive()` |
| `CustomModuleManager` | Custom Modules Path | `reload_all()`, `get_active_module()`, `list_modules()`, `ui_manifests()`, `active_modules_catalog` |
| `RestoreManager` | `current-known-good-copy/` | `snapshot()`, `status()`, `restore()` |
| `CustomModuleBridge` | — | `register_routes()`, `activate()`, `deactivate()`, `reachable_names()` |

## Related documentation

- `docs/architecture/INTERFACE.md`
- `docs/development/CUSTOM_MODULES.md`
- `docs/reference/API.md` (interface endpoints)
- `docs/GLOSSARY.md`