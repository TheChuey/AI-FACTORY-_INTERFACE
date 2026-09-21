# GenV1 — TODO

> **Location:** `docs/living/TODO.md`
> **Next:** `docs/living/DECISIONS.md` · **Prev:** `docs/living/KNOWN_ISSUES.md`

Actionable future work, separated by priority. Do **not** convert speculative
ideas into confirmed requirements.

---

## High Priority

- [ ] Finish the tool-usage HTTP round-trip verification on a free port
  (`docs/living/KNOWN_ISSUES.md`, Issue 1). Update the changelog with results.
- [ ] Re-verify the data-folder relocation on a clean machine/OS (known-issue
  item 2).
- [ ] Manually re-run `scripts/update_documentation.py` after a real
  server boot + TestClient pass, and record the outcome.

## Normal Priority

- [ ] Add a genuine `docs/architecture/MONITORING.md` (or merge monitoring into
  LOGGING.md) reflecting the retired-but-present telemetry state.
- [ ] Re-seed `interface/updates/` domains with a documented, working example
  module, or state explicitly that the domains are intentionally empty.
- [ ] Cross-verify `rag_assistant`'s RAG path references in
  `agent.md`/pipeline outputs against `server/paths.py` after the relocation.
- [ ] Add a small `scripts/validate_docs.py`-style unit check (or fold into
  `update_documentation.py`) that fails on dangling doc paths, and wire it into
  a CI command if one ever exists.

## Future

- [ ] Consider formalizing `agent_monitoring/` as a supported telemetry feature
  (per known-issue 4), or removing it fully.
- [ ] Split the sections of `ENGINE/V1` core docs if the engine grows further;
  keep every subsystem at one doc file until it is unreasonable.
- [ ] Introduce a packaged test suite (the current verification toolkit is
  per-file `py_compile`/`node --check` + manual smoke tests).

## Investigate

- [ ] Whether `skills/ux_module_designer_skills.md` should move under
  `docs/reference/` or stay as a runtime skill consumed by agents (it is a
  runtime input — likely stays put, but confirm the boundary).
- [ ] Whether `server/server.py`'s fallback identity ("Terminator 2") in
  `/api/about` defaults should track the GenV1 documentation identity.

## Blocked

- [ ] None currently.

## Related documentation

- `docs/living/KNOWN_ISSUES.md`
- `docs/development/DOCUMENTATION_RULES.md`
- `docs/development/TESTING.md`