# Phase 1 + 2 + 3 — Install Instructions

## Heads-up before you copy anything

Your actual `interface/update_manager.py` already has its own module system
(domain folders under `interface/updates/engine|tools|server/`, discovered by
`UpdateManager`). That system is **untouched** — nothing below deletes or
edits it. Phase 1's "drop a `.py` file in and it just works" loader is
implemented as a **second, independent** system living in a new file:
`interface/custom_module_manager.py`. The two managers never talk to each
other, so nothing you already built can break.

What you get, end to end:

- Drop a `.py` file with `UI_MANIFEST` + `register_routes(app)` into your
  **Custom Modules Path** folder (default `data/custom_modules/`) → it's
  auto-imported at boot, its route goes live, and its header button appears
  on the dashboard automatically. No editing `index.html`, `header-nav.js`,
  or `server.py` by hand.
- `python about/set_title.py create-module <name>` scaffolds that `.py` file
  for you, pre-wired and ready to edit.
- A manifest `buttons[]` entry picks one `action`: `prompt_input`,
  `dropdown_menu` (flyout), `open_modal` (schema-driven form) or `qa_survey`
  (step wizard). Any response returning `indicate_success: true` lights a
  green status-dot on the trigger button.
- The **wiring bridge** (new in this refresh) also exposes every loaded module
  to core Python: `InterfaceDispatcher().execute_action("custom", <module>,
  <func>, ...)`.

This kit is a snapshot of the running implementation — the files below are
byte-for-byte the live ones plus the wiring layer.

---

## 1. Files to REPLACE (same filename — just copy over the old one)

| File in this delivery | Copy over → (in your project) |
|---|---|
| `server/paths.py` | `server/paths.py` |
| `server/server.py` | `server/server.py` |
| `about/set_title.py` | `about/set_title.py` |
| `dashboard/js/app.js` | `dashboard/js/app.js` |
| `dashboard/js/ui/header-nav.js` | `dashboard/js/ui/header-nav.js` |
| `dashboard/js/ui/config-form.js` | `dashboard/js/ui/config-form.js` |

Every one of these is your original file with the Phase 1/2/3 additions
inserted — nothing else was rewritten. Diff-review them if you want to be
sure, then just overwrite.

## 2. Files to ADD (new — don't exist in an un-modified project yet)

| New file | Goes at |
|---|---|
| `interface/custom_module_manager.py` | `interface/custom_module_manager.py` |
| `interface/wiring/__init__.py` | `interface/wiring/__init__.py` |
| `interface/wiring/bridges.py` | `interface/wiring/bridges.py` |

- `custom_module_manager.py` is the flat-folder loader.
- `interface/wiring/` is the **connection layer**: it calls each module's
  `register_routes(app)` once per process and mirrors the modules into the
  update manager's catalog under the virtual domain `"custom"` so core code
  can call them through the traced dispatcher.

Everything else is a folder that gets created **automatically** the first time
the server boots (see below) — you don't need to make it by hand, but you can
if you want it to exist ahead of time.

## 3. Folder created automatically at runtime

```
data/
└── custom_modules/        ← created on first boot if missing
    └── (your .py modules land here)
```

If you'd rather point this somewhere else (an external folder, a synced
drive, whatever), open **Settings → Custom Modules Path** in the dashboard
after you install this and set it there — it works exactly like the
existing Data folder / RAG database path fields. Leave it blank to keep the
default (`data/custom_modules/`).

> Reference implementations: in the running app, `interactive_manager.py`
> (demonstrates `dropdown_menu`, `open_modal`, `qa_survey`, `status_dot`)
> and `project_manager.py` live in the configured Custom Modules Path. They
> are per-machine data, not part of this kit.

---

## Updated project tree (only the touched/added paths are marked)

```
genV2_Interface_projectManager/
├── about/
│   └── set_title.py                       ← REPLACE (adds `create-module`; `apply` via wiring)
├── dashboard/
│   ├── config/
│   │   └── app_settings.json              (unchanged — gains "customModulesPath" key
│   │                                         automatically the first time you save Settings)
│   └── js/
│       ├── app.js                         ← REPLACE (dispatches all four action types)
│       └── ui/
│           ├── config-form.js             ← REPLACE (adds "Custom Modules Path" field)
│           └── header-nav.js              ← REPLACE (renders buttons + dropdown menus)
├── data/
│   └── custom_modules/                    ← NEW FOLDER (auto-created at boot)
│       └── <your-generated-modules>.py    ← where `create-module` writes files
├── interface/
│   ├── custom_module_manager.py           ← ADD (the flat custom drop-in loader)
│   ├── wiring/                            ← ADD (new folder — the connection layer)
│   │   ├── __init__.py                    ←     WiringManager: wire / rewire / registry
│   │   └── bridges.py                     ←     CustomModuleBridge: routes + "custom" domain
│   ├── update_manager.py                  (unchanged — your existing domain system)
│   ├── interface_dispatcher.py            (unchanged)
│   ├── restore_manager.py                 (unchanged)
│   └── updates/                           (unchanged)
└── server/
    ├── paths.py                           ← REPLACE (adds CUSTOM_MODULES_DIR)
    └── server.py                          ← REPLACE (loads custom modules + wires them)
```

---

## 4. How to use it

### Generate a new module (Phase 3)

```bash
python about/set_title.py create-module analytics_builder
```

This writes `data/custom_modules/analytics_builder.py` (or wherever your
Custom Modules Path points), pre-filled with:

- `UI_MANIFEST` — declares a "＋ Analytics Builder" header button
- `register_routes(app)` — declares `POST /api/analytics_builder/execute`

Open that file and put your real logic inside `execute_module_action`.

### The four button action types

A manifest `buttons[]` entry picks exactly one `action` (see
`docs/CUSTOM_MODULE_DEV_GUIDE.md` for runnable backend code for each):

| `action` | What the frontend does |
|---|---|
| `prompt_input` | `window.prompt(prompt_message)` → `POST api_endpoint` with `{"input": ...}` → `alert(message)` |
| `dropdown_menu` | renders a flyout; each `items[]` entry is a real action, run against the parent button |
| `open_modal` | fetches `schema_endpoint` (a JSON schema of `input` / `select` / `checkbox` / `button` components), builds a modal form, POSTs the filled values to `schema.target_endpoint` |
| `qa_survey` | a step wizard that POSTs `{step, answers}` to `qa_endpoint` until the server returns `completed: true` |

Plus `status_dot` — not an action but a response flag: return
`indicate_success: true` from any endpoint and a green `.status-dot` appears
on the trigger button.

### Activate it

Two ways:

1. **Restart the server** (`python server.py`) — simplest, always works.
2. **Or**, without restarting: `python about/set_title.py apply`
   (or click whatever button in Settings → Updates/Interface calls
   `POST /api/interface/apply`). New modules get their routes registered
   live in the running process. (If you *edit* a module that was already
   loaded, its route logic is still the old closure until a real restart —
   only brand-new modules pick up instantly.)

### See it in the UI

Reload the dashboard (`index.html`). A new button appears in the header nav
automatically — no template or JS edits needed. Clicking it follows its
`action` (prompt → modal → dropdown → wizard) and POSTs to the module's
endpoint.

### Call it from core Python (the wiring bridge)

Any public function on a loaded module is callable from anywhere in the app
through the same traced dispatcher used for update modules:

```python
from interface.interface_dispatcher import InterfaceDispatcher

result = InterfaceDispatcher().execute_action(
    "custom",            # domain — the bridge's virtual domain
    "analytics_builder", # module name (file stem)
    "some_function",     # any public function on the module
    "some input",
)
```

Calls are logged to `data/interface_trace.log`.

### Change where modules are read from

Settings → App defaults → **Custom Modules Path**. Same rules as the other
path fields: blank = `data/<Data folder>/custom_modules`, relative paths
resolve from the project root, absolute paths are used as-is, and a change
here needs a server restart to take effect (the field will tell you so via
the existing "restart needed" banner).

---

## 5. What each new/changed piece actually does

- **`server/paths.py`** — adds `CUSTOM_MODULES_PATH` / `CUSTOM_MODULES_DIR`,
  resolved the same way `dataDir` / `ragDbPath` already are (relative →
  project root, absolute → used as-is, `GENESSIS_CUSTOM_MODULES_PATH` env
  var overrides everything).
- **`interface/custom_module_manager.py`** — scans that folder for `*.py`
  files, imports each with `importlib.util` (they're standalone files, not a
  Python package), and exposes `active_modules_catalog`, `ui_manifests()`,
  and `get_active_module(name)`.
- **`interface/wiring/`** — the connection layer (all new):
  - `__init__.py` — `WiringManager`: `wire(app)` at boot, `rewire(app)` on
    `apply`, `registry()` for `/api/interface/status`, `summary()` for the
    CLI/boot log. Loads both managers as singletons when none are passed.
  - `bridges.py` — `CustomModuleBridge`: calls `register_routes(app)` for
    every module **at most once per process** (`_REGISTERED` set), and
    `activate()` mirrors all active modules into the update manager's catalog
    under the virtual domain `"custom"` (re-injected after every reload).
- **`server/server.py`** — at startup (`lifespan`) creates the loader **and**
  `WiringManager`, wires them, and exposes them on `app.state` (`update_manager`,
  `custom_module_manager`, `wiring`). Route registration and the bridge now
  happen inside `interface/wiring` (previously hand-rolled in server.py).
  `GET /api/interface/status` returns `catalog` (per domain), `custom_modules`
  (folder + active names), `ui_manifests` (for the frontend) and `bridge`
  (domain + reachable names).
- **`dashboard/js/ui/header-nav.js`** — `renderDynamicHeaderButtons(container,
  onClick)` fetches `/api/interface/status`, reads `ui_manifests`, and appends
  one button per manifest entry; `action: "dropdown_menu"` renders a flyout of
  `items` (outside-click closes it). Regular buttons and dropdown items hand
  `(btnConfig, parentBtn)` to the click handler.
- **`dashboard/js/app.js`** — dispatches all four actions:
  `prompt_input` (prompt → POST → alert), `open_modal` (schema fetch → modal
  form → POST to `target_endpoint`), `qa_survey` (step wizard modal) and the
  `status_dot` helper (green dot on `indicate_success: true`). Adds the shared
  `openModal(title, builderFn)` overlay helper.
- **`dashboard/js/ui/config-form.js`** — adds the "Custom Modules Path" text
  field to the Settings form, saved through the existing generic
  `saveAppSettings()` call (no server change needed for that part — it
  already merges whatever keys you send it).
- **`about/set_title.py`** — adds the `create-module` CLI command and its
  boilerplate template (module name → `UI_MANIFEST` + `register_routes`);
  `apply` now reloads update + custom modules through `WiringManager().rewire()`
  and prints a combined summary (catalog + custom modules + bridge).