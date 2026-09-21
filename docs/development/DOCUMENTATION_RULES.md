# GenV1 — Documentation Rules

> **Location:** `docs/development/DOCUMENTATION_RULES.md`
> **Next:** `docs/living/CHANGELOG.md` · **Prev:** `docs/development/TESTING.md`

The discipline for keeping the GenV1 documentation system synchronized with the
real application. Follow these rules on **every** implementation task.

---

## Authority order

When documentation disagrees, trust in this order:

```text
1. Running source code
2. Active configuration files
3. Actual filesystem structure
4. Tests / verified runtime behavior
5. Generated source snapshots
6. Architecture documentation
7. README / user documentation
8. Historical changelog
```

The **source code wins**. Historical behavior belongs in the changelog, not in
current architecture.

## Change-tracking checklist

Whenever an implementation task changes GenV1:

1. Identify affected files.
2. Identify affected architecture.
3. Identify affected APIs.
4. Identify affected configuration.
5. Identify affected documentation.
6. Run appropriate tests (see `docs/development/TESTING.md`).
7. Record the change in `docs/living/CHANGELOG.md`.
8. Update `docs/living/CURRENT_STATE.md` if the current architecture changed.
9. Update `docs/living/KNOWN_ISSUES.md` if an issue was introduced, resolved, or
   changed.
10. Update `docs/living/DECISIONS.md` if an architectural decision was made.
11. Update `docs/living/TODO.md` if work remains incomplete.
12. Regenerate generated docs:

```powershell
venv\Scripts\python scripts\update_documentation.py
```

## Anti-hallucination rules

1. Never invent a file.
2. Never invent an API endpoint.
3. Never invent an agent.
4. Never invent a tool.
5. Never claim something was tested when it was not tested.
6. Never convert a historical behavior into current behavior without verifying
   the source.
7. When information is uncertain, record `UNKNOWN — requires verification`.
8. When source code and documentation disagree, inspect the source code.
9. When a feature is partially implemented, document it as partially
   implemented.
10. Preserve historical information in the changelog rather than deleting it
    simply because the implementation changed.

## Consistency check on every docs update

Check for:

- old application names (Terminator1/Terminator/Genessis/Genesisis → **GenV1**
  in documentation; `GENESSIS_*` code identifiers and UI strings stay as they
  are)
- obsolete file paths
- deleted APIs
- renamed modules
- obsolete architecture descriptions
- stale folder trees
- incorrect agent names/tool names/configuration keys/endpoint descriptions

Documentation terminology is updated independently from code compatibility
identifiers.

## What automation may NOT touch

The following `docs/living/` documents require **controlled updates** and are
never overwritten by `scripts/update_documentation.py`:

```text
docs/living/CHANGELOG.md
docs/living/DECISIONS.md
docs/living/TODO.md
docs/living/KNOWN_ISSUES.md
docs/living/CURRENT_STATE.md
```

## Changelog entry format

```markdown
## YYYY-MM-DD — Change Name

### Summary
### Why
### Added
### Changed
### Removed
### Architecture Impact
### API Impact
### Documentation Impact
### Testing
### Known Issues
### Recovery / Migration
```

Sections may be omitted when genuinely not applicable. An incomplete test note
must never be removed to make the project look complete.

## A feature is not done until its documentation is updated

The documentation system is part of GenV1. A feature is not fully documented
until the appropriate architecture, reference, current-state, changelog, issue,
decision, or generated documentation has been updated.

## Related documentation

- `docs/INDEX.md`
- `docs/BLUEPRINT_SPEC.md`
- `docs/living/CHANGELOG.md`
- `docs/development/TESTING.md`