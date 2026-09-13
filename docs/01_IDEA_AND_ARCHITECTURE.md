# 01_IDEA_AND_ARCHITECTURE.md: Modular Interface & System Update Architecture

## 1. Executive Summary & Core Idea

As an application grows, adding new features, experimental logic, or system updates directly into core modules increases complexity and risks breaking existing functionality. This architecture introduces a **Modular Interface & Change Tracking System** for the app.

The key objectives are:
1. **Isolation of Code Additions**: New updates are placed in domain-specific folders (`interface/updates/engine/`, `interface/updates/tools/`, `interface/updates/server/`) without modifying core files.
2. **Direct Module Object Access (Option B)**: The system dynamically discovers imported Python module objects, allowing developers to execute module functions natively (e.g., `update_manager.get_active_module("engine", "newfunction").execute_new_logic()`).
3. **Line-Number Change Tracing**: Execution calls can be wrapped in a dispatcher that uses Python's `inspect` module to log exact caller line numbers and file paths for troubleshooting.
4. **External Archiving**: Inactive or retired update modules are moved out of the main codebase into an external archive folder (`data/interface_archive/`) to prevent repo bloat.
5. **System-Wide Update & Contained Restoration**:
   - **Apply**: Reloads all active update modules and regenerates documentation snapshots (`APP_STRUCTURE.md` and `APP_CODE_SNAPSHOT.md`).
   - **Restore**: An isolated restoration system compares the current codebase against a known baseline (the `current-known-good-copy/` folder) using SHA-256 hashes, creates a safety backup (`data/snapshots/pre_restore_backup/`), excludes user data/env paths (`data/`, `venv/`, `.git/`, `app_settings.json`), and safely rolls back modified files.

---

## 2. Target Architecture & Directory Layout

The new components integrate seamlessly into the app structure:

```text
terminator1/
├── interface/
│   ├── interface_dispatcher.py    # Line-number tracing & execution dispatcher
│   ├── update_manager.py          # Dynamic module discovery (Option B) & external archiver
│   ├── restore_manager.py         # Isolated baseline comparison, backup & rollback manager
│   └── updates/                   # Active update modules (grouped by domain)
│       ├── engine/                # E.g., newfunction.py, agent_patch.py
│       ├── tools/                 # E.g., custom_capability.py
│       └── server/                # E.g., route_extensions.py
├── about/
│   ├── about.json
│   └── set_title.py               # Updated with 'apply' and 'restore' CLI triggers
├── data/
│   ├── interface_archive/         # External archive directory for retired update files
│   └── snapshots/
│       └── pre_restore_backup/    # Automated pre-restoration safety snapshot
├── current-known-good-copy/       # Complete working copy of the last good source
│                                  # (the restore baseline, regenerated via `snapshot`)
├── scripts/
│   └── update_docs.py             # Codebase snapshot generator
├── docs/
│   ├── APP_STRUCTURE.md           # Auto-generated folder-tree snapshot
│   └── APP_CODE_SNAPSHOT.md       # Auto-generated per-file source snapshot
└── test/                          # Legacy pre-infection snapshot (recovery reference)
```

---

## 3. Component Breakdown & Responsibilities

### Component A: `UpdateManager` (`interface/update_manager.py`)
- **Discovery**: Automatically scans all `.py` files in `interface/updates/` subdirectories (`engine/`, `tools/`, `server/`) and imports them.
- **Cataloging**: Stores live module objects in `active_modules_catalog` formatted as `{ "domain": { "module_name": module_object } }`.
- **Option B Access**: Exposes `get_active_module(domain_name, module_name)` to return the live module object for direct, native execution.
- **External Archiving**: Provides `move_module_to_external_archive(domain_name, module_name)`, which physically moves `.py` files out of the repository into `data/interface_archive/<domain>/` and refreshes the catalog.

### Component B: `InterfaceDispatcher` (`interface/interface_dispatcher.py`)
- **Caller Tracing**: Inspects the call stack using `inspect.currentframe().f_back` to retrieve the filename and line number of the caller.
- **Execution Logging**: Logs trace entries showing the exact function name, module, and line number before execution.
- **Traced Execution**: Provides `trace_and_execute(target_function, *args)` to wrap native Option B module calls with line logging.

### Component C: `RestoreManager` (`interface/restore_manager.py`)
- **Checksum Comparison**: Computes SHA-256 file hashes for every file in the active codebase against the baseline folder (`current-known-good-copy/` by default).
- **Safety Backup**: Creates a complete snapshot in `data/snapshots/pre_restore_backup/` before overwriting any file.
- **Exclusion Safety**: Strictly excludes runtime data and configuration paths (`data/`, `venv/`, `.git/`, `__pycache__`, `dashboard/config/app_settings.json`, `about/about.json`) to preserve user settings and chat logs.
- **Restoration & Doc Sync**: Overwrites corrupted/modified files from the clean baseline and executes `scripts/update_docs.py` to keep documentation snapshots accurate.

### Component D: Action Trigger Integration (`about/set_title.py`)
- **CLI Commands**:
  - `python about/set_title.py apply`: Re-discovers active modules and runs `scripts/update_docs.py`.
  - `python about/set_title.py snapshot [dest]`: Publishing the current tree into `current-known-good-copy/` (the restore baseline).
  - `python about/set_title.py restore [optional_baseline]`: Invokes `RestoreManager` to execute the rollback workflow.
  - Default execution (no arguments) preserves interactive title/subtitle editing.

---

## 4. System Workflow & Data Flow

1. **Adding New Features**:
   - Create a Python file under `interface/updates/<domain>/` (e.g., `interface/updates/engine/newfunction.py`).
   - Run `python about/set_title.py apply` to register the update and refresh documentation.
2. **Executing Logic (Option B)**:
   - Access the module via `module = update_manager.get_active_module("engine", "newfunction")`.
   - Call the function natively: `module.execute_new_logic(data)`.
3. **Archiving Inactive Code**:
   - Call `update_manager.move_module_to_external_archive("engine", "newfunction")`.
   - File is moved to `data/interface_archive/engine/newfunction.py`.
4. **Refreshing the Baseline**:
   - Run `python about/set_title.py snapshot` to publish the current known-good tree into `current-known-good-copy/`.
5. **Restoring Baseline**:
   - Run `python about/set_title.py restore`.
   - `RestoreManager` backs up the current codebase to `data/snapshots/pre_restore_backup/`, restores modified files from `current-known-good-copy/`, and regenerates `APP_STRUCTURE.md` and `APP_CODE_SNAPSHOT.md`.

---

## 5. Design Decisions

- **Restore semantics**: only files present in BOTH the live tree and the baseline whose SHA-256 differs are overwritten. Files that exist only in the baseline or only in the live tree are reported but left untouched.
- **Baseline**: `current-known-good-copy/` is the default restore baseline. The legacy `test/` (pre-infection snapshot) is used as a fallback with a staleness warning.
- **Exclusions**: `data/`, `venv/`, `.git/`, `__pycache__/`, `current-known-good-copy/`, `test/`, `dashboard/config/app_settings.json`, `about/about.json`, `*.bak`, `*.pyc`, `*.pyo`.