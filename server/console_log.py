"""server/console_log.py
=======================

A process-wide ring buffer that captures console output so the frontend can
render a clean terminal readout inside the chat window and on the pop-out
logs page (`dashboard/logs.html`).

It captures BOTH:

- the app's own `print()` calls (``[llm]`` / ``[paths]`` / ``[interface]`` /
  ``[wiring]`` / ``[custom-modules]`` / ``[Agent.act]`` / ``[SERVER]`` ...),
- and Python-logging output such as uvicorn's ``INFO:`` startup/access lines
  (uvicorn creates its StreamHandlers after this module is imported, so they
  pick up the tee'd ``sys.stderr`` automatically).

Install it at import time (self-installs when the module is loaded), i.e.:

    from server import console_log      # wires the tee + root-logger handler

Read the tail anytime:

    console_log.tail(limit=300)
"""

from __future__ import annotations

import logging
import re
import sys
from collections import deque

_LIMIT = 500
_BUFFER: deque[str] = deque(maxlen=_LIMIT)
_INSTALLED = False

# CSI (``ESC [ ...``) sequences - uvicorn's colored log lines. Stripped at
# capture time so the ring buffer stays plain text (the chat drawer and the
# logs page render text, not terminal escapes). Matches ``[32m``, ``[1m``,
# ``[36m``, ``[K``, ``[H``, ... (color/bold/erase/cursor motion).
_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def _append(text: str) -> None:
    for line in str(text).splitlines():
        if line:
            _BUFFER.append(_ANSI.sub("", line))


class _Tee:
    """A stdout/stderr replacement that mirrors writes to the ring buffer."""

    def __init__(self, original) -> None:
        self.original = original

    def write(self, text: str) -> int:
        _append(text)
        return self.original.write(str(text))

    def flush(self) -> None:
        try:
            self.original.flush()
        except Exception:
            pass

    def isatty(self) -> bool:
        try:
            return self.original.isatty()
        except Exception:
            return False

    def fileno(self) -> int:
        return self.original.fileno()

    def __getattr__(self, name):
        return getattr(self.original, name)


class _CaptureHandler(logging.Handler):
    """Records every message any propagating logger emits (INFO/access...)."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            _append(self.format(record))
        except Exception:
            pass


def install(limit: int = _LIMIT) -> None:
    """Tee stdout/stderr and attach a root-logger handler. Idempotent - a
    second import never double-wraps the streams."""
    global _BUFFER, _INSTALLED
    if _INSTALLED:
        return
    _BUFFER = deque(maxlen=max(10, int(limit)))
    sys.stdout = _Tee(sys.stdout)
    sys.stderr = _Tee(sys.stderr)
    handler = _CaptureHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logging.getLogger().addHandler(handler)
    _INSTALLED = True


def tail(limit: int | None = None) -> list[str]:
    """The most recent captured lines, newest last. `limit` trims the tail."""
    lines = list(_BUFFER)
    if limit is not None and limit > 0:
        lines = lines[-int(limit):]
    return lines


def captured() -> bool:
    """True once any line has been captured in this process."""
    return _INSTALLED and len(_BUFFER) > 0


# Wire immediately on import so uvicorn's startup lines land in the buffer.
install()