# How to Use the Custom Modules Feature

This is your day-to-day guide for adding new features to the app without
touching `index.html`, `header-nav.js`, or `server.py` by hand. Every new
feature is just one `.py` file.

> For the full developer guide — how the HTML, `server.py` and modules talk to
> each other, plus every UI action type (`dropdown_menu`, `open_modal`,
> `qa_survey`, `status_dot`) with runnable code — see
> [`CUSTOM_MODULE_DEV_GUIDE.md`](CUSTOM_MODULE_DEV_GUIDE.md).

---

## The 4-step loop

1. **Generate** a module from the terminal.
2. **Edit** the one function that does the work.
3. **Activate** it (restart, or the live-apply trick below).
4. **Click** the button that shows up in the dashboard header.

That's it. Repeat for every new feature.

---

## Step 1 — Generate a module

From your project root:

```bash
python about/set_title.py create-module analytics_builder
```

Pick any name you want (letters, numbers, `-` and `_`). This writes a new
file:

```
data/custom_modules/analytics_builder.py
```

(or wherever your **Custom Modules Path** points, if you changed it in
Settings — see "Changing where modules live" below).

If a module with that name already exists, the command refuses to overwrite
it and tells you so — pick a different name or delete the old file first.

## Step 2 — Edit the module

Open the file it just created. You'll see two things:

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

**`UI_MANIFEST`** controls what shows up in the header — the button's label,
its tooltip, and what it asks the user for. You can safely edit:

- `"label"` — the button text (emoji optional, e.g. `"＋ Analytics Builder"`)
- `"prompt_message"` — the text of the popup asking for input
- `"title"` — the tooltip shown on hover

Leave `"id"` and `"api_endpoint"` alone unless you also update them
consistently in `register_routes` below.

**`register_routes(app)`** is where the real logic goes. `execute_module_action`
is called every time someone clicks the button and submits the prompt.
Replace the body with whatever you actually want to happen — write a file,
call another part of your app, hit an external API, whatever. Just make
sure it returns a dict with a `"message"` key (that's what gets shown in
the alert box on the frontend).

Example — make it actually create a folder:

```python
from pathlib import Path
from server.paths import DATA_DIR

def register_routes(app):
    @app.post("/api/analytics_builder/execute")
    def execute_module_action(payload: dict):
        name = (payload.get("project_name") or payload.get("input") or "untitled").strip()
        folder = DATA_DIR / "projects" / name
        folder.mkdir(parents=True, exist_ok=True)
        return {"status": "success", "message": f"Created project folder: {folder}"}
```

You can add as many buttons to `UI_MANIFEST["buttons"]` and as many routes
inside `register_routes` as you want in a single module — they don't have
to be 1:1.

## Step 3 — Activate it

Pick whichever is easier in the moment:

- **Restart the server** — always works, no surprises:
  ```bash
  python server.py
  ```
- **Or, without restarting** — reload modules and register any brand-new
  ones live:
  ```bash
  python about/set_title.py apply
  ```
  This also works from the browser: whatever button in **Settings → Updates
  / Interface** calls `POST /api/interface/apply` does the same thing.

  > One caveat: `apply` only wires up routes for modules it has **never
  > seen before**. If you edit a module that was already loaded (change
  > what `execute_module_action` does), that edit needs a real restart to
  > take effect — the old version is still bound to the route in memory.
  > New file → `apply` is enough. Edited file → restart.

## Step 4 — Use it

Reload the dashboard page (`index.html`). Your new button appears in the
header nav automatically, right next to Dashboard / Chat / Settings.
Click it:

1. A prompt pops up asking whatever you put in `prompt_message`.
2. Type something and hit OK.
3. It POSTs to your `api_endpoint`, and whatever `"message"` your function
   returned pops up in an alert.

If nothing shows up in the header after activating, check the server's
console output for a line like:

```
[custom-modules] Failed to load analytics_builder.py: <error>
```

That means there's a Python error in your module — fix it and re-apply/restart.

---

## Removing or disabling a module

There's no CLI command for this yet — just delete or rename the `.py` file
in your custom modules folder and restart the server (or `apply`). A
renamed file starting with `_` or `.` (e.g. `_analytics_builder.py`) is
skipped by the loader too, which is a quick way to "turn off" a module
without deleting your code.

## Checking what's currently loaded

Hit this endpoint directly (in a browser or with curl) any time:

```
GET /api/interface/status
```

Look for:

```json
{
  "custom_modules": {
    "dir": "/path/to/data/custom_modules",
    "active": ["analytics_builder", "project_manager"]
  },
  "ui_manifests": [ ... ]
}
```

`custom_modules.active` is the list of every module currently loaded.
`ui_manifests` is exactly what the frontend uses to draw the buttons — if
your module's manifest isn't in that list, it either failed to import or
hasn't been picked up yet (restart / `apply`).

## Changing where modules live

Settings → App defaults → **Custom Modules Path**. Point it at any folder
— a project-relative path, an absolute path, or an external drive/synced
folder. Leave it blank to use the default (`data/custom_modules/`). Like
the other path fields, this needs a server restart after you save it.

---

## Quick reference

| I want to... | Do this |
|---|---|
| Add a new feature/button | `python about/set_title.py create-module <name>` |
| Make the button do something real | Edit `execute_module_action` in the generated file |
| Change the button's text/prompt | Edit `UI_MANIFEST` in the generated file |
| Pick up a brand-new module without restarting | `python about/set_title.py apply` |
| Pick up an edit to an existing module | Restart the server |
| Turn a module off | Rename it to start with `_` (or delete it), then restart/apply |
| See what's currently loaded | `GET /api/interface/status` |
| Move where modules are stored | Settings → Custom Modules Path (restart after) |
