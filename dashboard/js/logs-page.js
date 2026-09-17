// ==========================================
// js/logs-page.js - standalone console viewer for logs.html
// ==========================================
// Two full-page feeds for the server's captured output:
//   1. Console  - captured server console (GET /api/logs/console), the same
//                 data streamed into the chat widget's console drawer.
//   2. Tools    - structured tool-usage feed (GET /api/logs/tools): every tool
//                 call agents made, with ISO timestamp, agent, tool, status
//                 and a result/error preview.
// Both poll every 2s, apply the SAME shared console filter as the drawer
// (classes/terminal-window-out.js), and only append lines they have not shown
// yet so copied output is a clean chronological stream.

import {
    cleanPreview,
    formatArgs,
    filterConsoleLines,
} from "./classes/terminal-window-out.js";

const PRE_ELEMENT = document.getElementById("logs-body");
const TOOLS_ELEMENT = document.getElementById("tools-body");
const STATUS = document.getElementById("logs-status");
const PAUSE_BTN = document.getElementById("logs-pause");
const CLEAR_BTN = document.getElementById("logs-clear");
const COPY_BTN = document.getElementById("logs-copy");
const TAB_CONSOLE = document.getElementById("logs-tab-console");
const TAB_TOOLS = document.getElementById("logs-tab-tools");
const POLL_MS = 2000;
const MAX_LINES = 4000;

let activeTab = "console";
let paused = false;

// Per-feed state: rendered rows (chronological) + how many source entries the
// server has returned so far (so we only append the fresh ones).
let feeds = {
    console: { rows: [], shownCount: 0 },
    tools: { rows: [], shownCount: 0 },
};

function currentBody() {
    return activeTab === "tools" ? TOOLS_ELEMENT : PRE_ELEMENT;
}

function currentFeed() {
    return feeds[activeTab];
}

function setStatus(kind, text) {
    STATUS.textContent = text;
    STATUS.className = "logs-page-status " + kind;
}

function render() {
    const body = currentBody();
    const feed = currentFeed();
    body.textContent = feed.rows.join("\n");
    if (!paused) {
        body.scrollTop = body.scrollHeight;
    }
}

function formatToolTime(iso) {
    return String(iso || "").replace("T", " ").slice(0, 19);
}

function formatToolEvent(evt) {
    const time = formatToolTime(evt.time);
    const tool = evt.tool || "?";
    const agent = evt.agentName || evt.agentId || "?";
    const argStr = formatArgs(evt.args);
    const lines = [];
    if (evt.status === "error") {
        lines.push(`[${time}] [ERR]  ${agent} - ${tool}(${argStr})`);
        lines.push(`    ERROR: ${cleanPreview(evt.error)}`);
    } else if (evt.status === "missing") {
        lines.push(`[${time}] [MISS] ${agent} - ${tool}(${argStr}) - not available`);
    } else {
        lines.push(`[${time}] [OK]   ${agent} - ${tool}(${argStr})`);
        if (evt.result_preview) {
            lines.push(`    -> ${cleanPreview(evt.result_preview)}`);
        }
    }
    return lines.join("\n");
}

function appendFresh(feed, freshRows) {
    feed.rows.push(...freshRows);
    if (feed.rows.length > MAX_LINES) {
        feed.rows = feed.rows.slice(feed.rows.length - MAX_LINES);
    }
}

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
            render();
        }

        if (!data.captured) {
            setStatus("warn", "no capture running - start the server fresh");
        } else if (activeTab === "console") {
            setStatus("ok", paused ? "paused" : "live - " + feed.rows.length + " lines");
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
            const fresh = events
                .slice(0, events.length - feed.shownCount)
                .reverse()
                .map(formatToolEvent);
            appendFresh(feed, fresh);
            feed.shownCount = events.length;
            render();
        }

        if (activeTab === "tools") {
            setStatus(
                "ok",
                paused ? "paused" : "live - " + feed.rows.length + " tool call(s)"
            );
        }
    } catch (error) {
        if (activeTab === "tools") {
            setStatus("error", "cannot reach server: " + error.message);
        }
    }
}

function switchTab(tab) {
    activeTab = tab;
    TAB_CONSOLE.classList.toggle("active", tab === "console");
    TAB_TOOLS.classList.toggle("active", tab === "tools");
    PRE_ELEMENT.hidden = tab !== "console";
    TOOLS_ELEMENT.hidden = tab !== "tools";
    setStatus("ok", paused ? "paused" : "switched");
    render();
}

TAB_CONSOLE.addEventListener("click", () => switchTab("console"));
TAB_TOOLS.addEventListener("click", () => switchTab("tools"));

PAUSE_BTN.addEventListener("click", () => {
    paused = !paused;
    PAUSE_BTN.textContent = paused ? "Resume" : "Pause";
    setStatus("ok", paused ? "paused" : "live");
});

CLEAR_BTN.addEventListener("click", () => {
    const feed = currentFeed();
    feed.rows = [];
    feed.shownCount = 0;
    render();
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

TAB_CONSOLE.classList.add("active");
pollConsole();
pollTools();
setInterval(pollConsole, POLL_MS);
setInterval(pollTools, POLL_MS);