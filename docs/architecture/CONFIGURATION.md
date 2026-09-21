# GenV1 — Configuration Architecture

> **Location:** `docs/architecture/CONFIGURATION.md`
> **Next:** `docs/architecture/LOGGING.md` · **Prev:** `docs/architecture/DATA.md`

## Purpose

Describe the single path/config authority (`server/paths.py`): which settings
exist, how they resolve, and which environment variables override them.

## Responsibilities

- Resolve `dataDir`, `chatSavePath`, `ragDbPath`, `customModulesPath` for the
  whole app.
- Apply per-OS overrides and environment-variable overrides.
- Report the resolved layout and whether a restart is required.

## Does Not Own

- Agent configs (`agent.json`), pipeline config (`pipeline.json`), appearance
  or model configs (frontend settings page).

## Components

- `server/paths.py` — constants, resolution functions, `about()` report,
  `restart_needed()`, `rag_config()`.
- `dashboard/config/app_settings.json` — the stored settings file.

## Inputs

- `dashboard/config/app_settings.json`
- Environment variables (`GENESSIS_DATA_DIR`, `GENESSIS_CHAT_SAVE_PATH`,
  `GENESSIS_RAG_DB_PATH`, `GENESSIS_CUSTOM_MODULES_PATH`,
  `GENESSIS_PLATFORM`).
- OS detection (`platform()`: `win` / `linux` / `mac`).

## Processing — precedence chain

For each path setting, from highest to lowest:

```text
1. Environment variable (GENESSIS_*)             [highest]
2. Per-OS key for the current platform          (dataDirWindows/Linux/Mac)
3. Plain key                                    (dataDir)
4. Project-relative default                     (agent_monitoring/data)
```

Details:

- Env values pass through `expanduser`/`expandvars` (`~` and `$VAR` expand).
- Relative values resolve against the project root (`BASE_DIR`).
- Absolute values are used as-is.
- A Windows drive path (`E:\...`, `\\server\share`) in the *plain* key is
  ignored on non-Windows hosts so a literal `E:\...` folder is never created.
- Path changes need a **server restart**; `restart_needed()` compares the
  stored keys against a snapshot taken at import time.

## Outputs

- Path constants used across the app (see `docs/architecture/DATA.md`).
- `paths.about()` exposed via `GET /api/settings` and `/api/rag/status`
  (including `platform` and the per-key override `sources` map).
- `rag_config()` (`{commitOnSave, autoIngest}`).

## Dependencies

- `dashboard/config/app_settings.json`; Python `os`/`pathlib`.

## Consumers

- Every logger, store, the chat store, memory, the interface layer, and the
  frontend settings page.

## Extension Points

- New path settings: add a key + env var + resolved constant in
  `server/paths.py`, expose in `about()`, surface in
  `dashboard/js/ui/config-form.js`.

## Rules

- `GENESSIS_*` env-var names are **compatibility identifiers** and are kept
  even though the documentation identity is GenV1.
- Stored path values are not rewritten by `GET/POST /api/settings` (merges
  only).

## Failure Behavior

- Blank env vars are ignored; missing files fall back to defaults gracefully.
- Unknown models/config keys never break boot.

## Runtime Flow

```text
Import server.paths
  -> read app_settings.json -> snapshot path keys
  -> resolve each setting (env > os-key > plain > default)
  -> expose constants + about()
Request /api/settings
  -> {settings, restartNeeded, platform}
```

## Configuration

The settings keys documented for this app are `dataDir`, `chatSavePath`,
`ragDbPath`, `customModulesPath` (+ `Windows`/`Linux`/`Mac` variants), `rag`,
`defaultAgentId`, `chatTests`, `disableVersioning`, `metadataHeader`.

## APIs

- `GET/POST /api/settings`, `GET /api/rag/status`.

## Source Files

```text
server/paths.py
dashboard/config/app_settings.json
dashboard/js/ui/config-form.js
```

## Related Documentation

- `docs/architecture/DATA.md`
- `docs/architecture/MEMORY.md`
- `docs/reference/API.md`
- `docs/living/CHANGELOG.md` (cross-platform paths entry)