# GenV1 — Frontend Architecture

> **Location:** `docs/architecture/FRONTEND.md`
> **Next:** `docs/architecture/AGENTS.md` · **Prev:** `docs/architecture/BACKEND.md`

## Purpose

Describe the dashboard frontend: the pages served, the JS module layout, and
how UI actions (header buttons, modals, menu dropdowns, status dots) are
driven by custom-module manifests.

## Responsibilities

- Serve four pages: `index.html` (agent cards + floating chat widget),
  `chat.html` (self-contained chat), `config.html` (consolidated settings),
  `logs.html` (console + tool-usage viewer).
- Talk to the backend only through `dashboard/js/api/api.js`.
- Render custom-module header buttons from `/api/interface/status`
  (`renderDynamicHeaderButtons`).
- Apply one theme + font set globally (appearance), a console-size preset, and
  drag/resize/fullscreen behaviors for the chat window.

## Does Not Own

- Backend logic (see `docs/architecture/BACKEND.md`).
- Data persistence (it persists to `dashboard/config/app_settings.json` via
  the API, and to `about/about.json` via `/api/about`).

## Components

```text
dashboard/index.html      UI shell: agent cards + floating chat widget
dashboard/chat.html       standalone self-contained chat page
dashboard/config.html     consolidated settings page
dashboard/logs.html       standalone console + tool-usage viewer
dashboard/js/classes/     chat-window.js, ChatSession.js, terminal-window-out.js
dashboard/js/logic/       models.js (model dropdown), chat-formatter.js
dashboard/js/ui/          markdown.js, appearance.js, config-form.js, agents.js,
                          agent-editor.js, header-nav.js, interface-indicator.js,
                          interface-manager.js
dashboard/js/api/api.js   all HTTP calls
dashboard/js/app.js       index.html boot module
dashboard/js/config-page.js  config.html boot module
dashboard/js/logs-page.js    logs.html boot module
dashboard/css/styles.css  all styles (sections for console, logs, modal, etc.)
```

## Inputs

- `/api/*` responses (agents, models, settings, chats, interface status, logs).
- `UI_MANIFEST` entries from `/api/interface/status`.

## Processing

- Chat window boots, loads agents/models, renders cards/widgets; sends via
  `sendChat`; renders markdown replies; streams console + tool log feeds.
- Header buttons rendered per manifest; click handlers dispatch by
  `action` type:
  - `prompt_input` — prompt → POST `{"input": ...}` to `api_endpoint`.
  - `dropdown_menu` — flyout whose `items[]` inherit action types.
  - `open_modal` — fetch `schema_endpoint`, build a form, POST to
    `schema.target_endpoint`.
  - `qa_survey` — step wizard POSTing `{step, answers}` until `completed`.
  - `status_dot` — green dot on the trigger when a response has
    `indicate_success: true`.

## Outputs

- Rendered DOM, chat messages, console/tool feed, settings saved to the API.

## Dependencies

- Backend API (`/api/*`), `dashboard/config/app_settings.json`.

## Consumers

- Human users; indirect consumers are the custom modules whose buttons render.

## Extension Points

- Add pages under `dashboard/` and boot modules referencing `api/api.js`.
- Custom-module UI is NOT written in the frontend: modules declare
  `UI_MANIFEST` and the frontend renders it (see `docs/architecture/INTERFACE.md`).

## Rules

- `chat.html` is self-contained (single-file page).
- Log bodies stay an always-dark terminal look in both themes.
- Pause/Clear/Copy in the logs page operate on the active tab.

## Failure Behavior

- `renderDynamicHeaderButtons` is fail-soft: renders nothing on servers with no
  custom modules.
- Form controls are themed explicitly (e.g. `.cw-input` sets its own color).

## Runtime Flow

```text
Page load -> api.getAgents/getModels -> render cards/widget
Chat send -> sendChat() -> POST /api/chat -> render reply + tool_events
Header -> GET /api/interface/status -> renderDynamicHeaderButtons(manifests)
Settings -> GET/POST /api/settings + agent config endpoints
Logs page -> poll /api/logs/console + /api/logs/tools every 2s
```

## Configuration

- Browser defaults live in `dashboard/config/app_settings.json` (the "Settings
  page" data), read/written via `GET/POST /api/settings`.

## APIs

Consumed API endpoints: `docs/reference/API.md`.

## Source Files

```text
dashboard/index.html
dashboard/chat.html
dashboard/config.html
dashboard/logs.html
dashboard/js/app.js
dashboard/js/config-page.js
dashboard/js/logs-page.js
dashboard/js/api/api.js
dashboard/js/ui/*.js
dashboard/js/classes/*.js
dashboard/js/logic/*.js
dashboard/css/styles.css
```

## Related Documentation

- `docs/architecture/INTERFACE.md`
- `docs/development/CUSTOM_MODULES.md`
- `docs/reference/FILES.md`