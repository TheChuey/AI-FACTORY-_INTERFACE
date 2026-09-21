# GenV1 — Testing & Verification

> **Location:** `docs/development/TESTING.md`
> **Next:** `docs/development/DOCUMENTATION_RULES.md` · **Prev:** `docs/development/ADDING_TOOLS.md`

How GenV1 is verified today, and the rules for recording test results honestly.

---

## Current verification toolkit

There is no packaged test suite. The project uses these lightweight checks:

### Python syntax

```powershell
venv\Scripts\python -m py_compile <file1>.py <file2>.py ...
```

Check every Python file you touched.

### JavaScript syntax

```powershell
node --check dashboard\js\<file>.js
```

Requires Node to be installed. Check every JS file you touched.

### FastAPI TestClient smoke tests (no browser, no server)

```python
from fastapi.testclient import TestClient
import server.server as srv

with TestClient(srv.app) as client:      # `with` runs lifespan -> managers wired
    r = client.get("/api/interface/status")
    assert r.status_code == 200
    ...
```

Note: `TestClient(srv.app)` runs the lifespan and therefore calls Ollama's
model scan and module discovery — offline machines still work (scan failures
are fail-soft), but pick unit-level checks when you only need one endpoint.

### Direct module checks

```python
from engine.agents.registry import list_agents
print(list_agents())
```

```python
from tools.registry import list_tools
print(list_tools())
```

### Manual runtime round-trips

- Start `python server.py` on a free port (override with `$env:PORT=9000`).
- Chat with a tool-using agent; confirm rows appear in
  `<dataDir>/toollog/tool_usage.jsonl` and `GET /api/logs/tools` returns them.
- Check the logs page (`/logs.html`) streams console + tool feeds.
- Exercise `/api/interface/status`, `apply`, `snapshot`, `restore` from the
  Settings card.

---

## Recording test results honestly

- **Never claim a test passed unless it was actually performed.**
- If a test could not be completed, record exactly what was verified and what
  remains — the changelog must keep incomplete-test notes visible rather than
  silently dropping them (see the tool-usage HTTP round-trip note in
  `docs/living/CHANGELOG.md`).
- Prefer explicit sections: verified items vs "to finish" items.

## Related documentation

- `docs/living/CHANGELOG.md` (how results are recorded)
- `docs/development/DOCUMENTATION_RULES.md`