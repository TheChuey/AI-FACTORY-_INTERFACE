# GenV1 — Decisions

> **Location:** `docs/living/DECISIONS.md`
> **Prev:** `docs/living/TODO.md`

Important architecture decisions that future AI agents must not accidentally
undo. Grounded in the source and the historical changelog.

---

## 2026-09-20 — Documentation identity is GenV1

### Decision
All project documentation uses the name **GenV1**. Old names (Terminator1,
Terminator, Genessis, Genesisis) remain only inside code identifiers, env vars,
and user-visible UI strings.

### Context
The application had historical names; docs, UI strings and code identifiers
mixed them.

### Reason
Documentation should present a single consistent identity, while code
compatibility identifiers (`GENESSIS_*`, package/file names) must not change.

### Alternatives Considered
Renaming UI strings too (rejected: that is app text, not documentation);
renaming code identifiers (rejected: implementation detail).

### Consequences
Docs and UI names now differ; anyone editing docs must use GenV1, anyone
touching code keeps existing identifiers.

### Affected Components
`docs/` (all), `README.md`, `scripts/update_docs.py` headers.

### Related Files
`docs/INDEX.md`, `docs/development/DOCUMENTATION_RULES.md`, `README.md`.

---

## 2026-09-18 — Single master-copy recovery

### Decision
Recovery uses **one** master copy (`current-known-good-copy/`) with
overlay-restore semantics, replacing the old multi-baseline dry-run flow.

### Context
The previous baseline system used multiple baselines and dry-run/real restore
paths.

### Reason
One master copy is simpler to reason about; overlay-restore (backup differing
files, add master-only files, never delete live-only files) is safest for
recovering from bad edits without losing user work.

### Alternatives Considered
Multi-baseline diffing; pure overwrite restores (rejected — would delete
live-only work).

### Consequences
Overwritten files are backed up to
`<dataDir>/snapshots/pre_restore_backup/<stamp>/` before rollback; docs are
regenerated after restore; runtime data folders are excluded from comparisons.

### Affected Components
`interface/restore_manager.py`, `/api/interface/{status,snapshot,restore}`,
the Settings Updates/Interface card, `about/set_title.py` (retired restore CLI).

### Related Files
`interface/restore_manager.py`, `docs/living/CHANGELOG.md` (2026-09-18).

---

## 2026-09-17/2026-09-18 — HTTP-boundary-only monitoring; data folder reuse

### Decision
Agent telemetry (`agent_monitoring/`) is wired **at the HTTP boundary only** —
never editing the engine — and its data folder became the default runtime data
location.

### Context
A monitoring feature had previously been removed after breaking chats; the
subsystem was rebuilt carefully.

### Reason
Boundary-only wiring guarantees telemetry can never break a reply; reusing the
already-created data folder avoids a second root `data/` folder.

### Alternatives Considered
Deep engine instrumentation (rejected — the original fault); a new root data
folder (rejected — path churn).

### Consequences
`agent_monitoring/data/` is the default `DATA_DIR`; in-memory telemetry
counters reset on restart; the JSONL log is the durable record.

### Affected Components
`agent_monitoring/*`, `server/paths.py`, `server/server.py`.

### Related Files
`server/paths.py`, `docs/living/CHANGELOG.md` (2026-09-17, 2026-09-18).

---

## Historical decisions (pre-2026-09-20, abbreviated)

- **Agent = data, not code** — new agents are folders under
  `engine/agent_library/` (`agent.md` + `agent.json`); no new Python classes
  required. (Foundation of the whole engine.)
- **Id-aware folder lookup** — agent folders may differ from `agent.json#id`;
  the loader resolves by scanning (`engine/agents/loader.py`). Enables
  user-facing folder names (`Planner/`, `Builder/`) with pipeline ids.
- **Single reusable Agent class** — `chat` mode = no tools (no loop possible);
  `agent` mode = tool loop. Same runtime, configuration-only difference.
- **Tool-loop guard** — `MAX_TOOL_ROUNDS = 6`, `REPEAT_LIMIT = 3`; identical
  repeated tool rounds are stopped with a guard message.
- **Two-step deletion gate** — `delete_files(approved=False)` proposes;
  `approved=True` deletes only paths already recorded in
  `FileSession.pending_deletion`.
- **Model fallback** — an uninstalled requested model is dropped with a warning
  and replaced by a detected model; tool agents prefer tools-capable models.
- **Path authority** — `server/paths.py`: env var → per-OS key → plain key →
  project default; Windows drive paths ignored on non-Windows hosts.
- **Dual module loaders + wiring bridge** — `interface/updates/<domain>/`
  (UpdateManager) and flat Custom Modules Path (CustomModuleManager) stay
  separate; `interface/wiring/bridges.py` mirrors custom modules into the
  virtual `custom` domain for traced calls from core code.
- **Module execution off by default** — `INTERFACE_RUN_ENABLED` starts
  disabled; `/api/interface/run` is opt-in safety.
- **Three-step pipeline** — `feature_planner_agent` → `execute_engineer_agent`
  → `module_builder_agent`; each later step receives the user message plus the
  earlier steps' labeled replies (`config/pipeline.json`).

## Related documentation

- `docs/living/CHANGELOG.md`
- `docs/BLUEPRINT_SPEC.md`
- `docs/development/DOCUMENTATION_RULES.md`