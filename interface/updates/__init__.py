"""Active update modules, grouped by domain (engine / tools / server).

Each `.py` file here is discovered and imported by
`interface/update_manager.py`; callers run the module's functions directly
via `get_active_module(domain, name)`.
"""