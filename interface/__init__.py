"""Modular Interface & System Update Architecture.

Update modules live under `interface/updates/<domain>/` and are discovered by
`interface/update_manager.py`; execution can be wrapped with caller tracing
(`interface/interface_dispatcher.py`); rollback against a baseline is handled
by `interface/restore_manager.py`. Design: docs/01_IDEA_AND_ARCHITECTURE.md.
"""