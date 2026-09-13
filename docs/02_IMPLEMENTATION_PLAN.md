# 02_IMPLEMENTATION_PLAN.md: Step-by-Step Implementation Guide & AI Prompt

## Executive Instructions for AI Developer / Workflow

Use the following step-by-step implementation guide and verbatim code blocks to implement the Modular Interface, Update Manager, Restore Manager, and Command Triggers in the codebase.

---

## Step-by-Step Implementation Guide

### Step 1: Create Directory Layout
Create the `interface/` directory structure and external archive/backup folders:
- `interface/updates/engine/`
- `interface/updates/tools/`
- `interface/updates/server/`
- `data/interface_archive/`
- `data/snapshots/pre_restore_backup/`

### Step 2: Implement `interface/update_manager.py`
Add `UpdateManager` to handle dynamic module discovery across domain directories, Option B direct module retrieval, and external archiving.

### Step 3: Implement `interface/interface_dispatcher.py`
Add `InterfaceDispatcher` to capture caller line numbers (`inspect.currentframe().f_back.f_lineno`) and log function execution.

### Step 4: Implement `interface/restore_manager.py`
Add `RestoreManager` to compare active codebase files against `test/` baseline hashes, create safety backups, apply path exclusions, and perform restorations.

### Step 5: Update `about/set_title.py`
Extend `about/set_title.py` to handle `apply` and `restore` CLI commands while maintaining interactive title/subtitle editing.

### Step 6: Create Sample Update Module
Add `interface/updates/engine/newfunction.py` as an initial update file to verify Option B dynamic loading.

### Step 7: Wire into Server Startup & Refresh Docs
Initialize `UpdateManager` and `InterfaceDispatcher` in `server/server.py` at startup, then run:
```bash
venv/bin/python scripts/update_docs.py
```

---

## Copy-Paste Implementation Prompt for AI Developer

```text
PROMPT: Implement Modular Interface, Update Manager, Restore Manager, and CLI Triggers

Goal: Implement a modular interface system under `interface/` that dynamically loads Python module files across domain folders (`engine/`, `tools/`, `server/`), supports Option B direct module access, traces caller line numbers, manages external archiving in `data/interface_archive/`, and provides baseline restoration via `about/set_title.py`.

MANDATORY REQUIREMENT: You MUST use the exact Python code blocks provided below verbatim without shortening variable names or modifying logic.

--------------------------------------------------------------------------------
1. File: interface/update_manager.py
--------------------------------------------------------------------------------
import importlib
import shutil
from pathlib import Path

PROJECT_ROOT_DIRECTORY = Path(__file__).resolve().parent.parent
ACTIVE_UPDATES_DIRECTORY = Path(__file__).resolve().parent / "updates"
EXTERNAL_ARCHIVE_DIRECTORY = PROJECT_ROOT_DIRECTORY / "data" / "interface_archive"


class UpdateManager:
    """Discovers active update modules in interface/updates/ and manages external archiving."""

    def __init__(self):
        # Structure: { "engine": {"newfunction": <module_object>} }
        self.active_modules_catalog = {}

    def discover_all_active_modules(self):
        """Scans interface/updates/ for active Python files grouped by domain folder."""
        self.active_modules_catalog.clear()

        for domain_folder in ACTIVE_UPDATES_DIRECTORY.iterdir():
            if domain_folder.is_dir() and not domain_folder.name.startswith(("_", ".")):
                domain_name = domain_folder.name
                self.active_modules_catalog[domain_name] = {}

                for python_file in domain_folder.glob("*.py"):
                    if python_file.name.startswith("_"):
                        continue
                    module_name = python_file.stem
                    import_path = f"interface.updates.{domain_name}.{module_name}"
                    self.active_modules_catalog[domain_name][module_name] = importlib.import_module(import_path)

    def get_active_module(self, domain_name: str, module_name: str):
        """Option B Direct Access: Returns the live Python module object for direct calls."""
        return self.active_modules_catalog.get(domain_name, {}).get(module_name)

    def list_domain_modules(self, domain_name: str) -> list:
        """Returns a list of all loaded module names under a domain."""
        return list(self.active_modules_catalog.get(domain_name, {}).keys())

    def move_module_to_external_archive(self, domain_name: str, module_name: str):
        """Moves an inactive module file from the codebase to the external archive folder."""
        source_file_path = ACTIVE_UPDATES_DIRECTORY / domain_name / f"{module_name}.py"
        if not source_file_path.exists():
            raise FileNotFoundError(f"Source update file does not exist: {source_file_path}")

        target_archive_directory = EXTERNAL_ARCHIVE_DIRECTORY / domain_name
        target_archive_directory.mkdir(parents=True, exist_ok=True)
        target_file_path = target_archive_directory / f"{module_name}.py"

        shutil.move(str(source_file_path), str(target_file_path))
        self.discover_all_active_modules()  # Refresh catalog after moving
        return str(target_file_path)


--------------------------------------------------------------------------------
2. File: interface/interface_dispatcher.py
--------------------------------------------------------------------------------
import inspect
import logging

logger = logging.getLogger("app_change_tracker")


class InterfaceDispatcher:
    """Provides line-number execution tracing and function dispatching."""

    def __init__(self, update_manager):
        self.update_manager = update_manager

    def trace_and_execute(self, target_function, *arguments, **keyword_arguments):
        """Option B Traced Execution: Accepts a direct module function reference, logs caller line numbers, and executes."""
        caller_frame = inspect.currentframe().f_back
        line_number_in_code = caller_frame.f_lineno if caller_frame else "Unknown Line"
        source_file_path = caller_frame.f_code.co_filename if caller_frame else "Unknown File"

        function_name = getattr(target_function, "__name__", str(target_function))
        module_name = getattr(target_function, "__module__", "Unknown Module")

        logger.info(
            f"[TRACE LOG] Executing '{function_name}' from '{module_name}' "
            f"called from {source_file_path} at line {line_number_in_code}"
        )

        return target_function(*arguments, **keyword_arguments)

    def execute_action(self, domain_category: str, submodule_name: str, function_to_call: str, *arguments, **keyword_arguments):
        """Dispatches an action via string identifiers."""
        target_module = self.update_manager.get_active_module(domain_category, submodule_name)
        if not target_module:
            raise ModuleNotFoundError(
                f"Active update module '{submodule_name}' under domain '{domain_category}' was not found."
            )

        target_function = getattr(target_module, function_to_call)
        return self.trace_and_execute(target_function, *arguments, **keyword_arguments)


--------------------------------------------------------------------------------
3. File: interface/restore_manager.py
--------------------------------------------------------------------------------
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT_DIRECTORY = Path(__file__).resolve().parent.parent
DEFAULT_BASELINE_DIRECTORY = PROJECT_ROOT_DIRECTORY / "test"
SNAPSHOT_BACKUP_DIRECTORY = PROJECT_ROOT_DIRECTORY / "data" / "snapshots" / "pre_restore_backup"

EXCLUDED_RESTORE_PATHS = {
    "data",
    "venv",
    ".git",
    "__pycache__",
    "dashboard/config/app_settings.json",
}


class RestoreManager:
    """Manages baseline verification, pre-restore backups, file restoration, and doc updates."""

    def __init__(self, project_root: Path = PROJECT_ROOT_DIRECTORY):
        self.project_root = Path(project_root)

    def calculate_file_hash(self, file_path: Path) -> str:
        """Calculates SHA-256 hash for file comparison."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as target_file:
            for byte_block in iter(lambda: target_file.read(65536), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def should_exclude_path(self, relative_path_str: str) -> bool:
        """Checks if a path should be skipped during restoration."""
        normalized_path = relative_path_str.replace("\\", "/")
        for excluded_item in EXCLUDED_RESTORE_PATHS:
            if normalized_path == excluded_item or normalized_path.startswith(f"{excluded_item}/"):
                return True
        return False

    def create_pre_restore_backup(self):
        """Copies the current working codebase into a pre-restore backup directory."""
        print(f"[RESTORE] Creating safety backup in: {SNAPSHOT_BACKUP_DIRECTORY}")
        if SNAPSHOT_BACKUP_DIRECTORY.exists():
            shutil.rmtree(SNAPSHOT_BACKUP_DIRECTORY)

        SNAPSHOT_BACKUP_DIRECTORY.mkdir(parents=True, exist_ok=True)

        for source_item in self.project_root.rglob("*"):
            relative_path = source_item.relative_to(self.project_root)
            relative_str = str(relative_path)

            if self.should_exclude_path(relative_str):
                continue

            destination_item = SNAPSHOT_BACKUP_DIRECTORY / relative_path
            if source_item.is_dir():
                destination_item.mkdir(parents=True, exist_ok=True)
            elif source_item.is_file():
                destination_item.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_item, destination_item)

        print("[RESTORE] Safety backup created successfully.")

    def restore_from_baseline(self, baseline_source_directory: str = None):
        """Restores codebase files from a known good baseline directory."""
        source_dir = Path(baseline_source_directory) if baseline_source_directory else DEFAULT_BASELINE_DIRECTORY

        if not source_dir.exists():
            raise FileNotFoundError(f"[RESTORE ERROR] Baseline directory does not exist: {source_dir}")

        print(f"[RESTORE] Initiating restoration from baseline: {source_dir}")

        # 1. Create safety backup of current state
        self.create_pre_restore_backup()

        # 2. Compare and restore files
        restored_files_count = 0
        for baseline_file in source_dir.rglob("*"):
            if not baseline_file.is_file():
                continue

            relative_path = baseline_file.relative_to(source_dir)
            relative_str = str(relative_path)

            if self.should_exclude_path(relative_str):
                continue

            target_file_path = self.project_root / relative_path

            # Check if file needs updating
            needs_copy = False
            if not target_file_path.exists():
                needs_copy = True
            else:
                if self.calculate_file_hash(baseline_file) != self.calculate_file_hash(target_file_path):
                    needs_copy = True

            if needs_copy:
                target_file_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(baseline_file, target_file_path)
                print(f"  -> Restored: {relative_str}")
                restored_files_count += 1

        print(f"[RESTORE] Total files restored: {restored_files_count}")

        # 3. Refresh documentation snapshots
        print("[RESTORE] Regenerating documentation snapshots...")
        update_script = self.project_root / "scripts" / "update_docs.py"
        subprocess.run([sys.executable, str(update_script)], check=True)
        print("[RESTORE] System restoration completed successfully.")


--------------------------------------------------------------------------------
4. File: about/set_title.py
--------------------------------------------------------------------------------
"""Change the app title/subtitle shown on index.html OR execute app update commands.

Usage:
    python about/set_title.py [title [subtitle]]
    python about/set_title.py apply
    python about/set_title.py restore [snapshot_path]
"""
import json
import subprocess
import sys
from pathlib import Path

ABOUT_JSON_FILE_PATH = Path(__file__).parent / "about.json"
PROJECT_ROOT_DIRECTORY = Path(__file__).resolve().parent.parent


def execute_system_update():
    """Refreshes active interface modules and regenerates documentation snapshots."""
    print("[UPDATE TRIGGER] Discovering and refreshing active update modules...")
    from interface.update_manager import UpdateManager
    update_manager = UpdateManager()
    update_manager.discover_all_active_modules()
    print("[UPDATE TRIGGER] Active modules successfully cataloged.")

    print("[UPDATE TRIGGER] Regenerating APP_STRUCTURE.md and APP_CODE_SNAPSHOT.md...")
    update_script = PROJECT_ROOT_DIRECTORY / "scripts" / "update_docs.py"
    subprocess.run([sys.executable, str(update_script)], check=True)
    print("[UPDATE TRIGGER] Documentation snapshots successfully updated.")


def execute_system_restore(baseline_source_directory: str = None):
    """Triggers the isolated RestoreManager to rollback code to a known baseline."""
    from interface.restore_manager import RestoreManager
    restore_manager = RestoreManager()
    restore_manager.restore_from_baseline(baseline_source_directory=baseline_source_directory)


def handle_title_update(arguments_list):
    """Default interactive/argument-driven title and subtitle editor."""
    data = json.loads(ABOUT_JSON_FILE_PATH.read_text(encoding="utf-8")) if ABOUT_JSON_FILE_PATH.exists() else {}
    data.setdefault("title", "Genessis")
    data.setdefault("subtitle", "Home")

    for index_key, key_name in enumerate(("title", "subtitle")):
        value = arguments_list[index_key] if index_key < len(arguments_list) else None
        if value is None:
            try:
                value = input(f"{key_name} [{data[key_name]}]: ").strip()
            except EOFError:
                break
        if value:
            data[key_name] = value

    ABOUT_JSON_FILE_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Saved ->", data["title"])


def main():
    command_line_arguments = sys.argv[1:]

    if command_line_arguments:
        first_argument_action = command_line_arguments[0].lower()
        if first_argument_action == "apply":
            execute_system_update()
            return
        elif first_argument_action == "restore":
            target_snapshot = command_line_arguments[1] if len(command_line_arguments) > 1 else None
            execute_system_restore(baseline_source_directory=target_snapshot)
            return

    handle_title_update(command_line_arguments)


if __name__ == "__main__":
    main()


--------------------------------------------------------------------------------
5. File: interface/updates/engine/newfunction.py
--------------------------------------------------------------------------------
"""
LOCATION: interface/updates/engine/newfunction.py
USAGE (Option B Direct Access):
    module = update_manager.get_active_module("engine", "newfunction")
    result = module.execute_new_logic("Input Data")
"""
import logging

logger = logging.getLogger("app_change_tracker")


def execute_new_logic(data_payload: str):
    """Example logic function for engine updates."""
    logger.info(f"[ENGINE: newfunction] Processing payload: {data_payload}")
    return f"Engine processed payload: {data_payload}"


def secondary_engine_action(value: int):
    """Secondary action inside the same module file."""
    return value * 10


--------------------------------------------------------------------------------
6. Execution Tasks:
--------------------------------------------------------------------------------
1. Create folder structure (`interface/updates/engine/`, `interface/updates/tools/`, `interface/updates/server/`, `data/interface_archive/`).
2. Write `interface/update_manager.py` verbatim.
3. Write `interface/interface_dispatcher.py` verbatim.
4. Write `interface/restore_manager.py` verbatim.
5. Update `about/set_title.py` verbatim.
6. Write sample module `interface/updates/engine/newfunction.py`.
7. Execute: `python about/set_title.py apply`
8. Execute: `venv/bin/python scripts/update_docs.py`
```
