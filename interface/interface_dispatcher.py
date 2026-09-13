"""interface/interface_dispatcher.py
===================================

Line-number change tracing and traced execution for Option B module calls.

Every traced call records WHERE it was triggered - the caller's file and line
- before running the actual function, so troubleshooting never depends on
memory:

    from interface.interface_dispatcher import InterfaceDispatcher

    InterfaceDispatcher().trace_and_execute(my_module.run_example, data)
    InterfaceDispatcher().execute_action("engine", "newfunction",
                                         "secondary_engine_action", 5)

Trace lines are logged through the `app_change_tracker` logger (a FileHandler
writes them to `data/interface_trace.log`) and also printed to stdout.
"""

from __future__ import annotations

import inspect
import logging
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
TRACE_LOG_FILE = BASE_DIR / "data" / "interface_trace.log"

logger = logging.getLogger("app_change_tracker")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    _trace_handler = logging.FileHandler(
        TRACE_LOG_FILE, mode="a", encoding="utf-8"
    )
    _trace_handler.setFormatter(
        logging.Formatter("%(asctime)s %(message)s", datefmt="%Y-%m-%dT%H:%M:%S")
    )
    logger.addHandler(_trace_handler)
    logger.propagate = False


class InterfaceDispatcher:
    """Wraps update-module calls with caller file/line logging."""

    def __init__(self, update_manager=None, log_file: Path | str = TRACE_LOG_FILE) -> None:
        self.log_file = Path(log_file)
        if update_manager is None:
            from interface.update_manager import get_update_manager
            update_manager = get_update_manager()
        self.update_manager = update_manager

    # ---------------------------------------------------------- traced run

    def trace_and_execute(self, target_function, *arguments, **keyword_arguments):
        """Record the caller's file/line, then run `target_function(*args,
        **kwargs)` and return its result."""
        frame = inspect.currentframe()
        try:
            caller = frame.f_back
            caller_file = caller.f_code.co_filename
            caller_line = caller.f_lineno
            caller_func = caller.f_code.co_name
        finally:
            del frame

        function_name = getattr(target_function, "__name__", str(target_function))
        module_name = getattr(target_function, "__module__", "Unknown Module")

        entry = (
            f"[TRACE LOG] Executing '{function_name}' from '{module_name}' "
            f"called from {caller_file}:{caller_line} ({caller_func}) "
            f"@ {datetime.now().isoformat(timespec='seconds')}"
        )
        print(entry)
        logger.info(entry)

        return target_function(*arguments, **keyword_arguments)

    def execute_action(self, domain_category: str, submodule_name: str,
                       function_to_call: str, *arguments, **keyword_arguments):
        """Dispatch an action through the update manager via string names."""
        try:
            target_module = self.update_manager.get_active_module(
                domain_category, submodule_name
            )
        except KeyError as exc:
            raise ModuleNotFoundError(
                f"Active update module '{submodule_name}' under domain "
                f"'{domain_category}' was not found."
            ) from exc
        target_function = getattr(target_module, function_to_call)
        return self.trace_and_execute(target_function, *arguments, **keyword_arguments)


_dispatcher: InterfaceDispatcher | None = None


def get_dispatcher() -> InterfaceDispatcher:
    """Process-wide InterfaceDispatcher singleton."""
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = InterfaceDispatcher()
    return _dispatcher