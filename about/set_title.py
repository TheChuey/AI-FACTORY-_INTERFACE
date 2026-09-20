"""Change the app title/subtitle shown as the H1 on index.html.

Usage:
    python about/set_title.py                      edit about.json interactively
    python about/set_title.py [title [subtitle]]   set title/subtitle positionally
    python about/set_title.py create-module <name>  scaffold a new drop-in module
                                                      (Phase 3 - CLI Module Generator)

about.json is read by the server on every request, so a title change shows
after a refresh.
"""
import json
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve()
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

F = _SCRIPT_DIR.parent / "about.json"


def _save_about(data: dict) -> None:
    F.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _load_about() -> dict:
    return json.loads(F.read_text(encoding="utf-8")) if F.exists() else {}


# --------------------------------------------------------------------------
# Phase 3 - CLI Module Generator
# --------------------------------------------------------------------------
# Scaffolds a new drop-in .py module inside the configured custom modules
# folder (server.paths.CUSTOM_MODULES_DIR - default data/custom_modules/,
# or wherever "Custom Modules Path" in Settings points). The generated file
# already has a valid UI_MANIFEST (Phase 2 - a header button that appears
# automatically) and register_routes(app) (Phase 1 - an auto-registered
# FastAPI endpoint) - drop it in, apply/restart, and it's live.

MODULE_TEMPLATE = '''"""
Drop-in Update Module: {module_name}.py
Automatically loaded by CustomModuleManager from {custom_dir}
"""

# ----------------------------------------------------------------
# 1. UI MANIFEST (Exposed via GET /api/interface/status -> ui_manifests)
# ----------------------------------------------------------------
UI_MANIFEST = {{
    "module_id": "{module_name}",
    "buttons": [
        {{
            "id": "btn-{module_name}",
            "label": "\uff0b {label}",
            "target": "header",
            "action": "prompt_input",
            "prompt_message": "Enter name/parameter for {label}:",
            "api_endpoint": "/api/{module_name}/execute",
            "title": "Trigger {label} action"
        }}
    ]
}}


# ----------------------------------------------------------------
# 2. AUTO-ROUTE REGISTRATION (Hooked by server/server.py's lifespan +
#    POST /api/interface/apply for newly-added modules)
# ----------------------------------------------------------------
def register_routes(app):
    """Registers FastAPI endpoints automatically at server startup."""

    @app.post("/api/{module_name}/execute")
    def execute_module_action(payload: dict):
        user_input = payload.get("project_name") or payload.get("input", "Default")
        # Add your feature logic here.
        return {{
            "status": "success",
            "message": f"[{module_name}] Successfully processed input: {{user_input}}",
        }}
'''


def cmd_create_module(argv):
    """Generate a new boilerplate drop-in module template in the custom
    modules folder."""
    if not argv:
        print("Usage: python about/set_title.py create-module <module_name>")
        return 1

    from server.paths import CUSTOM_MODULES_DIR

    module_name = argv[0].lower().replace("-", "_").replace(".py", "")
    if not module_name or not module_name.replace("_", "").isalnum():
        print(f"Error: '{argv[0]}' is not a valid module name (letters, numbers, - and _ only).")
        return 1

    target_dir = CUSTOM_MODULES_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    file_path = target_dir / f"{module_name}.py"
    if file_path.exists():
        print(f"Error: Module '{file_path.name}' already exists in {target_dir}")
        return 1

    label = module_name.replace("_", " ").title()
    content = MODULE_TEMPLATE.format(
        module_name=module_name,
        label=label,
        custom_dir=target_dir,
    )
    file_path.write_text(content, encoding="utf-8")

    print(f"\u2713 Created new drop-in module: {file_path}")
    print("\u27a4 Restart your server, or POST /api/interface/apply to activate it.")
    return 0


def cmd_title(argv) -> int:
    """Original behavior: edit about.json interactively or positionally."""
    data = _load_about()
    data.setdefault("title", "Genessis")
    data.setdefault("subtitle", "Home")

    for i, key in enumerate(("title", "subtitle")):
        value = argv[i] if i < len(argv) else None
        if value is None:
            try:
                value = input(f"{key} [{data[key]}]: ").strip()
            except EOFError:
                break
        if value:
            data[key] = value

    _save_about(data)
    print("Saved ->", data["title"])
    return 0


COMMANDS = {
    "create-module": cmd_create_module,  # <-- Phase 3
}


def main() -> int:
    args = sys.argv[1:]
    if args and args[0] in COMMANDS:
        return COMMANDS[args[0]](args[1:])
    return cmd_title(args)


if __name__ == "__main__":
    sys.exit(main())
