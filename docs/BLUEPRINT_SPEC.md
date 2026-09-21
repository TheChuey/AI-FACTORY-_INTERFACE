# GenV1 — Blueprint Specification

> **Location:** `docs/BLUEPRINT_SPEC.md`
> **Next:** `docs/BLUEPRINT.md` (the assembled output) · **Prev:** `docs/INDEX.md`

This document is the **contract** for what `docs/BLUEPRINT.md` must contain. It
is mostly stable. Future AI agents updating the documentation use this
specification as the checklist for the master blueprint and for every
per-subsystem architecture document.

---

## 1. Purpose

Define the required content of `docs/BLUEPRINT.md` and of every document in
`docs/architecture/*.md`, so that documentation stays complete, consistent and
grounded in the real application.

## 2. The master blueprint (`docs/BLUEPRINT.md`)

`docs/BLUEPRINT.md` is assembled by `scripts/update_blueprint.py` from the
individually maintained architecture documents. It must answer:

- what GenV1 is
- how GenV1 is structured (layers)
- what the major components are
- how runtime requests flow
- how GenV1 is extended (agents, tools, modules)
- where runtime data goes
- how the documentation itself is generated and maintained

No document may invent a file, endpoint, agent, tool, module or behavior.
Uncertain information is recorded explicitly as `UNKNOWN — requires verification`.

## 3. Subsystem architecture template (`docs/architecture/*.md`)

Every major subsystem document uses this section skeleton. You must be able to
describe any subsystem using these fields:

```text
Purpose
Responsibilities
Does Not Own
Components
Inputs
Processing
Outputs
Dependencies
Consumers
Extension Points
Rules
Failure Behavior
Runtime Flow
Configuration
APIs
Source Files
Related Documentation
```

Rules:

- Do **not** force information into a section the application does not actually
  support — use `Not applicable`.
- `Source Files` lists only files that exist.
- `APIs` lists only endpoints/entry points that exist in the source.
- `Runtime Flow` describes behavior verified from the source code.
- `Failure Behavior` must match the actual guard logic (e.g. fail-safe logging,
  fallback model resolution, tool-loop guard).

## 4. Subsystem coverage

The blueprint must describe every subsystem that exists in GenV1:

| Subsystem | Architecture doc |
|---|---|
| System overview | `docs/architecture/SYSTEM.md` |
| Backend / HTTP boundary | `docs/architecture/BACKEND.md` |
| Frontend | `docs/architecture/FRONTEND.md` |
| Agent engine | `docs/architecture/AGENTS.md` |
| Tools | `docs/architecture/TOOLS.md` |
| Interface / update / restore | `docs/architecture/INTERFACE.md` |
| RAG memory | `docs/architecture/MEMORY.md` |
| Runtime data | `docs/architecture/DATA.md` |
| Configuration | `docs/architecture/CONFIGURATION.md` |
| Logging | `docs/architecture/LOGGING.md` |
| Monitoring (retired archive) | `docs/architecture/MONITORING.md` (see LOGGING/DATA) |

## 5. Blueprint assembly rules

- `scripts/update_blueprint.py` concatenates maintained sections in a fixed
  order; it never invents information.
- Manually maintained prose and assembled sections are clearly separated.
- The blueprint's identity, components and runtime-flow sections may be
  re-worded only against the source; the spec (this file) is the arbiter of
  required content, not of wording.

## 6. Related documentation

- `docs/INDEX.md`
- `docs/development/DOCUMENTATION_RULES.md`
- `scripts/update_blueprint.py`
- `scripts/update_documentation.py`