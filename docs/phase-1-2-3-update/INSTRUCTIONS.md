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

## 2. Files to ADD (new — don't exist in your project yet)

| New file | Goes at |
|---|---|
| `interface/custom_module_manager.py` | `interface/custom_module_manager.py` |

That's the only brand-new source file. Everything else is a folder that
gets created **automatically** the first time the server boots (see below) —
you don't need to make it by hand, but you can if you want it to exist ahead
of time.

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

---

## Updated project tree (only the touched/added paths are marked)

```
genV2_Interface_projectManager/
├── about/
│   └── set_title.py                       ← REPLACE (adds `create-module`)
├── dashboard/
│   ├── config/
│   │   └── app_settings.json              (unchanged — gains "customModulesPath" key
│   │                                         automatically the first time you save Settings)
│   └── js/
│       ├── app.js                         ← REPLACE (wires dynamic header buttons)
│       └── ui/
│           ├── config-form.js             ← REPLACE (adds "Custom Modules Path" field)
│           └── header-nav.js              ← REPLACE (adds renderDynamicHeaderButtons)
├── data/
│   └── custom_modules/                    ← NEW FOLDER (auto-created at boot)
│       └── <your-generated-modules>.py    ← where `create-module` writes files
├── interface/
│   ├── custom_module_manager.py           ← ADD (new file)
│   ├── update_manager.py                  (unchanged — your existing domain system)
│   ├── interface_dispatcher.py            (unchanged)
│   ├── restore_manager.py                 (unchanged)
│   └── updates/                           (unchanged)
└── server/
    ├── paths.py                           ← REPLACE (adds CUSTOM_MODULES_DIR)
    └── server.py                          ← REPLACE (loads + registers custom modules)
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
automatically — no template or JS edits needed. Clicking it prompts for
input (per `prompt_message`) and POSTs to the module's `api_endpoint`.

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
- **`server/server.py`** — at startup (`lifespan`), creates a
  `CustomModuleManager`, calls `register_routes(app)` once per module, and
  remembers which ones are already registered (`_CUSTOM_ROUTES_REGISTERED`)
  so `apply` can register new ones live without double-registering old ones.
  `GET /api/interface/status` now also returns `custom_modules` (folder +
  active names) and `ui_manifests` (every active module's manifest, for the
  frontend to render buttons from).
- **`dashboard/js/ui/header-nav.js`** — new export
  `renderDynamicHeaderButtons(container, onClick)` fetches
  `/api/interface/status`, reads `ui_manifests`, and appends one button per
  manifest entry into `container`, wired to `onClick`.
- **`dashboard/js/app.js`** — calls that function right after mounting the
  normal nav row, with a click handler that follows each button's
  `action: "prompt_input"` contract (prompt → POST `api_endpoint` → alert
  the response).
- **`dashboard/js/ui/config-form.js`** — adds the "Custom Modules Path" text
  field to the Settings form, saved through the existing generic
  `saveAppSettings()` call (no server change needed for that part — it
  already merges whatever keys you send it).
- **`about/set_title.py`** — adds the `create-module` CLI command and its
  boilerplate template (module name → `UI_MANIFEST` + `register_routes`),
  plus a summary line for the custom-module catalog in `apply`.
