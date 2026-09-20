// ==========================================
// js/logs-page.js - standalone console viewer for logs.html
// ==========================================
// Two full-page feeds for the server's captured output:
//   1. Console  - captured server console (GET /api/logs/console), the same
//                 data streamed into the chat widget's console drawer.
//   2. Tools    - structured tool-usage feed (GET /api/logs/tools): every tool
//                 call agents made, rendered as inspectable cards with the
//                 agent, model, status, args (paths highlighted) and a
//                 result/error preview.
//
// The Tools feed is a hallucination inspector: it classifies each call the way
// a watching developer would, not the way the backend logs it:
//   - op-fail  - the call EXECUTED but the operation failed (file not found,
//                bad directory) - the shape of a model inventing a path.
//   - fake     - the path argument looks placeholder-ish (bare filename,
//                "/path/to/...", "/echo_...", leading-slash absolute).
// Both poll every 2s, use the shared console filter, and only append fresh
// rows so copied output stays a clean chronological stream.

import {
    cleanPreview,
    filterConsoleLines,
} from "./classes/terminal-window-out.js";

const PRE_ELEMENT = document.getElementById("logs-body");
const TOOLS_ELEMENT = document.getElementById("tools-body");
const STATUS = document.getElementById("logs-status");
const TOOLBAR = document.getElementById("logs-toolbar");
const FILTER_INPUT = document.getElementById("logs-filter");
const FAILURES_TOGGLE = document.getElementById("logs-failures");
const PAUSE_BTN = document.getElementById("logs-pause");
const CLEAR_BTN = document.getElementById("logs-clear");
const COPY_BTN = document.getElementById("logs-copy");
const TAB_CONSOLE = document.getElementById("logs-tab-console");
const TAB_TOOLS = document.getElementById("logs-tab-tools");
const POLL_MS = 2000;
const MAX_LINES = 4000;

let activeTab = "console";
let paused = false;
let toolFilter = "";
let failuresOnly = false;

// Per-feed state: rendered rows (chronological) + how many source entries the
// server has returned so far (so we only append the fresh ones). Console rows
// are strings; tools rows are the raw event objects (rendered on demand so
// filters can re-run without losing the incremental "fresh" bookkeeping).
let feeds = {
    console: { rows: [], shownCount: 0 },
    tools: { rows: [], shownCount: 0 },
};

// ---------------------------------------------------------------------------
// tiny DOM helpers (safe textContent-only built rows)
// ---------------------------------------------------------------------------

function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
}

function setStatus(kind, text) {
    STATUS.textContent = text;
    STATUS.className = "logs-page-status " + kind;
}

// ---------------------------------------------------------------------------
// tool event classification
// ---------------------------------------------------------------------------

const PATH_KEY_RE = /(^|_)(path|paths|directory|dir|dirs|file|files|file_list|src|source|dest|destination|target|folder|readme)(s)?$/i;

const NONPATH_TOOLS = new Set([
    "search_chat_logs",
    "get_current_date",
    "tell_me_the_date_and_time",
]);

function pathArgs(evt) {
    const found = [];
    for (const [key, value] of Object.entries(evt.args || {})) {
        if (PATH_KEY_RE.test(key)) {
            if (Array.isArray(value)) {
                value.forEach((item) => {
                    if (typeof item === "string") found.push(item);
                });
            } else if (typeof value === "string") {
                found.push(value);
            }
        }
    }
    return found;
}

function isFabricatedPath(p) {
    const s = String(p || "").replace(/\\/g, "/");
    if (!s) return false;
    const lower = s.toLowerCase();
    if (lower.includes("/path/to/")) return true;
    // placeholder-ish glob words
    if (/^\/*(echo|tmp|temp|dummy|sample|example|workspace|placeholder)[/\-_.]*/.test(lower)) return true;
    // env-var / tilde style
    if (/^~\/|\$[a-z_][a-z0-9_]*\b/.test(lower)) return true;
    // bare filename with a known extension = invented (no directory context)
    const hasSep = lower.includes("/");
    if (!hasSep && /\.(md|txt|json|py|js|html|css|ts|tsx|toml|yaml|yml|log|ini|cfg|sql)$/.test(lower)) {
        return true;
    }
    // leading "/" absolute on a drive-letter box = usually a pasted placeholder
    if (/^\/[^/]/.test(lower)) return true;
    return false;
}

function isFabricated(evt) {
    if (evt.tool && NONPATH_TOOLS.has(evt.tool)) return false;
    return pathArgs(evt).some(isFabricatedPath);
}

function statusOf(evt) {
    if (evt.status === "error") return { kind: "err", label: "ERR" };
    if (evt.status === "missing") return { kind: "miss", label: "MISS" };
    if (evt.op_ok === false) return { kind: "op-fail", label: "OP-FAIL" };
    // Legacy events (no op_ok field): sniff the preview the old raw way.
    const preview = [evt.result_preview, evt.op_error, evt.error].filter(Boolean).join(" ");
    if (
        /success["']?\s*[:=]\s*(false|False|\bno\b)/.test(preview) ||
        /not found|no such file|not a valid directory|does not exist|cannot find|path does not/i.test(preview)
    ) {
        return { kind: "op-fail", label: "OP-FAIL" };
    }
    return { kind: "ok", label: "OK" };
}

// ---------------------------------------------------------------------------
// tool row rendering
// ---------------------------------------------------------------------------

function formatToolTime(iso) {
    return String(iso || "").replace("T", " ").slice(0, 19);
}

function renderValue(key, value) {
    const sp = el("span", "tf-val");
    if (typeof value === "string") {
        sp.textContent = value;
        if (PATH_KEY_RE.test(key)) {
            sp.className = "tf-path" + (isFabricatedPath(value) ? " tf-path-bad" : "");
        }
    } else if (value === null) {
        sp.textContent = "null";
    } else if (typeof value === "boolean" || typeof value === "number") {
        sp.textContent = String(value);
    } else {
        sp.textContent = JSON.stringify(value);
    }
    return sp;
}

function renderArgs(args) {
    const frag = document.createDocumentFragment();
    const entries = Object.entries(args || {});
    if (!entries.length) {
        const ghost = el("span", "tf-deemph");
        ghost.textContent = "(no args)";
        frag.appendChild(ghost);
        return frag;
    }
    entries.forEach(([key, value]) => {
        const keySp = el("span", "tf-arg");
        keySp.textContent = key;
        keySp.title = key;
        frag.appendChild(keySp);
        frag.appendChild(document.createTextNode(" = "));
        if (Array.isArray(value)) {
            value.forEach((item, index) => {
                if (index) frag.appendChild(document.createTextNode(", "));
                frag.appendChild(renderValue(key, item));
            });
        } else {
            frag.appendChild(renderValue(key, value));
        }
        frag.appendChild(document.createTextNode("  "));
    });
    return frag;
}

function renderToolRow(evt) {
    const st = statusOf(evt);
    const fake = isFabricated(evt);

    const card = el("article", "tf-row");
    card.dataset.status = st.kind;
    card.dataset.problem = st.kind !== "ok" || fake ? "1" : "0";

    const head = el("div", "tf-head");
    head.appendChild(el("span", "tf-time", formatToolTime(evt.time)));
    const agentSp = el("span", "tf-agent");
    agentSp.textContent = evt.agentName || evt.agentId || "?";
    head.appendChild(agentSp);
    const toolSp = el("span", "tf-tool");
    toolSp.textContent = evt.tool || "?";
    head.appendChild(toolSp);
    if (evt.model) head.appendChild(el("span", "tf-model", evt.model));
    head.appendChild(el("span", "tf-chip tf-chip-" + st.kind, st.label));
    if (fake) head.appendChild(el("span", "tf-chip tf-chip-fab", "FAKE PATH?"));
    card.appendChild(head);

    if (evt.origin) {
        const meta = el("div", "tf-meta");
        meta.textContent = "via " + evt.origin;
        card.appendChild(meta);
    }

    const argLine = el("div", "tf-args");
    argLine.appendChild(renderArgs(evt.args));
    card.appendChild(argLine);

    const body = el("div", "tf-result");
    if (evt.error) {
        body.textContent = "ERROR: " + cleanPreview(evt.error);
    } else if (evt.op_error) {
        body.textContent = "FAILED: " + cleanPreview(evt.op_error);
    } else if (evt.result_preview) {
        body.textContent = "-> " + cleanPreview(evt.result_preview);
    }
    card.appendChild(body);

    return card;
}

// ---------------------------------------------------------------------------
// rendering / filtering
// ---------------------------------------------------------------------------

function currentBody() {
    return activeTab === "tools" ? TOOLS_ELEMENT : PRE_ELEMENT;
}

function renderTools(alignBottom) {
    TOOLS_ELEMENT.textContent = "";
    const frag = document.createDocumentFragment();
    const rows = feeds.tools.rows;
    let shown = 0;
    let problems = 0;
    let fakes = 0;

    for (const evt of rows) {
        const st = statusOf(evt);
        const fake = isFabricated(evt);
        const isProblem = st.kind !== "ok" || fake;
        if (failuresOnly && !isProblem) continue;
        if (toolFilter) {
            const hay = [
                evt.agentName,
                evt.agentId,
                evt.tool,
                evt.model,
                JSON.stringify(evt.args || {}),
                evt.result_preview,
                evt.error,
                evt.op_error,
            ]
                .filter(Boolean)
                .join(" ")
                .toLowerCase();
            if (!hay.includes(toolFilter)) continue;
        }
        frag.appendChild(renderToolRow(evt));
        shown += 1;
        if (isProblem) problems += 1;
        if (fake) fakes += 1;
    }

    TOOLS_ELEMENT.appendChild(frag);
    if (alignBottom && !paused) {
        TOOLS_ELEMENT.scrollTop = TOOLS_ELEMENT.scrollHeight;
    }
    setStatus(
        "ok",
        paused
            ? "paused"
            : `${shown}/${rows.length} shown \u00b7 ${problems} failed \u00b7 ${fakes} suspicious path(s)`
    );
}

function render() {
    if (activeTab === "tools") {
        renderTools(true);
    } else {
        PRE_ELEMENT.textContent = feeds.console.rows.join("\n");
        if (!paused) PRE_ELEMENT.scrollTop = PRE_ELEMENT.scrollHeight;
        setStatus("ok", paused ? "paused" : "live - " + feeds.console.rows.length + " lines");
    }
}

function appendFresh(feed, freshRows) {
    feed.rows.push(...freshRows);
    if (feed.rows.length > MAX_LINES) {
        feed.rows = feed.rows.slice(feed.rows.length - MAX_LINES);
    }
}

// ---------------------------------------------------------------------------
// polling
// ---------------------------------------------------------------------------

async function pollConsole() {
    try {
        const res = await fetch("/api/logs/console?limit=1000");
        if (!res.ok) {
            throw new Error(res.statusText);
        }
        const data = await res.json();
        const lines = filterConsoleLines(data.logs || []);
        const feed = feeds.console;

        if (lines.length > feed.shownCount) {
            const fresh = lines.slice(feed.shownCount);
            appendFresh(feed, fresh);
            feed.shownCount = lines.length;
        }

        if (!data.captured) {
            setStatus("warn", "no capture running - start the server fresh");
        } else if (activeTab === "console") {
            render();
        } else {
            renderTools(false);
        }
    } catch (error) {
        if (activeTab === "console") {
            setStatus("error", "cannot reach server: " + error.message);
        }
    }
}

async function pollTools() {
    try {
        const res = await fetch("/api/logs/tools?limit=500");
        if (!res.ok) {
            throw new Error(res.statusText);
        }
        const data = await res.json();
        const events = data.events || []; // newest first
        const feed = feeds.tools;

        if (events.length > feed.shownCount) {
            // The newest `events.length - shownCount` events are the new ones
            // (the array is newest-first); reverse for a chronological append.
            const fresh = events.slice(0, events.length - feed.shownCount);
            feed.rows.push(...fresh.reverse());
            if (feed.rows.length > MAX_LINES) {
                feed.rows = feed.rows.slice(feed.rows.length - MAX_LINES);
            }
            feed.shownCount = events.length;
        }

        if (activeTab === "tools") {
            renderTools(true);
        }
    } catch (error) {
        if (activeTab === "tools") {
            setStatus("error", "cannot reach server: " + error.message);
        }
    }
}

// ---------------------------------------------------------------------------
// controls
// ---------------------------------------------------------------------------

function switchTab(tab) {
    activeTab = tab;
    TAB_CONSOLE.classList.toggle("active", tab === "console");
    TAB_TOOLS.classList.toggle("active", tab === "tools");
    PRE_ELEMENT.hidden = tab !== "console";
    TOOLS_ELEMENT.hidden = tab !== "tools";
    TOOLBAR.hidden = tab !== "tools";
    if (tab === "tools") {
        renderTools(false);
    } else {
        setStatus("ok", paused ? "paused" : "live - " + feeds.console.rows.length + " lines");
    }
}

TAB_CONSOLE.addEventListener("click", () => switchTab("console"));
TAB_TOOLS.addEventListener("click", () => switchTab("tools"));

FILTER_INPUT.addEventListener("input", () => {
    toolFilter = FILTER_INPUT.value.trim().toLowerCase();
    if (activeTab === "tools") renderTools(false);
});

FAILURES_TOGGLE.addEventListener("change", () => {
    failuresOnly = FAILURES_TOGGLE.checked;
    if (activeTab === "tools") renderTools(false);
});

PAUSE_BTN.addEventListener("click", () => {
    paused = !paused;
    PAUSE_BTN.textContent = paused ? "Resume" : "Pause";
    if (activeTab === "tools") renderTools(false);
});

CLEAR_BTN.addEventListener("click", () => {
    const feed = currentFeed();
    feed.rows = [];
    feed.shownCount = 0;
    if (activeTab === "tools") renderTools(false);
    else render();
});

COPY_BTN.addEventListener("click", async () => {
    try {
        await navigator.clipboard.writeText(currentBody().textContent || "");
        COPY_BTN.textContent = "Copied!";
        setTimeout(() => (COPY_BTN.textContent = "Copy"), 1200);
    } catch {
        setStatus("error", "copy blocked - select and copy manually");
    }
});

function currentFeed() {
    return feeds[activeTab];
}

TAB_CONSOLE.classList.add("active");
pollConsole();
pollTools();
setInterval(pollConsole, POLL_MS);
setInterval(pollTools, POLL_MS);