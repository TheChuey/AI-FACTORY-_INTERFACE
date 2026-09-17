"""server/tool_log.py
====================

A process-wide, append-only log of every tool call agents make.

Each event is a small structured dict written as one JSON line to
`data/toollog/tool_usage.jsonl` (path resolved through server/paths.py so it
follows the configured dataDir), AND kept in an in-memory deque so the
frontend can poll a live tail without re-reading the file on every request.

Event shape (superset of Agent.tool_events, with agent context):

    {
        "time":           "2026-09-16T14:22:31",   # ISO (seconds)
        "agentId":        "dev_assistant",
        "agentName":      "Dev Assistant",
        "model":          "qwen2.5:7b",
        "tool":           "read_file",
        "args":           {...},
        "result_preview": "...",      # on success / missing
        "error":          "...",      # only on error
        "status":         "success" | "error" | "missing",
        "origin":         "native tool_calls" | "TEXT reply",
    }

record() is deliberately fail-safe: a disk error must never break a tool call,
so every write is wrapped so exceptions are swallowed (matching the "chats
save even if the log fails" philosophy of chat_store).

Read the tail anytime:

    from server import tool_log
    tool_log.tail(limit=100)
"""

from __future__ import annotations

import json
import threading
from collections import deque
from datetime import datetime

from server import paths

_LIMIT = 1000  # in-memory tail (the JSONL file keeps the full history)
_BUFFER: deque[dict] = deque(maxlen=_LIMIT)
_LOCK = threading.Lock()
_SEEDED = False

# A single JSONL logger behind every append, so concurrent tool calls (and the
# seed-on-import read) never interleave writes.

_JSONL_FILE = paths.TOOL_LOG_FILE


def _iso_now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _read_tail(lines: int) -> list[dict]:
    """Best-effort read of the last `lines` JSONL records (newest last)."""
    events: list[dict] = []
    try:
        if not _JSONL_FILE.exists():
            return events
        with _JSONL_FILE.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return events
    return events[-lines:]


def _seed() -> None:
    """Warm the in-memory tail from the persisted log so a restarted server
    still shows recent tool activity in the live view immediately. Runs once
    at import (before any append), and only fills an empty buffer so events
    recorded fresh in this process are never duplicated."""
    global _SEEDED
    with _LOCK:
        if _SEEDED:
            return
        _SEEDED = True
        if _BUFFER:
            return
        for event in _read_tail(_LIMIT):
            _BUFFER.append(event)


def append(event: dict) -> None:
    """Record one structured tool event (thread-safe, fail-safe)."""
    if not isinstance(event, dict):
        return
    normalized = {
        "time": event.get("time") or _iso_now(),
        "agentId": event.get("agentId", ""),
        "agentName": event.get("agentName", ""),
        "model": event.get("model", ""),
        "tool": event.get("tool", ""),
        "args": event.get("args", {}) or {},
        "status": event.get("status", "success"),
    }
    if event.get("error"):
        normalized["error"] = str(event["error"])
    elif event.get("result_preview"):
        normalized["result_preview"] = str(event["result_preview"])[:200]
    if event.get("origin"):
        normalized["origin"] = event["origin"]

    with _LOCK:
        _BUFFER.append(normalized)
        try:
            _JSONL_FILE.parent.mkdir(parents=True, exist_ok=True)
            with _JSONL_FILE.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(normalized, ensure_ascii=False, default=str) + "\n")
        except Exception:
            pass  # a logging failure never blocks the tool call


def tail(limit: int | None = None, tool: str = "", agent: str = "", since: str = "") -> list[dict]:
    """The most recent captured events, newest first (the file seed means a
    restarted server can still return pre-restart history).

    Optional filters:
        tool  - event["tool"] must equal the value (case-insensitive)
        agent - event["agentId"] or event["agentName"] matches (case-insensitive)
        since - only events with time >= this ISO string (inclusive, lexicographic)
    """
    _seed()
    events = list(_BUFFER)
    if tool:
        needle = str(tool).strip().lower()
        events = [e for e in events if str(e.get("tool", "")).lower() == needle]
    if agent:
        needle = str(agent).strip().lower()
        events = [
            e for e in events
            if needle in str(e.get("agentId", "")).lower()
            or needle in str(e.get("agentName", "")).lower()
        ]
    if since:
        events = [e for e in events if str(e.get("time", "")) >= str(since)]
    events.reverse()
    if limit is not None and limit > 0:
        events = events[: int(limit)]
    return events


def captured() -> bool:
    """True once any event has been recorded in this process."""
    _seed()
    return len(_BUFFER) > 0


# Warm the tail from disk once at import so the live view can show pre-restart
# history without duplicating events recorded later in this process.
_seed()