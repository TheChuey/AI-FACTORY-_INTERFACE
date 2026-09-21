# GenV1 — Known Issues

> **Location:** `docs/living/KNOWN_ISSUES.md`
> **Next:** `docs/living/TODO.md` · **Prev:** `docs/living/CURRENT_STATE.md`

Known problems and incomplete work. Do **not** mark an issue resolved until
verification has actually occurred.

---

## Issue: Tool-usage HTTP round-trip not re-verified

### Status
Open — incomplete verification (carried from the 2026-09-16 changelog entry).

### Symptoms
The `GET /api/logs/tools` live round-trip has not been re-run end to end.

### Cause
On a previous test day port `8000` was already in use by an earlier server
instance, so a fresh boot of `server/server.py` could not bind there; the test
was stopped on purpose to let the user fix the port situation and re-run later.

### Affected Components
- `server/tool_log.py`
- `server/server.py` (`GET /api/logs/tools`)
- `dashboard/logs.html` (Tool Usage tab)

### Reproduction
Start `server/server.py` on a free port (e.g. `$env:PORT=9000`), chat with a
tool-using agent (e.g. `module_builder_agent`), confirm rows in
`<dataDir>/toollog/tool_usage.jsonl`, `GET /api/logs/tools` returns them, and
the logs page streams them live.

### Current Workaround
Verified directly: `tool_log.append`/`tail()` filters work, and the full agent
path without Ollama produced correctly shaped events (`build_agent` +
`agent.act()`). The unfinished part is the HTTP layer + live page stream.

### Planned Resolution
Run the reproduction on a free port; record the result in the changelog.

### Related Changes
- `docs/living/CHANGELOG.md` — 2026-09-16 "Tool-usage tracker" entry.

---

## Issue: `server/paths.py` data-folder relocation — verify on a clean machine

### Status
Open — needs a repeat verification when next run on another machine/OS.

### Symptoms
N/A (recorded as a verification item from the 2026-09-18 relocation).

### Cause
`DATA_DIR` default moved from project-root `data/` to `agent_monitoring/data/`;
existing external data folders are untouched because configured paths win.

### Affected Components
`server/paths.py` and every consumer (chat store, tool log, RAG, interface
archive, snapshots).

### Reproduction
Boot with a configured `dataDirWindows` and confirm the external folder wins;
boot with no settings and confirm the new default location.

### Current Workaround
None needed; resolution precedence is documented.

### Planned Resolution
Re-verify once on a clean Windows + Linux machine after the documentation
restructure.

### Related Changes
- `docs/living/CHANGELOG.md` — 2026-09-18 "Master-copy recovery" entry.

---

## Issue: Debris from a generated-module experiment

### Status
Open (partially cleaned on 2026-09-20).

### Symptoms
Untracked stub files/copies existed (`server/dialog_box.py` empty file, a
`server/dialog_box.py/` directory of text stubs, and
`server/data/custom_modules/` one-line stub modules) — leftovers from an
experiment with the drop-in module generator.

### Cause
A `dialog_box` custom module run that was interrupted/experimental; the
generator scaffold appears to have been spread across multiple locations.

### Affected Components
`server/`, `server/data/`, `server/dialog_box.py/`.

### Reproduction
N/A (files removed). `git status` should now be clean of these stubs.

### Current Workaround
Removed on 2026-09-20 as part of the documentation restructure. If another real
`dialog_box` module is wanted, generate it with
`python about/set_title.py create-module dialog_box` (writes only to the
Custom Modules Path).

### Planned Resolution
None required beyond the removal; monitor `git status` for stray scaffold
output in future module-generation runs.

### Related Changes
- `docs/living/CHANGELOG.md` — 2026-09-20 "GenV1 documentation system" entry.

---

## Issue: Retired monitoring subsystem still present

### Status
Open — intentionally retained.

### Symptoms
`agent_monitoring/` is functionally retired (the Agent Monitor UI was removed)
but its telemetry endpoints and data folder remain active as of today's layout.

### Cause
Design decision: keep the HTTP-boundary telemetry and reuse its data folder as
the default runtime data location rather than tearing it out.

### Affected Components
`agent_monitoring/`, `/api/monitoring/*`.

### Reproduction
`GET /api/monitoring/status` still responds.

### Current Workaround
None needed; in-memory counters reset on restart, JSONL is the durable record.

### Planned Resolution
Either formalize as a supported telemetry feature or fully remove in a later
version and update `docs/architecture/LOGGING.md`.

### Related Changes
- `docs/living/DECISIONS.md`
- `docs/living/CHANGELOG.md` — 2026-09-17 / 2026-09-18 entries.

---

## UNKNOWN — requires verification

The following were **not** re-verified against a running server as part of the
2026-09-20 documentation restructure:

- Full boot + TestClient run after the docs restructure (no behavioral change
  was made, so risk is low).
- The exact contents of `current-known-good-copy/` drift after the docs moved
  (restore was not physically exercised).

Record a result in `docs/living/CHANGELOG.md` once verified.

## Related documentation

- `docs/development/TESTING.md`
- `docs/development/DOCUMENTATION_RULES.md`
- `docs/living/CHANGELOG.md`