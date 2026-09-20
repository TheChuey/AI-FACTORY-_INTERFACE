"""
app/chat_store/store.py
=======================

Server-side chat organization: one in-progress chat session PER AGENT.

Files:
    data/chatlog/chatRecord.jsonl            -> the LOG: one record per chat
    data/chatlog/.active-chat.json           -> {agentId: session} map of the
                                                live conversations in progress
    data/chatlog/agent-text-records/*.txt     -> ONE transcript per chat

Lifecycle of a chat (its own start -> middle -> end):
    start  (new chat, or the first message after a restart/finalize)
    turn   (each /api/chat call appends the user message + assistant reply and
            persists the session JSON; NO .txt is written per-reply)
    end    (/api/chats/end, "Save chat", or a new chat starting) writes the
            transcript as a new '# VERSION N' SECTION inside the chat's ONE
            .txt file, and updates the chat's single record in
            chatRecord.jsonl. Version 1, 2, ..., 3 -> the frontend can then
            OFFER AI consolidation ('# CONSOLIDATED'), which keeps a summary
            plus the full conversation in the same file.

The browser never owns the transcript anymore: the server tracks each chat, and
data/chatlog/agent-text-records/*.txt is the source of truth that the records
point at. The records and the live session stay directly in data/chatlog/.

On startup, import_once() also migrates the old layout (separate -N.txt files,
data/chats/*.txt, data/discussions.json) into data/chatlog/ so nothing is lost
when upgrading.
"""

import hashlib
import json
import re
import shutil
import threading
import uuid
from datetime import datetime
from pathlib import Path

from . import logger as chat_logger
from server import paths

BASE_DIR = Path(__file__).resolve().parents[2]
# All folders/files below resolve through app/paths so the UI configuration
# (dataDir / chatSavePath / ragDbPath in app_settings.json) controls where
# chats, transcripts, history, exports and the RAG store actually live.
DATA_DIR = paths.DATA_DIR
CHATS_DIR = paths.CHATS_DIR
RECORDS_DIR = paths.RECORDS_DIR
# The ONE metadata file: a JSONL log of every chat version. chatRecord.jsonl
# replaced the old log-chats.json (JSON array, one row per chat) - the "one
# row per chat" view is now derived at read time by list_log(). Old files are
# migrated into it by import_once() and then deleted.
LOG_FILE = paths.LOG_FILE
ACTIVE_SESSION_FILE = paths.ACTIVE_SESSION_FILE
APP_SETTINGS_FILE = paths.APP_SETTINGS_FILE

_LEGACY_CHATS_DIR = DATA_DIR / "chats"
_LEGACY_LOG_FILE = DATA_DIR / "discussions.json"
_OLD_LOGCHATS_FILE = CHATS_DIR / "log-chats.json"   # superseded by chatRecord.jsonl
_OLD_JSONL_FILE = CHATS_DIR / "chat_log.jsonl"      # superseded by chatRecord.jsonl

_lock = threading.Lock()

# The single JSONL logger behind every read/write of chatRecord.jsonl.
_metadata_logger = chat_logger.ChatLogger()

DIVIDER = "=" * 64
THIN = "-" * 64

# Single-file transcript model: every chat is ONE .txt where resets/saves
# append "# VERSION N" sections. After 3 versions the AI can consolidate the
# file into a "# CONSOLIDATED" doc (summary + full conversation).
VERSION_MARK = "# VERSION"
CONSOLIDATED_MARK = "# CONSOLIDATED"
CONSOLIDATE_TRIGGER = 3


def _resolve_transcript(file_name: str) -> Path:
    """Where a logged transcript lives: agent-text-records first (the current
    home of every .txt), falling back to the chatlog root for stragglers."""
    if not file_name:
        return Path()
    candidate = RECORDS_DIR / file_name
    if candidate.exists():
        return candidate
    return CHATS_DIR / file_name


# ==========================================================================
# LOW-LEVEL HELPERS
# ==========================================================================

def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _new_id(prefix: str = "chr") -> str:
    """Random id like 'chr-1a2b3c4d5e6f'."""
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _stable_id(file_name: str) -> str:
    """Deterministic id for imported files so re-importing never duplicates."""
    return f"chr-{hashlib.sha1(file_name.encode('utf-8')).hexdigest()[:12]}"


def _slugify(value) -> str:
    """Filesystem-safe name from the chat title ('My Chat! 1' -> 'my-chat-1')."""
    s = re.sub(r"[^a-z0-9-]+", "-", str(value or "").lower().strip()).strip("-")
    return s[:60] or "chat"


def _load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _save_json(path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def _versioning_disabled() -> bool:
    """Read the 'disableVersioning' toggle from the app settings file."""
    try:
        settings = json.loads(APP_SETTINGS_FILE.read_text(encoding="utf-8"))
        return bool(settings.get("disableVersioning"))
    except (OSError, json.JSONDecodeError):
        return False


def _header_enabled() -> bool:
    """Read the 'metadataHeader' toggle from the app settings file.

    When on, finalized transcripts get the CHAT_ID:/TITLE:/... block from
    app.chat_store.logger prepended. Off by default so existing .txt files
    never change unless explicitly asked for.
    """
    try:
        settings = json.loads(APP_SETTINGS_FILE.read_text(encoding="utf-8"))
        return bool(settings.get("metadataHeader"))
    except (OSError, json.JSONDecodeError):
        return False


# ==========================================================================
# TRANSCRIPTS
# ==========================================================================

def _count_interactions(messages: list) -> int:
    """Number of user->assistant turn pairs (mirrors frontend chat-formatter)."""
    pairs = 0
    for i in range(1, len(messages)):
        if (
            messages[i].get("role") == "assistant"
            and messages[i - 1].get("role") == "user"
        ):
            pairs += 1
    if messages and messages[-1].get("role") == "user":
        pairs += 1
    return pairs


def _fmt_date(value) -> str:
    """ISO timestamp -> 'Sep 04, 2026, 02:35 PM' (or now on parse failure)."""
    try:
        iso = str(value or "").replace("Z", "+00:00")
        return datetime.fromisoformat(iso).strftime("%b %d, %Y, %I:%M %p")
    except (ValueError, TypeError):
        return datetime.now().strftime("%b %d, %Y, %I:%M %p")


def build_transcript(session: dict) -> str:
    """Render a session dict into the .txt transcript body."""
    messages = session.get("messages", []) or []
    lines = [
        DIVIDER,
        f"Session: {session.get('title') or 'Untitled chat'}",
        f"Agent:   {session.get('agentName') or session.get('agentId') or 'default'}",
        f"Model:   {session.get('model') or '(server default)'}",
        f"Date:    {_fmt_date(session.get('endedAt') or session.get('updatedAt') or session.get('startedAt'))}",
        f"Interactions between LLM and user: {_count_interactions(messages)}",
        DIVIDER,
        "",
    ]
    for message in messages:
        speaker = message.get("author") or ("You" if message.get("role") == "user" else "AI")
        lines.append(f"[{speaker}]  {_fmt_date(message.get('timestamp'))}")
        lines.append(THIN)
        lines.append((message.get("content") or "") or "")
        lines.append("")
    return "\n".join(lines)


def _parse_transcript_messages(text) -> list:
    """Turn transcript text back into [{role, author, text}, ...] (best effort)."""
    messages = []
    current = None
    for line in str(text or "").splitlines():
        match = re.match(r"^\[([^\]]+)\]\s*(.*)$", line)
        if match:
            if current and current.get("text"):
                messages.append(current)
            current = {
                "role": "user" if match.group(1).strip() == "You" else "assistant",
                "author": match.group(1).strip(),
                "text": "",
            }
        elif current is not None:
            stripped = line.strip()
            if stripped and not stripped.startswith("-") and not stripped.startswith("="):
                current["text"] = (
                    f"{current.get('text')}\n{stripped}" if current.get("text") else stripped
                )
    if current and current.get("text"):
        messages.append(current)
    return messages


def parse_sections(text) -> list:
    """Split a single-file transcript into its ordered sections.

    Each entry is {kind: 'version'|'consolidated', version, summary, content}:
      - version sections come from '# VERSION N' markers,
      - the consolidated section from '# CONSOLIDATED' (its leading
        '## Summary' block is captured in `summary`, the rest in `content`).
    Unrecognized text parses as a single version-1 section.
    """
    sections: list = []
    current: dict | None = None

    def flush():
        nonlocal current
        if current is not None:
            sections.append(current)
            current = None

    for raw in str(text or "").splitlines():
        line = raw.rstrip()
        if line.startswith(CONSOLIDATED_MARK):
            flush()
            current = {"kind": "consolidated", "version": "C", "summary": "", "content": [], "_area": "summary"}
        elif line.startswith(VERSION_MARK):
            flush()
            match = re.match(rf"^{re.escape(VERSION_MARK)}\s*([0-9]+)", line)
            current = {
                "kind": "version",
                "version": match.group(1) if match else str(len(sections) + 1),
                "summary": "",
                "content": [],
                "_area": "body",
            }
        elif current is not None:
            if line.startswith("## Full Conversation"):
                current["_area"] = "body"
            elif line.startswith("## Summary"):
                current["_area"] = "summary"
            elif current["_area"] == "summary":
                current["summary"] = (current["summary"] + "\n" + line).strip()
            else:
                current["content"].append(line)

    flush()
    for section in sections:
        section["content"] = "\n".join(section.get("content", [])).strip()
        section.pop("_area", None)
    return sections if sections else [{"kind": "version", "version": "1", "summary": "", "content": str(text or "").strip()}]


def _append_block(path: Path, block: str) -> None:
    """Append one text block onto a transcript file, creating it when missing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = path.read_text(encoding="utf-8", errors="replace").rstrip()
        path.write_text(existing + "\n\n" + block + "\n", encoding="utf-8")
    else:
        path.write_text(block + "\n", encoding="utf-8")


def parse_transcript_header(text: str) -> dict:
    """Pull the 'Session:/Agent:/...' header values out of a transcript.

    Also understands the newer CAPS: metadata block written by
    app.chat_store.logger (CHAT_ID:/TITLE:/AGENT:/MODEL:/MESSAGES://...),
    so transcripts with the optional header still import cleanly.
    """
    lines = str(text or "").splitlines()
    values: dict = {}

    def grab(key: str, field: str):
        for line in lines:
            if line.startswith(key):
                values[field] = line[len(key):].strip()
                return

    grab("Session:", "title")
    grab("TITLE:", "title")
    grab("Agent:", "agent_name")
    grab("AGENT:", "agent_name")
    grab("Model:", "model")
    grab("MODEL:", "model")
    grab("MESSAGES:", "messageCount")
    grab("STARTED:", "startedAt")
    grab("ENDED:", "endedAt")
    grab("TAGS:", "tags")
    grab("Interactions between LLM and user:", "interactions")
    values.pop("interactions", None)  # read separately below
    for line in lines:
        if line.startswith("Interactions between LLM and user:"):
            try:
                values["interactionCount"] = int(line.split(":")[-1].strip())
            except ValueError:
                pass
            break
    if values.get("messageCount"):
        try:
            values["messageCount"] = int(values["messageCount"])
        except (ValueError, TypeError):
            pass
    return values


# ==========================================================================
# ACTIVE SESSIONS  (one in-progress chat PER AGENT)
# ==========================================================================

def _load_active_sessions() -> dict:
    """Every in-progress session keyed by agent id.

    Legacy support: the file used to hold ONE session object (a dict with
    'id'/'messages'); that is auto-wrapped into {agentId: session} so an
    existing .active-chat.json keeps working and is re-saved as a map on the
    next write."""
    data = _load_json(ACTIVE_SESSION_FILE, {})
    if isinstance(data, dict) and "messages" in data:
        agent = data.get("agentId") or ""
        return {agent: data} if agent else {}
    if not isinstance(data, dict):
        return {}
    return {cid: sess for cid, sess in data.items() if isinstance(sess, dict) and sess.get("id")}


def _save_active_sessions(sessions: dict) -> None:
    """Write the agent-keyed session map back to .active-chat.json."""
    _save_json(ACTIVE_SESSION_FILE, sessions)


def _session_for(agent_id: str) -> dict | None:
    """The in-progress session for one agent (None when none exists).

    Back-compat: a call with an empty agent id resolves the session only when
    exactly one exists anywhere (old single-session clients)."""
    sessions = _load_active_sessions()
    if agent_id:
        return sessions.get(agent_id)
    if len(sessions) == 1:
        return next(iter(sessions.values()))
    return None


def current_session(agent_id: str = "") -> dict | None:
    """The in-progress session for one agent (None when none exists)."""
    with _lock:
        return _session_for(agent_id)


def active_sessions() -> list:
    """Every in-progress session across all agents, newest activity first."""
    with _lock:
        sessions = list(_load_active_sessions().values())
        sessions.sort(
            key=lambda s: s.get("updatedAt") or s.get("startedAt") or "",
            reverse=True,
        )
        return sessions


def ensure_session(agent, session_id: str = "", title: str = "", new_chat: bool = False, rag: bool | None = None) -> dict:
    """Return this agent's active session, finalizing any previous one when a
    new chat starts. Each agent keeps its OWN in-progress session, so starting
    a chat for agent B never touches agent A's live session.

    `rag` controls whether this chat is committed to the RAG store when it is
    saved. None -> the stored commitOnSave default applies.
    """
    with _lock:
        agent_id = agent.profile.id or ""
        active = _session_for(agent_id)
        wants_new = (
            new_chat
            or active is None
            or (session_id and active.get("id") != session_id)
        )
        if wants_new:
            if active is not None and active.get("status") == "finalized":
                # Re-save only when the chat grew after its last version.
                if len(active.get("messages", [])) > (active.get("finalizedCount") or 0):
                    _finalize_locked(agent_id)
            elif active is not None:
                _finalize_locked(agent_id)
            return _create_locked(agent, title, rag=rag)
        return active


def _create_locked(agent, title: str = "", rag: bool | None = None) -> dict:
    now = _now_iso()
    if rag is None:
        rag = paths.rag_config()["commitOnSave"]
    session = {
        "id": _new_id("chr"),
        "title": (str(title or "").strip()[:80]) or "New chat",
        "agentId": agent.profile.id or "",
        "agentName": agent.profile.name or "",
        "model": agent.model or "",
        "startedAt": now,
        "updatedAt": now,
        "rag": bool(rag),
        "messages": [],
    }
    sessions = _load_active_sessions()
    sessions[session["agentId"]] = session
    _save_active_sessions(sessions)
    print(f"[CHATS] started session '{session['id']}' for '{session['agentId']}' (rag={session['rag']})")
    return session


def append_turn(agent_id: str, user_text: str, reply_text: str) -> dict | None:
    """Append the user message + assistant reply to that agent's active session."""
    with _lock:
        session = _session_for(agent_id)
        if not session:
            return None
        key = session.get("agentId") or next(iter(_load_active_sessions()), "")
        now = _now_iso()
        session.setdefault("messages", []).append(
            {"role": "user", "author": "You", "content": str(user_text), "timestamp": now}
        )
        session.setdefault("messages", []).append(
            {
                "role": "assistant",
                "author": session.get("agentName") or "AI",
                "content": str(reply_text),
                "timestamp": now,
            }
        )
        if session.get("title") in ("", "New chat"):
            session["title"] = _first_words(user_text, 50)
        session["updatedAt"] = now
        sessions = _load_active_sessions()
        sessions[key] = session
        _save_active_sessions(sessions)
        return session


def _first_words(text: str, max_chars: int) -> str:
    text = str(text or "").strip()
    if not text:
        return "New chat"
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "..."


# ==========================================================================
# FINALIZE (end of a chat)
# ==========================================================================

def finalize_session(agent_id: str = "", title: str | None = None, rag: bool | None = None) -> dict | None:
    """Finalize THAT agent's active chat: write its .txt (versioned) + log one
    header row. A call without an agent id resolves the lone session when
    exactly one exists (old single-session clients).

    `rag: True` commits the written transcript into the RAG store (save to
    memory). None -> the session's stored rag flag (set at chat creation from
    the per-chat toggle / commitOnSave default) applies.
    """
    with _lock:
        return _finalize_locked(agent_id=agent_id, title=title, rag=rag)


def _finalize_locked(agent_id: str = "", title: str | None = None, rag: bool | None = None) -> dict | None:
    session = _session_for(agent_id)
    if not session:
        return None

    if title and str(title).strip():
        session["title"] = str(title).strip()[:80]
    elif session.get("title") in ("", "New chat"):
        session["title"] = _first_words(
            ((session.get("messages") or [{}])[0].get("content") if session.get("messages") else ""),
            50,
        )

    session["endedAt"] = _now_iso()
    session["status"] = "finalized"
    session["finalizedCount"] = len(session.get("messages", []))
    content = build_transcript(session)

    base = _slugify(session["title"])
    target = _chat_file(base)
    meta = {"id": session.get("id") or _stable_id(target.name), "title": session.get("title")}

    if _versioning_disabled():
        block = f"{VERSION_MARK} 1\n\n{content}".strip()
        if not target.exists():
            block = chat_logger.add_header_to_transcript(block, chat_logger.record_from_store_row({**meta, "version": "1"}))
        target.write_text(block + "\n", encoding="utf-8")
        version = "1"
    else:
        current = read_chat_file_locked(target)
        version = "1"
        if current and current.get("sections"):
            numbers = [
                s.get("version") for s in current["sections"]
                if s.get("kind") == "version"
            ]
            version = str(max((_version_number(v) for v in numbers), default=0) + 1)
        block = f"{VERSION_MARK} {version}\n\n{content}".strip()
        if not target.exists():
            block = chat_logger.add_header_to_transcript(block, chat_logger.record_from_store_row({**meta, "version": version}))
        _append_block(target, block)

    row = {
        "id": session.get("id") or _stable_id(target.name),
        "title": session.get("title"),
        "fileName": target.name,
        "agentId": session.get("agentId", ""),
        "agentName": session.get("agentName", ""),
        "model": session.get("model", ""),
        "version": version,
        "messageCount": len(session.get("messages", [])),
        "interactionCount": _count_interactions(session.get("messages", [])),
        "startedAt": session.get("startedAt"),
        "endedAt": session.get("endedAt"),
        "status": "done",
    }

    # One row per chat in chatRecord.jsonl: update() appends when the chat id
    # is unknown and REPLACES the most recent row for a known id, so the
    # current version is always the row on disk. A failure must never block
    # the chat save.
    try:
        _metadata_logger.update(row["id"], chat_logger.record_from_store_row(row))
    except OSError:
        pass

    # Commit to the RAG store when the chat is marked for memory ("save to
    # memory" toggle, or the commitOnSave default). Never blocks the save.
    commit = rag if rag is not None else bool(session.get("rag", False))
    if commit:
        try:
            from app.rag_commit import commit_transcript

            commit_transcript(target)
        except Exception as e:
            print(f"[CHATS] RAG commit failed (chat still saved): {e}")

    # Keep the live session so continued messages can become the next version.
    sessions = _load_active_sessions()
    sessions[session.get("agentId") or ""] = session
    _save_active_sessions(sessions)
    print(f"[CHATS] finalized '{session['title']}' -> {target.name} (v{version})")
    if _version_number(version) >= CONSOLIDATE_TRIGGER:
        row["consolidation_offered"] = True
    return row


def read_chat_file(base_or_path) -> dict | None:
    """Public read of a single-file transcript: returns the parsed representation
    {file, base, sections:[...]} with sections ordered newest-first."""
    with _lock:
        return read_chat_file_locked(base_or_path)


def read_chat_file_locked(base_or_path) -> dict | None:
    """Parse the single-file transcript for `base`/`fileName`/a record id (or
    Path directly). Sections are returned newest-first both for the transcript
    builder and the API."""
    path = _chat_file(base_or_path) if isinstance(base_or_path, Path) else _resolve_chat_target(base_or_path)
    if path is None:
        return None
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    sections = parse_sections(text)
    sections.reverse()
    return {"file": path, "base": _base_file_name(path.name).replace(".txt", ""), "sections": sections}


def write_consolidated(chat_id: str, summary: str, combined: str) -> Path | None:
    """Persist a consolidated section into the chat's single transcript file.
    The FULL conversation is kept (summary + full text); consolidation never
    replaces or destroys earlier versions. Returns the target path."""
    with _lock:
        current = read_chat_file_locked(chat_id)
        if current is None:
            return None
        block = (
            f"{CONSOLIDATED_MARK}\n\n## Summary\n\n{_sanitize_embedded_markers(summary).strip()}\n\n"
            f"## Full Conversation\n\n{_sanitize_embedded_markers(combined).strip()}"
        ).strip()
        _append_block(current["file"], block)
        return current["file"]


def _sanitize_embedded_markers(text: str) -> str:
    """Neutralize '# VERSION N' / '# CONSOLIDATED' lines that appear INSIDE a
    consolidated body's verbatim conversation, so parse_sections() keeps
    treating top-level file sections as the only section boundaries."""
    lines = []
    for line in str(text or "").splitlines():
        if re.match(r"^#\s*(VERSION|CONSOLIDATED)\b", line):
            lines.append(line[1:].strip())
        else:
            lines.append(line)
    return "\n".join(lines)


def mark_consolidated(chat_id: str, file_name: str) -> None:
    """Point a chat's log record at its consolidated section (version 'C').

    The transcript itself already holds the '# CONSOLIDATED' section; this
    only updates the metadata row so the UI shows "(consolidated)".
    """
    with _lock:
        record = _metadata_logger.get(chat_id)
        if not record:
            return
        record["version"] = "C"
        record["fileName"] = file_name
        try:
            _metadata_logger.update(
                chat_id,
                chat_logger.record_from_store_row(
                    {**record, "status": "completed", "version": "C"}
                ),
            )
        except OSError:
            pass


def discard_session(agent_id: str = "") -> dict | None:
    """Abandon THAT agent's in-progress chat WITHOUT writing a transcript.
    A call without an agent id resolves the lone session when exactly one
    exists. Returns None when there is nothing to discard."""
    with _lock:
        sessions = _load_active_sessions()
        key = agent_id
        if not key:
            if len(sessions) == 1:
                key = next(iter(sessions))
            else:
                return None
        session = sessions.pop(key, None)
        if not session:
            return None
        _save_active_sessions(sessions)
        return session


def _chat_file(base: str | Path) -> Path:
    """The ONE transcript file a chat ever gets: <slug>.txt (never versioned
    into separate files - versions live inside as '# VERSION N' sections).
    Accepts a full path, a file name (with .txt) or a base slug."""
    if isinstance(base, Path):
        return base
    base = str(base)
    if base.lower().endswith(".txt"):
        return RECORDS_DIR / base
    return RECORDS_DIR / f"{base}.txt"


def _resolve_chat_target(chat_id) -> Path | None:
    """Map a chat id / transcript file name / base slug to the ONE transcript
    file on disk (None when missing). Used so API callers (and consolidation)
    can find a chat by its record id without knowing the slug."""
    if isinstance(chat_id, Path):
        return chat_id if chat_id.exists() else None
    direct = _chat_file(chat_id)
    if direct.exists():
        return direct
    record = _metadata_logger.get(chat_id)
    if record and record.get("fileName"):
        path = _resolve_transcript(record.get("fileName", ""))
        if path.exists():
            return path
    return None


def _base_file_name(file_name: str) -> str:
    """'my-chat-2.txt' -> 'my-chat.txt'; 'my-chat.txt' stays as-is. Used to
    normalize legacy per-version names onto the single-file model."""
    match = re.search(r"-(\d+(?:\.\d+)*)\.txt$", str(file_name or ""))
    return file_name if not match else file_name[: match.start()] + ".txt"


def _version_number(value) -> int:
    """'1'/'2'/'3' -> int, 'C' -> a large number (consolidated wins)."""
    if str(value).upper() == "C":
        return 1000
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


# ==========================================================================
# CHAT RECORDS (data/chatlog/chatRecord.jsonl) - the single metadata store
# ==========================================================================

def _transcript_exists(file_name: str) -> bool:
    """True when the transcript .txt a record points at is still on disk."""
    return bool(file_name) and _resolve_transcript(file_name).exists()


def _record_to_row(record: dict) -> dict:
    """Rebuild the frontend-facing row shape from a chatRecord.jsonl record."""
    return {
        "id": record.get("id"),
        "title": record.get("title"),
        "fileName": record.get("fileName", ""),
        "agentId": record.get("agentId", ""),
        "agentName": record.get("agentName") or record.get("agent", ""),
        "model": record.get("model", ""),
        "version": record.get("version", ""),
        "messageCount": record.get("messageCount", 0),
        "interactionCount": record.get("interactionCount", 0),
        "startedAt": record.get("startedAt", ""),
        "endedAt": record.get("endedAt", ""),
        "status": "done",
    }


def latest_per_chat(records: list) -> list:
    """Collapse per-version records down to the LATEST record per chat id.

    chatRecord.jsonl keeps one line per version; the dropdown only shows one
    entry per chat. The file is append-only, so walking in reverse and keeping
    the first sighting of each id yields the newest version of every chat.
    """
    latest = {}
    for record in reversed(records):
        chat_id = record.get("id")
        if chat_id is not None and chat_id not in latest:
            latest[chat_id] = record
    return list(latest.values())


def prune_deleted() -> int:
    """Remove chatRecord.jsonl records whose transcript .txt is gone.

    Runs lazily on every list_log() so a chat whose transcript is deleted
    manually disappears from the drop-down immediately - no server restart
    needed. Records without a fileName are left alone. Returns count removed.
    """
    with _lock:
        try:
            return _metadata_logger.prune(
                lambda rec: not rec.get("fileName") or _transcript_exists(rec.get("fileName"))
            )
        except OSError:
            return 0


def _active_row(active: dict) -> dict:
    """The dropdown row shape for an in-progress session."""
    return {
        "id": active.get("id"),
        "title": active.get("title"),
        "fileName": "",
        "agentId": active.get("agentId", ""),
        "agentName": active.get("agentName", ""),
        "model": active.get("model", ""),
        "version": "",
        "messageCount": len(active.get("messages", [])),
        "interactionCount": _count_interactions(active.get("messages", [])),
        "startedAt": active.get("startedAt"),
        "endedAt": "",
        "status": "active",
    }


def list_log(include_active=True) -> list:
    """The log used by the frontend dropdown/sidebar, newest end first.

    Stale records whose transcript .txt no longer exists are pruned first, so
    chats deleted on disk disappear here and from chatRecord.jsonl on the next
    refresh rather than lingering until a restart. Returns one row per chat,
    pointing at its LATEST version. Every agent's in-progress session (status
    'active') is appended.
    """
    prune_deleted()
    rows = [_record_to_row(rec) for rec in latest_per_chat(_metadata_logger.list_all())]
    if include_active:
        rows.extend(_active_row(active) for active in active_sessions() if active.get("status") != "finalized")
    rows.sort(
        key=lambda r: r.get("endedAt") or r.get("savedAt") or r.get("startedAt") or "",
        reverse=True,
    )
    return rows


def get_chat(chat_id: str) -> dict | None:
    """One chat (its record + the transcript/messages) to reopen it.

    A transcript file may carry several '# VERSION N'/'# CONSOLIDATED'
    sections; only the LATEST section is returned (that is what the UI
    reopens), so past versions stay archived in the file without cluttering
    the current conversation.
    """
    record = _metadata_logger.get(chat_id)
    if record:
        path = _resolve_transcript(record.get("fileName", ""))
        content = ""
        if path.exists():
            current = read_chat_file_locked(path)
            sections = (current or {}).get("sections") or []
            if sections:
                latest = sections[0]
                content = latest.get("content") or ""
                if latest["kind"] == "consolidated" and latest.get("summary"):
                    content = f"## Summary\n\n{latest['summary']}\n\n{content}"
            else:
                content = path.read_text(encoding="utf-8", errors="replace")
        row = _record_to_row(record)
        return {**row, "content": content, "messages": _parse_transcript_messages(content)}
    for sess in _load_active_sessions().values():
        if sess.get("id") == chat_id:
            return {
                **{**_active_row(sess), "status": "active"},
                "content": build_transcript(sess),
                "messages": sess.get("messages", []),
            }
    return None


def _fileName_version(file_name: str) -> str:
    """'my-chat-2.txt' -> '2'; 'my-chat.txt' -> '1'."""
    match = re.search(r"-(\d+(?:\.\d+)*)\.txt$", file_name)
    return match.group(1) if match else "1"


def set_chat_version(chat_id: str, version: str) -> dict | None:
    """Append a chat's own transcript as a new '# VERSION N' section.

    Kept for scripts/version_chats.py compatibility: this now works within
    the single-file model by reading the chat's current transcript (first
    section, i.e. the latest version) and appending it again under the given
    version marker, then pointing the chat's record at that section.
    """
    with _lock:
        record = _metadata_logger.get(chat_id)
        if not record:
            return None
        current = read_chat_file_locked(record.get("fileName", ""))
        if current is None or not current.get("sections"):
            return None
        payload = current["sections"][0].get("content") or ""
        block = f"{VERSION_MARK} {version}\n\n{payload}".strip()
        _append_block(current["file"], block)
        record["version"] = str(version)
        record["fileName"] = current["file"].name
        try:
            _metadata_logger.update(record)
        except OSError:
            pass
        return {**record}


def _rebuild_header(file_name: str) -> dict:
    """Best-effort header row for an existing single-file transcript (used by
    import_once). Version + counts come from the LATEST '# VERSION N' section."""
    path = _resolve_transcript(file_name)
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        mtime = datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")
    except OSError:
        return None

    header = parse_transcript_header(text)
    title = header.get("title") or re.sub(r"-(\d+(\.\d+)*)?$", "", path.stem).replace("-", " ").title()
    current = read_chat_file_locked(path)
    sections = (current or {}).get("sections") or []
    latest = sections[0] if sections else {}
    content = latest.get("content") or (text if not sections else "")
    messages = _parse_transcript_messages(content)
    return {
        "id": _stable_id(file_name),
        "title": title,
        "fileName": file_name,
        "agentId": "",
        "agentName": header.get("agent_name") or "",
        "model": "" if header.get("model") in (None, "(server default)") else header.get("model", ""),
        "version": latest.get("version") or _fileName_version(file_name),
        "messageCount": len(messages),
        "interactionCount": header.get("interactionCount", _count_interactions(messages)),
        "startedAt": "",
        "endedAt": mtime,
        "status": "done",
    }


def _migrate_legacy_layout() -> None:
    """Move the pre-rename layout (data/chats/* + data/discussions.json)
    into data/chatlog/, and every .txt into agent-text-records/. Idempotent:
    each step only runs when the target is missing and the source still
    exists. Called from import_once() at startup.
    """
    # 1. Folder: data/chats -> data/chatlog (all .txt + hidden state files).
    if _LEGACY_CHATS_DIR.is_dir() and (not CHATS_DIR.exists() or not list(CHATS_DIR.glob("*.txt"))):
        CHATS_DIR.mkdir(parents=True, exist_ok=True)
        for legacy in list(_LEGACY_CHATS_DIR.iterdir()):
            target = CHATS_DIR / legacy.name
            if not target.exists():
                shutil.move(str(legacy), str(target))
        if not list(_LEGACY_CHATS_DIR.iterdir()):
            _LEGACY_CHATS_DIR.rmdir()

    # 2. Log: data/discussions.json -> data/chatlog/log-chats.json (the old
    #    store; import_once() absorbs it into chatRecord.jsonl afterwards).
    if not _OLD_LOGCHATS_FILE.exists() and _LEGACY_LOG_FILE.exists():
        CHATS_DIR.mkdir(parents=True, exist_ok=True)
        shutil.move(str(_LEGACY_LOG_FILE), str(_OLD_LOGCHATS_FILE))

    # 3. Transcripts: data/chatlog/*.txt -> data/chatlog/agent-text-records/.
    #    (The log keeps the bare file name, so moving is safe.)
    RECORDS_DIR.mkdir(parents=True, exist_ok=True)
    for legacy in list(CHATS_DIR.glob("*.txt")) + list(RECORDS_DIR.glob("*.txt")):
        target = RECORDS_DIR / legacy.name
        if target.exists():
            continue
        shutil.move(str(legacy), str(target))


def _migrate_legacy_version_files() -> int:
    """Fold legacy per-version '<slug>-N.txt' files into one '<slug>.txt'.

    The old model wrote a NEW .txt per version (my-chat-2.txt, -3.txt, ...);
    the single-file model keeps everything in my-chat.txt as '# VERSION N'
    sections. This folds any surviving -N.txt files into the base file as
    sections (version label taken from the suffix), then deletes them.
    Returns how many files were folded. Idempotent.
    """
    folded = 0
    if not RECORDS_DIR.exists():
        return 0
    numbered = [
        path for path in RECORDS_DIR.glob("*.txt")
        if re.search(r"-(\d+(?:\.\d+)*)\.txt$", path.name)
    ]
    for path in sorted(numbered, key=lambda p: p.name):
        match = re.search(r"-(\d+(?:\.\d+)*)\.txt$", path.name)
        if not match:
            continue
        version = match.group(1)
        base_name = path.name[: path.name.rfind("-" + version + ".txt")] + ".txt"
        try:
            content = path.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            continue
        if not content.startswith(VERSION_MARK) and not content.startswith(CONSOLIDATED_MARK):
            content = f"{VERSION_MARK} {version}\n\n{content}".strip()
        _append_block(RECORDS_DIR / base_name, content)
        try:
            path.unlink()
            folded += 1
        except OSError:
            pass
    if folded:
        print(f"[CHATS] folded {folded} legacy version file(s) into single-file transcripts")
    return folded


def import_once() -> int:
    """One-time boot sync that builds the single store, chatRecord.jsonl.

    - Migrates legacy per-version '<slug>-N.txt' transcripts into single
      '<slug>.txt' files carrying '# VERSION N' sections.
    - Migrates the pre-chatRecord layout into chatRecord.jsonl:
        * data/discussions.json  (legacy message arrays) -> .txt transcripts,
        * data/chatlog/log-chats.json (old one-row-per-chat store),
        * data/chatlog/chat_log.jsonl (old per-version records).
    - Scans data/chatlog/agent-text-records/*.txt and records any file not
      yet logged.
    - Drops records whose transcript disappeared since the last boot.
    - Deletes the old store files once their content is in chatRecord.jsonl.

    Idempotent: the merge key is (id, fileName), so a restart never
    duplicates. Runs once at server startup.
    """
    with _lock:
        _migrate_legacy_layout()
        _migrate_legacy_version_files()
        migrated = 0
        added = 0

        # --- 1. Read the old stores BEFORE they are deleted ---
        old_rows = _load_json(_OLD_LOGCHATS_FILE, []) if _OLD_LOGCHATS_FILE.exists() else []
        old_records = chat_logger.ChatLogger(log_file=_OLD_JSONL_FILE).list_all()
        for record in old_records:
            record["fileName"] = _base_file_name(record.get("fileName", ""))

        # --- 2. Legacy discussion rows (no fileName, whole 'messages' arrays)
        #         become versioned .txt transcripts, exactly as before. ---
        new_rows = []
        for entry in old_rows:
            if entry.get("fileName"):
                new_rows.append(entry)
                continue
            legacy_id = entry.get("id") or _new_id("chr")
            if not entry.get("messages"):
                continue
            session = {
                "id": legacy_id,
                "title": entry.get("title") or "Legacy import",
                "agentId": entry.get("agentId", ""),
                "agentName": entry.get("agentName", ""),
                "model": entry.get("model", ""),
                "startedAt": entry.get("createdAt") or entry.get("updatedAt") or _now_iso(),
                "updatedAt": entry.get("updatedAt") or _now_iso(),
                "endedAt": entry.get("updatedAt") or _now_iso(),
                "messages": [
                    {
                        "role": (m.get("role") or "user"),  # assistant->assistant
                        "author": m.get("author") or ("You" if m.get("role") == "user" else "AI"),
                        "content": (m.get("text") or m.get("content") or ""),
                        "timestamp": m.get("timestamp", _now_iso()),
                    }
                    for m in (entry.get("messages") or [])
                    if (m.get("text") or m.get("content") or "")
                ],
            }
            base = _slugify(session["title"])
            target = _chat_file(base)
            block = f"{VERSION_MARK} 1\n\n{build_transcript(session)}".strip()
            if not target.exists():
                block = chat_logger.add_header_to_transcript(block, chat_logger.record_from_store_row(
                    {"id": legacy_id, "title": session["title"], "version": "1"}
                ))
            _append_block(target, block)
            version = "1"
            new_rows.append(
                {
                    "id": legacy_id,
                    "title": session["title"],
                    "fileName": target.name,
                    "agentId": session["agentId"],
                    "agentName": session["agentName"],
                    "model": session["model"],
                    "version": str(version),
                    "messageCount": len(session["messages"]),
                    "interactionCount": _count_interactions(session["messages"]),
                    "startedAt": session["startedAt"],
                    "endedAt": session["endedAt"],
                    "status": "done",
                }
            )
            migrated += 1

        # --- 3. Merge chatRecord.jsonl + both old files by (id, fileName).
        #         File names are normalized onto the single-file model so old
        #         '<base>-N.txt' record rows still point at the folded file.
        #         chatRecord.jsonl is authoritative (kept as-is); old stores
        #         fill gaps, the LAST old record per (id, fileName) winning. ---
        merged = {}
        for rec in _metadata_logger.list_all():
            rec["fileName"] = _base_file_name(rec.get("fileName", ""))
            merged[(rec.get("id"), rec["fileName"])] = rec

        legacy = {}
        for record in old_records:
            record["fileName"] = _base_file_name(record.get("fileName", ""))
            legacy[(record.get("id"), record["fileName"])] = record
        for row in new_rows:
            row["fileName"] = _base_file_name(row.get("fileName", ""))
            legacy[(row.get("id"), row["fileName"])] = chat_logger.record_from_store_row(row)
        for key, record in legacy.items():
            if key not in merged:
                merged[key] = record
                migrated += 1

        # --- 4. Import on-disk .txt transcripts not logged yet ---
        known = set(merged)
        known_names = {k[1] for k in known}
        # Scan agent-text-records/ first, then anything left in the chatlog root.
        for scan_dir in (RECORDS_DIR, CHATS_DIR):
            if not scan_dir.exists():
                continue
            for path in sorted(scan_dir.glob("*.txt")):
                name = path.name
                if name in known_names:
                    continue
                row = _rebuild_header(name)
                if row:
                    key = (_stable_id(name), name)
                    merged[key] = chat_logger.record_from_store_row(row)
                    known_names.add(name)
                    added += 1

        # --- 5. Collapse to ONE row per chat (single-file model), drop rows
        #         whose transcript disappeared, and rewrite the index once. ---
        records = list(merged.values())
        for record in records:
            record["fileName"] = _base_file_name(record.get("fileName", ""))
        write_ok = True
        try:
            _metadata_logger.replace_all(records)
            _metadata_logger.prune(
                lambda rec: not rec.get("fileName") or _transcript_exists(rec.get("fileName"))
            )
        except OSError:
            write_ok = False

        # --- 6. The old stores are absorbed - delete them only on success ---
        if write_ok:
            for legacy in (_OLD_LOGCHATS_FILE, _OLD_JSONL_FILE):
                if legacy.exists():
                    try:
                        legacy.unlink()
                    except OSError:
                        pass

        total = migrated + added
        if total:
            print(f"[CHATS] migrated {migrated} legacy record(s) and imported {added} transcript(s)")
        return total


def save_discussion(discussion: dict) -> bool:
    """Legacy /api/discussions POST: upsert one record into chatRecord.jsonl.

    The server stamps updatedAt. The payload is merged into the chat's most
    recent record (or appended when the id is new). Returns True when saved.
    """
    discussion_id = discussion.get("id")
    if not discussion_id:
        return False
    discussion["updatedAt"] = _now_iso()
    try:
        _metadata_logger.update(discussion_id, discussion)
    except OSError:
        return False
    return True


def delete_discussion(discussion_id: str) -> bool:
    """Legacy /api/discussions DELETE: remove EVERY record for a chat id.

    Returns True when at least one record was removed.
    """
    try:
        return _metadata_logger.remove(discussion_id) > 0
    except OSError:
        return False


def delete_chat(chat_id: str) -> dict:
    """Erase a chat completely: its log records, EVERY versioned .txt transcript,
    and the live active session when it is the one being deleted.

    The records alone are not enough - import_once() rescans the transcript
    folder on boot, so the .txt files must be unlinked too or the chat would
    come back. Returns a summary dict, or an all-zero dict when the id is
    unknown (callers decide whether that is an error).
    """
    with _lock:
        records = _metadata_logger.list_all()
        mine = [record for record in records if record.get("id") == chat_id]

        files_removed = []
        for record in mine:
            file_name = record.get("fileName", "")
            if not file_name:
                continue
            path = _resolve_transcript(file_name)
            try:
                if path.exists():
                    path.unlink()
                    files_removed.append(file_name)
            except OSError:
                continue

        records_removed = _metadata_logger.remove(chat_id)

        was_active = False
        sessions = _load_active_sessions()
        for key, sess in list(sessions.items()):
            if sess.get("id") == chat_id:
                sessions.pop(key, None)
                was_active = True
        if was_active:
            _save_active_sessions(sessions)

        if records_removed or files_removed or was_active:
            print(
                f"[CHATS] deleted '{chat_id}' "
                f"({len(files_removed)} file(s), {records_removed} record(s), active={was_active})"
            )
        return {
            "recordsRemoved": records_removed,
            "filesRemoved": files_removed,
            "wasActive": was_active,
        }


__all__ = [
    "current_session",
    "active_sessions",
    "ensure_session",
    "append_turn",
    "finalize_session",
    "list_log",
    "get_chat",
    "read_chat_file",
    "write_consolidated",
    "discard_session",
    "import_once",
    "set_chat_version",
    "mark_consolidated",
    "save_discussion",
    "delete_discussion",
    "delete_chat",
    "build_transcript",
    "CHATS_DIR",
    "RECORDS_DIR",
    "LOG_FILE",
]
