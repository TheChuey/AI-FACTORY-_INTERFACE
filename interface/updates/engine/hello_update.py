"""Example update module for the `engine` domain.

Discovered by UpdateManager and executable natively:
    from interface.update_manager import UpdateManager
    mod = UpdateManager().get_active_module("engine", "hello_update")
    print(mod.run_example())
"""


def run_example() -> str:
    """Return a short self-identification string for the example module."""
    return "hello from interface/updates/engine/hello_update.py"


def double(number: int | float) -> int | float:
    """Trivial demo transform: return twice `number`."""
    return number * 2