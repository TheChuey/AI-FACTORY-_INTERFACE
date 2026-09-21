# GenV1 — Custom Modules Guide

> **Location:** `docs/development/CUSTOM_MODULES.md`
> **Next:** `docs/development/ADDING_AGENTS.md` · **Prev:** `docs/reference/WORKFLOWS.md`

This is the full guide — the day-to-day "make a button" loop **and** the deep
dive for developers and AI coding assistants: how the dashboard HTML,
`server/server.py`, and a drop-in Python module talk to each other, with
complete copy-paste code for every UI action type.

---

## The 4-step loop (quick version)

1. **Generate** a module from the terminal.
2. **Edit** the one function that does the work.
3. **Activate** it (restart, or the live-apply trick below).
4. **Click** the button that shows up in the dashboard header.

Repeat for every new feature. Details below.

---

## 1. The pipeline, one picture

```
BROWSER  (dashboard/index.html)
  header-nav.js  ->  GET /api/interface/status  ->  ui_manifests[]  ->  draw button
  click button   ->  app.js action handler       ->  fetch(<endpoint>)
                                                          |
                                                          v
SERVER  (server/server.py)
  lifespan -> interface/wiring/bridges.py -> calls YOUR register_routes(app)
                                             => YOUR routes are LIVE on `app`
  <endpoint> handler runs your function -> returns { status, message, ... }
                                                          |
                                                          v
BROWSER  -> alert / modal / Q&A step / green status-dot
```

There are exactly **two ways anything can reach your module**:

| Channel | How | When to use |
|---|---|---|
| **1. HTTP routes** | `register_routes(app)` adds FastAPI routes at boot (or `apply`). The browser (or any client) calls them. | UI buttons, external callers, `curl`. |
| **2. In-process call** | the wiring bridge mirrors your module into the update catalog under the virtual domain `"custom"`, so `InterfaceDispatcher().execute_action("custom", <module>, <func>, ...)` runs it from Python. | Core code calling your module — see §6. |

---

## 2. Module lifecycle

### Where files live

- **Configured Custom Modules Path** (Settings → App defaults → *Custom Modules
  Path*), default `<dataDir>/custom_modules` (resolved by `server/paths.py`).
- Relative paths resolve from the project root; absolute paths are used as-is;
  `GENESSIS_CUSTOM_MODULES_PATH` env var overrides everything. Path changes
  need a **server restart**.

Instead of writing the file by hand you can scaffold one:

```bash
python about/set_title.py create-module <name>
```

Pick any name you want (letters, numbers, `-` and `_`). The command refuses to
overwrite an existing module.

### What the loader does (`interface/custom_module_manager.py`)

- Scans the folder for `*.py`, **ignoring names starting with `_` or `.`**
  (rename a module to `_old.py` to disable it without deleting).
- Imports each file with `importlib.util` and keeps it in
  `active_modules_catalog`.
- One broken file is logged and skipped — it never takes the app down.

### When modules (re)load

| You just… | Do this |
|---|---|
| Created a **brand-new** module file | Settings → Updates/Interface → **Apply**, or `POST /api/interface/apply`. Routes get registered live. |
| **Edited** an already-loaded module | **Restart the server** (`python server.py`). Routes are registered once per process, so an edit to a loaded module isn't picked up by Apply. |

Check what's loaded at any time:

```bash
curl http://127.0.0.1:8000/api/interface/status
# -> { "custom_modules": { "dir": "...", "active": ["my_feature", ...] },
#      "ui_manifests": [ ... ], "bridge": { ... } }
```

If a module you wrote isn't in `active`, look for this line in the server
console:

```
[custom-modules] Failed to load my_feature.py: <the Python error>
```

---

## 3. Step 1 — Generate a module

```bash
python about/set_title.py create-module analytics_builder
```

Writes `data/custom_modules/analytics_builder.py` (or wherever your Custom
Modules Path points). Open the file. You'll see two things:

```python
UI_MANIFEST = {
    "module_id": "analytics_builder",
    "buttons": [
        {
            "id": "btn-analytics_builder",
            "label": "＋ Analytics Builder",
            "target": "header",
            "action": "prompt_input",
            "prompt_message": "Enter name/parameter for Analytics Builder:",
            "api_endpoint": "/api/analytics_builder/execute",
            "title": "Trigger Analytics Builder action"
        }
    ]
}

def register_routes(app):
    @app.post("/api/analytics_builder/execute")
    def execute_module_action(payload: dict):
        user_input = payload.get("project_name") or payload.get("input", "Default")
        return {
            "status": "success",
            "message": f"[analytics_builder] Successfully processed input: {user_input}",
        }
```

**`UI_MANIFEST`** controls the header button (label, tooltip, prompt text).
You can safely edit `"label"`, `"prompt_message"`, `"title"`. Leave `"id"` and
`"api_endpoint"` consistent with `register_routes`.

**`register_routes(app)`** is where the real logic goes. Replace the body with
whatever you actually want to happen. Just make sure it returns a dict with a
`"message"` key (shown in the alert box on the frontend).

You can add as many buttons to `UI_MANIFEST["buttons"]` and as many routes
inside `register_routes` as you want — they don't have to be 1:1.

## 4. Minimal working module

Drop this into your Custom Modules Path as `hello_folder.py`. It shows a
header button ("✚ New Folder") that prompts for a name, POSTs it to the
server, and the server creates a folder inside your data directory.

```python
"""Minimal drop-in module: a header button that creates a folder."""
from pathlib import Path

from server.paths import DATA_DIR

UI_MANIFEST = {
    "module_id": "hello_folder",
    "buttons": [
        {
            "id": "btn-hello_folder",
            "label": "✚ New Folder",
            "target": "header",
            "action": "prompt_input",                 # prompt -> POST -> alert
            "prompt_message": "Enter folder name:",
            "api_endpoint": "/api/hello_folder/create",
            "title": "Creates a folder under <dataDir>/made_by_module",
        }
    ],
}


def register_routes(app):
    """Called once at boot; registers this module's HTTP routes on `app`."""
    @app.post("/api/hello_folder/create")
    def create_folder(payload: dict):
        # The frontend sends {"input": "the text the user typed"}.
        name = (payload.get("input") or payload.get("project_name") or "untitled").strip()
        target = DATA_DIR / "made_by_module" / name
        target.mkdir(parents=True, exist_ok=True)
        return {
            "status": "success",
            "message": f"Created folder: {target}",
        }
```

The contract:

- **`UI_MANIFEST`** — read by `GET /api/interface/status` → `ui_manifests`;
  `dashboard/js/ui/header-nav.js` draws it. `target: "header"` means the
  dashboard header.
- **`register_routes(app)`** — the wiring bridge calls it once per process
  (`interface/wiring/bridges.py`). Inside, the decorators are normal FastAPI.
- **Every endpoint returns `{"status": ..., "message": ...}`**. `message` is
  what the frontend shows. Optional `"indicate_success": true` turns the green
  status-dot on (see §5.5).

---

## 5. The five action types

A manifest `buttons[]` entry picks an `action`. The frontend dispatch lives in
`dashboard/js/app.js` (the `renderDynamicHeaderButtons` callback) and
`dashboard/js/ui/header-nav.js` (rendering).

### 5.1 `prompt_input` — the simple one

Button click → `window.prompt(prompt_message)` → `POST api_endpoint` with
`{"input": "<typed text>"}` → `alert(message)`.

```python
{
  "id": "btn-hello_folder",
  "label": "✚ New Folder",
  "target": "header",
  "action": "prompt_input",
  "prompt_message": "Enter folder name:",
  "api_endpoint": "/api/hello_folder/create",
}
```

Handler reads the typed value with `payload.get("input")`
(or `payload.get("project_name")` for agents that use that field).

### 5.2 `dropdown_menu` — several actions under one button

Button renders a flyout; each `items[]` entry is a real action handed to the
same handler (and the status-dot attaches to the parent button).

```python
{
  "id": "btn-tools",
  "label": "⚡ Tools",
  "target": "header",
  "action": "dropdown_menu",
  "title": "A menu of sub-actions",
  "items": [
      { "id": "item-newfolder", "label": "✚ New Folder",
        "action": "prompt_input", "prompt_message": "Folder name:",
        "api_endpoint": "/api/hello_folder/create" },
      { "id": "item-configure", "label": "⚙ Configure",
        "action": "open_modal", "schema_endpoint": "/api/my_feature/schema" },
  ],
}
```

### 5.3 `open_modal` — a form built from a JSON schema

The frontend fetches `schema_endpoint`, renders the `components`, and on submit
POSTs the filled values to `target_endpoint`.

```python
from fastapi import FastAPI

def register_routes(app: FastAPI):
    @app.get("/api/my_feature/schema")
    def dialog_schema():
        return {
            "title": "My Feature Configuration",
            "target_endpoint": "/api/my_feature/execute",
            "components": [
                {"type": "input", "name": "item_name", "label": "Item name",
                 "placeholder": "e.g. Alpha-1"},
                {"type": "select", "name": "priority", "label": "Priority",
                 "options": ["Low", "Medium", "High"]},
                {"type": "checkbox", "name": "notify", "label": "Notify team",
                 "value": True},
                {"type": "button", "label": "Save", "action": "submit"},
            ],
        }

    @app.post("/api/my_feature/execute")
    def execute_dialog(payload: dict):
        name = payload.get("item_name", "untitled")
        return {
            "status": "success",
            "message": f"Butler configured for '{name}'",
            "indicate_success": True,
        }
```

Component types the frontend understands: `input`, `select`, `checkbox`,
`button` (the `action: "submit"` row). Any other key is ignored.

### 5.4 `qa_survey` — step-by-step option wizard

The frontend opens a modal and repeatedly POSTs `{"step": N, "answers": {...}}`
to `qa_endpoint` until `completed: true`. `answers` is keyed `step_1`, `step_2`,
… (frontend-managed).

```python
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel

from server.paths import EXPORTS_DIR


class QARequest(BaseModel):
    step: int
    answers: dict = {}


def register_routes(app: FastAPI):
    @app.post("/api/my_feature/qa_step")
    def handle_qa_step(req: QARequest):
        if req.step == 1:
            return {
                "step": 1,
                "completed": False,
                "question": "Which objective?",
                "type": "choice",
                "options": ["AI Training", "Data Pipeline", "RAG Indexing"],
            }
        if req.step == 2:
            prev = req.answers.get("step_1", "?")
            return {
                "step": 2,
                "completed": False,
                "question": f"Got it: '{prev}'. Execution environment?",
                "type": "choice",
                "options": ["Local Ollama", "FastAPI Server", "Worker"],
            }
        # Final step -> completion. Optional: save a record.
        summary = (
            f"Objective: {req.answers.get('step_1')}\n"
            f"Environment: {req.answers.get('step_2')}"
        )
        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        record = EXPORTS_DIR / f"qa_{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        record.write_text(
            '{"answers": ' + __import__("json").dumps(req.answers) + "}",
            encoding="utf-8",
        )
        return {
            "step": 3,
            "completed": True,
            "summary": summary,
            "message": "Setup complete!",
            "indicate_success": True,
            "record_path": str(record),
        }
```

Manifest entry:

```python
{ "id": "item-qa", "label": "❓ Q&A Wizard",
  "action": "qa_survey", "qa_endpoint": "/api/my_feature/qa_step" }
```

### 5.5 `status_dot` — the green success indicator

Any of the above may return `"indicate_success": true`. The frontend adds a
green `.status-dot` to the trigger button (the parent button for a dropdown
item). No manifest flag needed — just return the key:

```python
return {"status": "success", "message": "Done!", "indicate_success": True}
```

---

## 6. Backend patterns

### `payload: dict` vs a pydantic model

- Quick endpoints just take `payload: dict` and read keys. Fine for
  `prompt_input`, modals and ad-hoc calls.
- Use a `pydantic.BaseModel` subclass when you want validation (e.g. the Q&A
  step contract). FastAPI validates the body automatically and returns 422 on
  bad input.

### The response you should return

```python
{
  "status": "success",                 # "success" | "error"
  "message": "Human-readable result",  # shown in alert / modal
  "indicate_success": True,            # optional -> green dot
}
```

### Referring to the app's internals

Import paths (from `server.paths`): `DATA_DIR`, `CHATS_DIR`, `RECORDS_DIR`,
`EXPORTS_DIR`, `RAG_DB_DIR`, `CUSTOM_MODULES_DIR`, `CHAT_SAVE_PATH`. See
`server/paths.py`.

### Streaming / long tasks

This system is request → response for module routes. If a module does slow
work, it should return quickly with a status object and (optionally) write
progress to a file or log the UI reads.

---

## 7. Calling a module's functions from core Python

The wiring bridge (`interface/wiring/__init__.py` + `bridges.py`) mirrors every
loaded custom module into the update manager's catalog under the virtual domain
**`"custom"`**, so core code can run module functions through the traced
dispatcher used by update modules:

```python
from interface.interface_dispatcher import InterfaceDispatcher

out = InterfaceDispatcher().execute_action(
    "custom",                     # domain: the bridge's virtual domain
    "my_feature",                 # module name (file stem)
    "some_function",              # any public function on the module
    arg1,                         # positional args...
    kwarg="value",                # and/or keyword args...
)
```

Every call is written to `<dataDir>/interface_trace.log`. If the module isn't
loaded you get a `KeyError` — the bridge only exposes active modules.

The module just needs a normal function:

```python
def some_function(name: str, make_upper: bool = False) -> str:
    return name.upper() if make_upper else name
```

---

## 8. Frontend files (usually you never touch these)

| File | Role |
|---|---|
| `dashboard/js/ui/header-nav.js` | `renderDynamicHeaderButtons()` fetches `ui_manifests`, draws regular buttons + `dropdown_menu`. |
| `dashboard/js/app.js` | The action dispatch: `prompt_input`, `open_modal`, `qa_survey`, the status-dot helper, and the shared `openModal(title, builder)` helper. |
| `dashboard/js/api/api.js` | Thin HTTP wrappers (`getInterfaceStatus`, `runInterface`, …). |

**To add a brand-new action type** (advanced): the three-file recipe —

1. Give a module button that action name in its `UI_MANIFEST`.
2. Add a rendering branch in `header-nav.js` `renderDynamicHeaderButtons()` if
   the action needs new DOM.
3. Add an `else if (btnConfig.action === "<name>")` branch in the
   `renderDynamicHeaderButtons(navSlot, async (btnConfig, parentBtn) => {...})`
   callback in `app.js`. Return `indicate_success` from your endpoint to reuse
   the green dot.

---

## 9. Testing without a browser

### Is my module loaded, and does its manifest look right?

```bash
curl http://127.0.0.1:8000/api/interface/status
```

### Direct endpoint calls

```bash
# prompt-style action
curl -X POST http://127.0.0.1:8000/api/hello_folder/create \
  -H "Content-Type: application/json" \
  -d "{\"input\": \"my_folder\"}"

# schema (open_modal)
curl http://127.0.0.1:8000/api/my_feature/schema

# Q&A step
curl -X POST http://127.0.0.1:8000/api/my_feature/qa_step \
  -H "Content-Type: application/json" \
  -d "{\"step\": 1, \"answers\": {}}"
```

(PowerShell: `^` is the line continuation; in bash use `\`.)

### FastAPI TestClient (no browser, no running server)

```python
from fastapi.testclient import TestClient

import server.server as srv

with TestClient(srv.app) as client:          # `with` runs lifespan -> routes registered
    status = client.get("/api/interface/status").json()
    assert "hello_folder" in status["custom_modules"]["active"]

    r = client.post("/api/hello_folder/create", json={"input": "test_dir"})
    assert r.json()["status"] == "success"
```

---

## 10. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Button not in the header | Not loaded. Check `custom_modules.active` via `GET /api/interface/status`; look for `Failed to load <name>.py: …` in the server console. |
| Module in `active` but endpoint 404s | The module has no `register_routes(app)`, or the route path/label don't match. Remember registration is **once per process** — after editing an already-loaded module, **restart**. |
| Edited the module, `apply` didn't change anything | Expected: `apply` wires brand-new modules; edits to loaded ones need a restart (the old function is still bound to the route in memory). |
| 422 error on a pydantic endpoint | Body doesn't match the model — check field names/types (e.g. `step` must be an int). |
| Typed text didn't arrive | `prompt_input` posts `{"input": ...}` — read `payload.get("input")` (many modules also accept `project_name`). |
| Put the file in `data/custom_modules` but nothing loads | Check the configured Custom Modules Path (Settings → App defaults) — modules load from *that* folder, not a hardcoded one. |
| Function callable in Python but not over HTTP | Only functions bound to routes inside `register_routes(app)` are HTTP-reachable; plain functions are reachable via `execute_action("custom", ...)`. |

---

## 11. Quick reference

| I want to… | Do this |
|---|---|
| Scaffold a module | `python about/set_title.py create-module <name>` |
| Add a simple input button | `prompt_input` + a `POST` route reading `payload.get("input")` |
| Group actions under one button | `dropdown_menu` + `items[]` |
| Render a schema-driven form | `open_modal` + a `GET` schema endpoint with `components` |
| Run a multi-step choice wizard | `qa_survey` + a POST `qa_endpoint` (`{step, answers}` → `completed`) |
| Show a green status dot | Return `"indicate_success": true` |
| Call a module from Python | `InterfaceDispatcher().execute_action("custom", "<module>", "<func>", ...)` |
| See load + manifests | `GET /api/interface/status` |
| Turn a module off | Rename it to start with `_` (or delete it), then restart/Apply |
| Move where modules are stored | Settings → Custom Modules Path (restart after) |

## Related documentation

- `docs/architecture/INTERFACE.md`
- `docs/reference/MODULE_REFERENCE.md`
- `docs/reference/API.md`
- `docs/GLOSSARY.md`