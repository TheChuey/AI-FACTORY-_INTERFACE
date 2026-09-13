import sys
import os
import subprocess

# Make `python server.py` work from anywhere (server/, root, ...):
#   1. put the project root on sys.path so `engine.*` imports resolve;
#   2. drop this script's own folder from sys.path so our `server.py`
#      does not shadow the `server/` package (`from server import paths`,
#      `from server.chat_store import store`).
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)
sys.path[:] = [p for p in sys.path if os.path.abspath(p) != _SCRIPT_DIR]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List
from datetime import datetime
import json
import os

# App modules:
#   app.core.llm.refresh_models     -> scans installed Ollama models into config/models.json
#   app.agents.registry.list_agents -> scans agent_library/ for available agents
#   app.agents.factory.build_agent  -> builds a fresh Agent from
#                                      agent_library/{agent_id}/agent.md + agent.json,
#                                      replays chat history, and returns the LLM reply
from contextlib import asynccontextmanager
from pathlib import Path

from engine.core.llm import refresh_models
from engine.agents.registry import list_agents
from engine.agents.factory import build_agent, replay_history, AgentNotFoundError
from server.chat_store import store as chat_store
from server import paths

# Modular interface layer (docs/01_IDEA_AND_ARCHITECTURE.md): update modules
# under interface/updates/<domain>/ are discovered and executed natively.
from interface.update_manager import (UpdateManager, get_update_manager,
                                      UPDATES_DIR, ARCHIVE_DIR)
from interface.interface_dispatcher import (InterfaceDispatcher,
                                            get_dispatcher, TRACE_LOG_FILE)
from interface.restore_manager import (RestoreManager, get_restore_manager,
                                       DEFAULT_BASELINE, MANIFEST_NAME)

# Runs once at startup; scans data/chatlog/agent-text-records/*.txt and records
# their header info in data/chatlog/chatRecord.jsonl so past chats appear in
# the drop-down immediately.

# server.py now lives in server/, so the project root is one level up.
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "dashboard"
MODELS_FILE = BASE_DIR / "config" / "models.json"
SETTINGS_FILE = BASE_DIR / "config" / "settings.json"

# Frontend-owned data (written by the /api/history, /api/settings and
# /api/exports endpoints below). Folder locations resolve through app.paths
# so the UI configuration can relocate the data folder.
DATA_DIR = paths.DATA_DIR
HISTORY_FILE = paths.HISTORY_FILE
EXPORTS_DIR = paths.EXPORTS_DIR
APP_SETTINGS_FILE = paths.APP_SETTINGS_FILE

# The chat log lives in data/chatlog/chatRecord.jsonl, owned by
# app.chat_store (import_once / list_log / save_discussion / delete_discussion).
# The legacy /api/discussions endpoints below are thin wrappers over it.


def _load_json(path, default):
    """Read a JSON file; return `default` when missing or unreadable."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _save_json(path, value) -> None:
    """Pretty-write a JSON file, creating parent folders when needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _default_agent() -> str:
    """The agent used when a chat request carries no agent_id.

    Comes from config/settings.json ("default_agent"); falls back to
    "basic_chat" when the file is missing or unreadable.
    """
    try:
        settings = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        return settings.get("default_agent") or "basic_chat"
    except (OSError, json.JSONDecodeError):
        return "basic_chat"


# Startup hook: scan Ollama models BEFORE any request is served, and import
# any existing data/chatlog/agent-text-records/*.txt transcripts into the log
# (data/chatlog/chatRecord.jsonl) so old chats show up in the frontend
# drop-down without manual work.
@asynccontextmanager
async def lifespan(app: FastAPI):
    refresh_models()           # ollama -> config/models.json
    chat_store.import_once()   # agent-text-records/*.txt -> data/chatlog/chatRecord.jsonl

    # Resolved storage locations at boot (cross-platform - data/chat/rag can
    # live anywhere via app_settings.json or GENESSIS_* env overrides).
    _boot_paths = paths.about()
    print("[paths] data      -> " + _boot_paths["data_dir"])
    print("[paths] records   -> " + _boot_paths["chat_records_dir"])
    print("[paths] rag db    -> " + _boot_paths["rag_db_dir"])
    for key, source in _boot_paths.get("sources", {}).items():
        if source != key:
            print(f"[paths] {key} overridden by {source}")

    # Modular interface: discover update modules + traced dispatcher once at
    # startup (exposed on app.state so request handlers can reach them).
    try:
        interface_manager = UpdateManager()
        interface_manager.discover_all_active_modules()
        print("[interface] active update modules: "
              + ", ".join(f"{d}/{', '.join(n) if n else ''}"
                          for d, n in sorted(interface_manager.active_modules_catalog.items())))
        app.state.update_manager = interface_manager
        app.state.interface_dispatcher = InterfaceDispatcher(interface_manager)
    except Exception as exc:   # a broken update module must never block boot
        print(f"[interface] WARNING: update discovery failed: {exc}")
        app.state.update_manager = None
        app.state.interface_dispatcher = None

    yield                      # serve requests; code after this runs on shutdown

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    model: str = ""
    agent_id: str = ""
    history: List[dict] = []  # Prior turns from the frontend: [{role, content}, ...]
    # --- server-side chat session fields ---
    session_id: str = ""      # "" on the first message of a new chat
    title: str = ""           # optional user-chosen title for the chat
    new_chat: bool = False    # start a fresh chat (finalizes the previous one)
    rag: bool = False         # commit this chat to the RAG memory store on save

# --- UI SOURCE OF TRUTH ---

"""
GET /api/models
---------------
What this request is:
    The front-end calls this endpoint on page load to populate the model
    dropdown (#model-select). It is a simple GET request with no body.

What it needs:
    1. A file named "models.json" located in the config folder of the project
       (config/models.json, relative to server.py), written by refresh_models().
    2. The file must contain a "models" key: a list of objects shaped like
       {"id": str, "name": str}.

Behaviour:
    - If models.json exists and has models, the list is returned.
    - If the file is missing, unreadable, or contains no models, the
      endpoint returns an empty list: {"models": []}.
"""

@app.get("/api/models")
async def get_models():
    if not MODELS_FILE.exists():
        print("[MODELS] models.json not found - returning empty list")
        return {"models": []}

    try:
        data = json.loads(MODELS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        print("[MODELS] models.json unreadable - returning empty list")
        return {"models": []}

    models = data.get("models", [])

    if not models:
        print("[MODELS] models.json has no models - returning empty list")
        return {"models": []}

    print("json file sent: models")
    return {"models": models}


@app.get("/api/agents")
async def get_agents():
    """Return every discovered agent from agent_library/.

    Each entry carries {id, name, description, mode}. Adding a new folder
    under agent_library/ (with agent.md + agent.json) automatically makes
    it show up here and in the frontend selector after a restart.
    """
    agents = list_agents()
    print(f"[AGENTS] {len(agents)} agent(s) discovered")
    return {"agents": agents}


@app.get("/api/tools")
async def get_tools():
    """Every tool id an agent can pick in its config (feeds the checkboxes)."""
    from tools.registry import list_tools

    return {"tools": list_tools()}


# --- AGENT CONFIG (the dashboard's per-agent settings editor) ---

def _agent_tests(meta: dict) -> list:
    """The agent's own tests stored in its agent.json (default [])."""
    tests = meta.get("tests") or []
    return tests if isinstance(tests, list) else []


def _shared_tests() -> list:
    """Tests that run for EVERY agent (kept in the app settings)."""
    stored = _load_json(APP_SETTINGS_FILE, {})
    tests = ((stored.get("chatTests") or {}).get("tests")) or []
    return [t for t in tests if isinstance(t, dict) and not t.get("agentId")]


@app.get("/api/agents/{agent_id}/config")
async def get_agent_config(agent_id: str):
    """One agent's consolidated config: agent.json (meta+tests), agent.md raw
    text + parsed sections, and the shared tests that also run for it."""
    from engine.agents.loader import agent_dir, load_definition, AgentNotFoundError

    try:
        definition = load_definition(agent_id)
    except AgentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    meta = definition["meta"]
    md_file = agent_dir(agent_id) / "agent.md"

    return {
        "agent": {
            "id": meta.get("id") or agent_id,
            "name": meta.get("name") or agent_id,
            "description": meta.get("description", ""),
            "mode": meta.get("mode", "chat"),
        },
        "meta": meta,
        "markdown": md_file.exists() and md_file.read_text(encoding="utf-8") or "",
        "tests": _agent_tests(meta),
        "sharedTests": _shared_tests(),
    }


@app.put("/api/agents/{agent_id}/config")
async def save_agent_config(agent_id: str, payload: dict):
    """Partial update of one agent's config.

    Accepts any of {meta, markdown, tests} (each optional):
      - meta:     merged into agent.json (top-level fields only)
      - markdown: written verbatim to agent.md
      - tests:    replaces agent.json#tests (scoped to this agent)
    Always returns the fresh consolidated config.
    """
    from engine.agents.loader import (
        agent_dir,
        load_definition,
        save_markdown,
        save_meta,
        save_tests,
        AgentNotFoundError,
    )

    try:
        load_definition(agent_id)  # 404 when the agent is unknown
    except AgentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    meta_update = payload.get("meta")
    if isinstance(meta_update, dict):
        normalized = dict(meta_update)
        for key in ("name", "description"):
            if key in normalized and not isinstance(normalized[key], str):
                normalized[key] = ""
        if "mode" in normalized and str(normalized["mode"]).lower() not in ("chat", "agent"):
            normalized["mode"] = "chat"
        if "model" in normalized and not normalized["model"]:
            normalized["model"] = None
        if "tools" in normalized and (normalized["tools"] is None or not isinstance(normalized["tools"], list)):
            normalized["tools"] = []
        save_meta(agent_id, normalized)

    markdown_update = payload.get("markdown")
    if isinstance(markdown_update, str):
        save_markdown(agent_id, markdown_update)

    tests_update = payload.get("tests")
    if isinstance(tests_update, list):
        save_tests(agent_id, tests_update)

    definition = load_definition(agent_id)
    meta = definition["meta"]
    md_file = agent_dir(agent_id) / "agent.md"
    return {
        "agent": {
            "id": meta.get("id") or agent_id,
            "name": meta.get("name") or agent_id,
            "description": meta.get("description", ""),
            "mode": meta.get("mode", "chat"),
        },
        "meta": meta,
        "markdown": md_file.exists() and md_file.read_text(encoding="utf-8") or "",
        "tests": _agent_tests(meta),
        "sharedTests": _shared_tests(),
    }

# --- I/O ROUTES ---

@app.post("/api/chat")
def chat(data: ChatRequest):
    """Handle a chat message from the frontend.

    The backend now tracks chat sessions itself (ONE active session at a
    time). Each chat has its own start -> middle -> end:
      - the first message ({new_chat: true}, or no active session) finalizes
        any previous chat and starts a new one;
      - every message appends the user turn + assistant reply to the active
        session (persisted in data/chatlog/.active-chat.json);
      - when a chat ends (new chat, "Save chat" or /api/chats/end), the
        transcript is written once to data/chatlog/agent-text-records/<title>[-v].txt
        and logged in data/chatlog/chatRecord.jsonl.

    The agent is still built FRESH per request and the browser may keep its
    own copy of history, but the server is now the source of truth for the
    conversation so a refresh never loses it.

    This stays a SYNC endpoint on purpose: the blocking LLM call runs in
    FastAPI's threadpool, so the event loop stays free.
    """
    agent_id = data.agent_id or _default_agent()
    print(f"[SERVER] Message for '{agent_id}': {data.message}")
    print(f"[SERVER] history turns received: {len(data.history)}")

    try:
        agent = build_agent(agent_id, model=data.model or None)
    except AgentNotFoundError as exc:
        print(f"[SERVER] {exc}")
        return {"reply": f"(unknown agent '{agent_id}' - is the folder present in agent_library/?)"}

    # One session at a time: start one when asked, otherwise continue it.
    session = chat_store.ensure_session(
        agent,
        session_id=data.session_id,
        title=data.title,
        new_chat=data.new_chat,
        rag=data.rag,
    )

    # Seed the fresh agent with the server's copy of the conversation so the
    # LLM always sees the full chat (browser history is ignored when a session
    # already exists server-side).
    for turn in session.get("messages", []):
        agent.messages.append({"role": turn.get("role"), "content": turn.get("content", "")})

    reply = agent.think(data.message)
    session = chat_store.append_turn(data.message, reply) or session
    print(f"[SERVER] Reply via {agent.model}: {reply[:120]}...")

    return {"reply": reply, "session_id": session["id"], "title": session.get("title", "")}


# --- CHAT SESSIONS (server-side organization) ---

@app.get("/api/chats")
async def list_chats():
    """The chat log (data/chatlog/chatRecord.jsonl): header rows for every
    transcript + the currently active session. Feeds the frontend chats
    drop-down."""
    return {"chats": chat_store.list_log()}


@app.get("/api/chats/{chat_id}")
async def get_chat(chat_id: str):
    """One chat: its log row + the .txt content + parsed messages."""
    chat = chat_store.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail=f"Chat '{chat_id}' not found")
    return chat


@app.post("/api/chats/end")
async def end_chat(payload: dict = None):
    """Finalize the active chat: writes its .txt (versioned on name collision)
    and adds a header row to the log. Safe to call repeatedly.

    payload.rag: optional bool override for committing this chat to the RAG
    memory store (falls back to the chat's stored flag / commitOnSave default).
    """
    payload = payload or {}
    rag = payload.get("rag")
    row = chat_store.finalize_session(
        title=payload.get("title") or payload.get("chatTitle"),
        rag=rag if isinstance(rag, bool) else None,
    )
    if not row:
        return {"finalized": False, "saved": False, "error": "No active chat to finalize."}
    return {"finalized": True, "saved": True, "file": row["fileName"], "id": row["id"], "version": row["version"]}


# --- RAG MEMORY STORE ---

@app.get("/api/rag/status")
async def rag_status():
    """Store location + how many segments are indexed (0 = empty)."""
    from memory.rag_commit import status

    return {"status": status()}


@app.post("/api/rag/rebuild")
async def rag_rebuild():
    """Re-index every saved transcript into the RAG store (idempotent)."""
    from memory.rag_commit import rebuild_store

    return {"message": rebuild_store()}


@app.post("/api/rag/reset")
async def rag_reset():
    """Delete the RAG store so it starts empty (records + transcripts keep)."""
    from memory.rag_commit import purge_store

    return {"message": purge_store()}


@app.delete("/api/chats/{chat_id}")
async def delete_chat(chat_id: str):
    """Permanently erase a chat: its .txt transcript(s) + log records (+ the
    active session when that is the chat being deleted)."""
    result = chat_store.delete_chat(chat_id)
    if not result["recordsRemoved"] and not result["filesRemoved"] and not result["wasActive"]:
        raise HTTPException(status_code=404, detail=f"Chat '{chat_id}' not found")
    return {"deleted": True, "id": chat_id, **result}


# --- DISCUSSIONS (data/chatlog/chatRecord.jsonl - the chat log) ---

@app.get("/api/discussions")
async def list_discussions():
    """Every stored chat header row, newest first (the log)."""
    return {"discussions": chat_store.list_log()}


@app.post("/api/discussions")
async def save_discussion(discussion: dict):
    """Create or update one discussion (upsert by its `id`).

    The server stamps `updatedAt` itself - the frontend never has to.
    Delegated to chat_store, which writes data/chatlog/chatRecord.jsonl.
    """
    discussion_id = discussion.get("id")
    if not discussion_id:
        return {"saved": False, "error": "A discussion needs an 'id' to be saved."}

    discussion["updatedAt"] = datetime.now().isoformat(timespec="seconds")
    saved = chat_store.save_discussion(discussion)
    if saved:
        print(f"[DISCUSSIONS] saved '{discussion_id}'")
    return {"saved": saved}


@app.delete("/api/discussions/{discussion_id}")
async def delete_discussion(discussion_id: str):
    """Permanently remove one discussion by id (404 when unknown)."""
    deleted = chat_store.delete_discussion(discussion_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Discussion '{discussion_id}' not found")
    print(f"[DISCUSSIONS] deleted '{discussion_id}'")
    return {"deleted": True, "id": discussion_id}


# --- HISTORY (data/history.json) ---

@app.get("/api/history")
async def list_history():
    """Every saved message snapshot ("Save" button copies)."""
    return {"history": _load_json(HISTORY_FILE, [])}


@app.post("/api/history")
async def save_history(message: dict):
    """Store one message snapshot (upsert by its `id`)."""
    message_id = message.get("id") or os.urandom(8).hex()
    message["id"] = message_id

    history = _load_json(HISTORY_FILE, [])
    replaced = False
    for index, existing in enumerate(history):
        if existing.get("id") == message_id:
            history[index] = message
            replaced = True
            break

    if not replaced:
        history.append(message)

    _save_json(HISTORY_FILE, history)
    print(f"[HISTORY] saved '{message_id}' ({'updated' if replaced else 'new'})")
    return {"saved": True}


@app.delete("/api/history/{message_id}")
async def delete_history(message_id: str):
    """Remove one saved message by id (404 when unknown)."""
    history = _load_json(HISTORY_FILE, [])
    remaining = [m for m in history if m.get("id") != message_id]

    if len(remaining) == len(history):
        raise HTTPException(status_code=404, detail=f"History item '{message_id}' not found")

    _save_json(HISTORY_FILE, remaining)
    print(f"[HISTORY] deleted '{message_id}'")
    return {"deleted": True, "id": message_id}


# --- APP SETTINGS (static/config/app_settings.json) ---

@app.get("/api/about")
async def get_about():
    """Site identity read from about/about.json (the H1 + tagline on
    index.html). Changed by: `python about/set_title.py`. Read per request,
    so edits apply on the next page load without a server restart.
    """
    about_file = BASE_DIR / "about" / "about.json"
    defaults = {
        "title": "Terminator 2",
        "subtitle": "Pick an agent below to chat with it in the floating chat, or use the chat button in the corner.",
    }
    try:
        data = json.loads(about_file.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    return {
        "title": str(data.get("title") or defaults["title"]).strip(),
        "subtitle": str(data.get("subtitle") or defaults["subtitle"]).strip(),
    }


@app.get("/api/settings")
async def get_app_settings():
    """The stored browser defaults; {} when nothing was saved yet.

    `restartNeeded` is true when the stored path settings (dataDir,
    chatSavePath, ragDbPath) changed since the server started - the running
    process is still using the old resolved folders until a restart.
    """
    payload = _load_json(APP_SETTINGS_FILE, {})
    return {
        "settings": payload,
        "restartNeeded": paths.restart_needed(),
        "platform": paths.platform(),
    }


@app.post("/api/settings")
async def save_app_settings(partial_settings: dict):
    """Merge a partial settings object into what is already stored.

    Path values are stored verbatim - each OS picks its own per-OS key
    (dataDirWindows / dataDirLinux / dataDirMac, ...) or falls back to the
    plain key, and the running server keeps its already-resolved folders
    until a restart (`restartNeeded`)."""
    stored = _load_json(APP_SETTINGS_FILE, {})
    stored.update(partial_settings)

    _save_json(APP_SETTINGS_FILE, stored)
    print(f"[SETTINGS] updated keys: {', '.join(partial_settings.keys()) or '(none)'}")
    return {
        "settings": stored,
        "restartNeeded": paths.restart_needed(),
        "platform": paths.platform(),
    }


# --- CHAT SAVE (write chat transcripts as .txt files) ---

def _sanitize_file_name(raw: str) -> str:
    """Keep only filesystem-friendly characters; fall back to 'chat'."""
    cleaned = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in str(raw).strip())
    cleaned = cleaned.strip("_.") or "chat"
    return cleaned[:120]


def _resolve_chat_dir(raw_path: str) -> Path:
    """Resolve the configured output folder, always anchored inside BASE_DIR.

    - Empty path -> BASE_DIR / "data" / "chatlog" / "agent-text-records"
    - Relative path -> BASE_DIR / <path>
    - Absolute path -> kept only if it stays inside BASE_DIR; otherwise
      an absolute path is re-rooted under BASE_DIR (so a crafted value
      can never escape the project).

    A Windows-style drive path (E:\\... ) has no meaning on Linux and is
    treated as empty there (same rule as server/paths.py).
    """
    raw_path = paths.os_text(raw_path)
    candidate = Path(raw_path or "")

    if not candidate.is_absolute():
        resolved = (BASE_DIR / candidate).resolve()
    else:
        resolved = candidate.resolve()

    # Prevent escaping BASE_DIR (sandbox the save location).
    try:
        resolved.relative_to(BASE_DIR.resolve())
    except ValueError:
        resolved = (BASE_DIR / "data" / "chatlog" / "agent-text-records").resolve()

    return resolved


@app.post("/api/chat-save")
async def save_chat_session(payload: dict):
    """Finalize the ACTIVE chat: name the .txt from the chat title, bump the
    version on a name collision (unless disableVersioning is on), and log it.

    The transcript is built server-side from the active session, so the
    frontend no longer sends raw 'content' per reply. If no active session
    exists, it falls back to writing the legacy payload the old way.
    """
    row = chat_store.finalize_session(title=payload.get("title"))
    if row:
        print(f"[CHAT-SAVE] finalized '{row['title']}' -> {row['fileName']} (v{row['version']})")
        return {"saved": True, "file": str(chat_store.RECORDS_DIR / row["fileName"]), "id": row["id"]}

    content = payload.get("content")
    if content is None:
        return {"saved": False, "error": "No active chat to finalize, and no 'content' supplied."}

    # Legacy fallback: write the raw blob (used by older clients).
    raw_name = str(payload.get("fileName") or "").strip() or "chat"
    safe_name = _sanitize_file_name(raw_name)
    if not safe_name.lower().endswith(".txt"):
        safe_name = f"{safe_name}.txt"

    out_dir = _resolve_chat_dir(str(payload.get("path") or ""))
    out_dir.mkdir(parents=True, exist_ok=True)

    file_path = out_dir / safe_name
    file_path.write_text(str(content), encoding="utf-8")

    print(f"[CHAT-SAVE] wrote {file_path}")
    return {"saved": True, "file": str(file_path)}


# --- WIZARD EXPORTS (data/exports/) ---

def _safe_export_name(raw: str) -> str:
    """Keep only filesystem-friendly characters; fall back to 'export'."""
    cleaned = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in raw.strip())
    cleaned = cleaned.strip("_") or "export"
    return cleaned[:80]


@app.post("/api/exports")
async def save_export(payload: dict):
    """Save one wizard prompt as TWO files: {name}.md + {name}.json.

    The frontend slugifies `name` already; we sanitize it again so a
    crafted name can never escape data/exports/.
    """
    name_raw = str(payload.get("name") or "")
    markdown = payload.get("markdown")
    export_data = payload.get("data")

    if not name_raw or markdown is None or export_data is None:
        return {"saved": False, "error": "An export needs 'name', 'markdown' and 'data'."}

    safe_name = _safe_export_name(name_raw)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

    md_path = EXPORTS_DIR / f"{safe_name}.md"
    json_path = EXPORTS_DIR / f"{safe_name}.json"
    md_path.write_text(str(markdown), encoding="utf-8")
    json_path.write_text(json.dumps(export_data, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"[EXPORTS] wrote {md_path.name} + {json_path.name}")
    return {"saved": True, "files": [md_path.name, json_path.name]}


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
async def home():
    return FileResponse(STATIC_DIR / "index.html")

# --- MODULAR INTERFACE / UPDATE SYSTEM (docs/01_IDEA_AND_ARCHITECTURE.md) ---

# Master switch for /api/interface/run (executes update-module functions with
# arbitrary arguments - the user opted in for this local app). Starts OFF so a
# fresh boot is never armed; /api/interface/toggle-run flips it for the
# current process.
INTERFACE_RUN_ENABLED = False


def _update_manager():
    """The lifespan-created manager, or the process-world singleton when the
    startup discovery failed (so the endpoints never crash)."""
    manager = getattr(app.state, "update_manager", None)
    return manager if manager is not None else get_update_manager()


def _dispatcher():
    dispatcher = getattr(app.state, "interface_dispatcher", None)
    return dispatcher if dispatcher is not None else get_dispatcher()


def _restore_manager():
    manager = getattr(app.state, "restore_manager", None)
    return manager if manager is not None else get_restore_manager()


def _json_safe(value):
    """Best-effort JSON serialization for /api/interface/run results."""
    if isinstance(value, (dict, list, str, int, float, bool)) or value is None:
        return value
    try:
        return json.loads(json.dumps(value, default=str))
    except (TypeError, ValueError):
        return str(value)


class InterfaceRunRequest(BaseModel):
    domain: str
    module: str
    function: str
    args: list = []
    kwargs: dict = {}


class InterfaceToggleRequest(BaseModel):
    enabled: bool


@app.get("/api/interface/status")
def interface_status():
    """Everything the Settings 'Updates / Interface' card needs: the active
    module catalog, the external archive, the trace-log tail and the
    baseline (current-known-good-copy/) freshness + live drift."""
    try:
        manager = _update_manager()
        catalog = {
            domain: sorted(names)
            for domain, names in sorted(manager.active_modules_catalog.items())
        }
    except Exception:
        catalog = {}

    archived: dict[str, list[str]] = {}
    if ARCHIVE_DIR.is_dir():
        for domain_dir in sorted(ARCHIVE_DIR.iterdir()):
            if domain_dir.is_dir():
                archived[domain_dir.name] = sorted(
                    p.name for p in domain_dir.glob("*.py")
                )

    trace_tail: list[str] = []
    if TRACE_LOG_FILE.is_file():
        trace_tail = TRACE_LOG_FILE.read_text(
            encoding="utf-8", errors="replace"
        ).splitlines()[-20:]

    baseline = {
        "folder": str(DEFAULT_BASELINE),
        "exists": DEFAULT_BASELINE.is_dir(),
        "manifest": None,
        "drift": None,
        "error": None,
    }
    try:
        diff = _restore_manager().diff()
        baseline.update({
            "folder": diff["baseline"],
            "exists": Path(diff["baseline"]).is_dir(),
            "drift": {
                "modified": len(diff["modified"]),
                "modified_files": diff["modified"][:50],
                "shared": diff["shared"],
                "skipped": len(diff["skipped"]),
                "untracked": len(diff["untracked"]),
            },
        })
    except Exception as exc:
        baseline["error"] = str(exc)

    manifest_path = Path(baseline["folder"]) / MANIFEST_NAME
    if manifest_path.is_file():
        baseline["manifest"] = _load_json(manifest_path, None)

    return {
        "ok": True,
        "run_enabled": INTERFACE_RUN_ENABLED,
        "updates_dir": str(UPDATES_DIR),
        "archive_dir": str(ARCHIVE_DIR),
        "trace_log": str(TRACE_LOG_FILE),
        "catalog": catalog,
        "archived": archived,
        "trace_tail": trace_tail,
        "baseline": baseline,
    }


@app.post("/api/interface/apply")
def interface_apply():
    """Reload every update module from disk, then regenerate the docs
    snapshots (docs/APP_STRUCTURE.md + docs/APP_CODE_SNAPSHOT.md)."""
    try:
        manager = _update_manager()
        catalog = manager.reload_all()
        print("[interface] apply: reloaded modules per domain:"
              + ", ".join(f"{d}={len([n for n in ns])}"
                          for d, ns in sorted(catalog.items())))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"module reload failed: {exc}")

    docs_script = BASE_DIR / "scripts" / "update_docs.py"
    docs_ok = True
    if docs_script.is_file():
        result = subprocess.run(
            [sys.executable, str(docs_script)], cwd=str(BASE_DIR)
        )
        docs_ok = result.returncode == 0
    else:
        docs_ok = False

    return {
        "ok": True,
        "catalog": {
            d: sorted(names)
            for d, names in sorted(_update_manager().active_modules_catalog.items())
        },
        "docs_regenerated": docs_ok,
    }


@app.post("/api/interface/snapshot")
def interface_snapshot():
    """Publish the current live tree as the new baseline (rebaseline)."""
    try:
        count = _restore_manager().snapshot_baseline()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"snapshot failed: {exc}")
    return {"ok": True, "files": count, "baseline": str(DEFAULT_BASELINE)}


@app.post("/api/interface/restore")
def interface_restore(payload: dict = None):
    """Roll the live tree back to the baseline. DRY-RUN by default - the
    browser must send {"apply": true} (or {"dryRun": false}) to actually
    restore. A real restore backs everything up first into
    data/snapshots/pre_restore_backup/."""
    payload = payload or {}
    baseline = payload.get("baseline")
    requested = payload.get("apply", False)
    dry_run = requested is not True
    if payload.get("dryRun") is False:
        dry_run = False
    if dry_run:
        result = _restore_manager().restore(baseline=baseline, dry_run=True)
        return {"ok": True, "dry_run": True, **result}
    try:
        result = _restore_manager().restore(baseline=baseline, dry_run=False)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"restore failed: {exc}")
    return {"ok": True, "dry_run": False, **result}


@app.post("/api/interface/run")
def interface_run(data: InterfaceRunRequest):
    """Execute an update-module function by (domain, module, function) names.
    Arbitrary code execution - gated by INTERFACE_RUN_ENABLED, which the
    Settings card arms explicitly via /api/interface/toggle-run."""
    if not INTERFACE_RUN_ENABLED:
        raise HTTPException(
            status_code=403,
            detail="Module execution is disabled. Enable it in Settings -> "
                   "Updates / Interface first.",
        )
    try:
        result = _dispatcher().execute_action(
            data.domain, data.module, data.function,
            *data.args, **data.kwargs,
        )
    except ModuleNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}")
    return {"ok": True, "domain": data.domain, "module": data.module,
            "function": data.function, "result": _json_safe(result)}


@app.post("/api/interface/toggle-run")
def interface_toggle_run(data: InterfaceToggleRequest):
    """Arm/disarm /api/interface/run for this process. The flip is logged to
    data/interface_trace.log so a change of state is never silent."""
    global INTERFACE_RUN_ENABLED
    INTERFACE_RUN_ENABLED = data.enabled
    entry = f"[RUN TOGGLE] module execution {'ENABLED' if data.enabled else 'DISABLED'}"
    print(entry)
    try:
        from interface.interface_dispatcher import logger as _trace_logger
        _trace_logger.info(entry)
    except Exception:
        pass
    return {"ok": True, "run_enabled": INTERFACE_RUN_ENABLED}


if __name__ == "__main__":
    import uvicorn
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host=host, port=port)
