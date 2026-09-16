// ==========================================
// js/logs-page.js - standalone console viewer for logs.html
// ==========================================
// Full-page terminal for the captured server console (GET /api/logs/console):
// the same data streamed into the chat widget's console drawer, but in its
// own tab. Polls every 2s, applies the SAME shared filter as the drawer
// (classes/terminal-window-out.js), and only appends lines it has not shown
// yet so copied output is a clean chronological stream.

import { filterConsoleLines } from "./classes/terminal-window-out.js";

const PRE_ELEMENT = document.getElementById("logs-body");
const STATUS = document.getElementById("logs-status");
const PAUSE_BTN = document.getElementById("logs-pause");
const CLEAR_BTN = document.getElementById("logs-clear");
const COPY_BTN = document.getElementById("logs-copy");
const POLL_MS = 2000;
const MAX_LINES = 4000;

let paused = false;
let shownCount = 0;
let rows = [];

function setStatus(kind, text) {
    STATUS.textContent = text;
    STATUS.className = "logs-page-status " + kind;
}

function render() {
    PRE_ELEMENT.textContent = rows.join("\n");
    if (!paused) {
        PRE_ELEMENT.scrollTop = PRE_ELEMENT.scrollHeight;
    }
}

async function pollOnce() {
    try {
        const res = await fetch("/api/logs/console?limit=1000");
        if (!res.ok) {
            throw new Error(res.statusText);
        }
        const data = await res.json();
        const lines = filterConsoleLines(data.logs || []);

        if (lines.length > shownCount) {
            const fresh = lines.slice(shownCount);
            rows.push(...fresh);
            if (rows.length > MAX_LINES) {
                rows = rows.slice(rows.length - MAX_LINES);
                shownCount = lines.length - MAX_LINES;
            }
            shownCount = lines.length;
            render();
        }

        if (!data.captured) {
            setStatus("warn", "no capture running - start the server fresh");
        } else {
            setStatus("ok", paused ? "paused" : "live - " + lines.length + " lines");
        }
    } catch (error) {
        setStatus("error", "cannot reach server: " + error.message);
    }
}

PAUSE_BTN.addEventListener("click", () => {
    paused = !paused;
    PAUSE_BTN.textContent = paused ? "Resume" : "Pause";
    setStatus("ok", paused ? "paused" : "live - " + rows.length + " lines");
});

CLEAR_BTN.addEventListener("click", () => {
    rows = [];
    shownCount = 0;
    render();
});

COPY_BTN.addEventListener("click", async () => {
    try {
        await navigator.clipboard.writeText(PRE_ELEMENT.textContent || "");
        COPY_BTN.textContent = "Copied!";
        setTimeout(() => (COPY_BTN.textContent = "Copy"), 1200);
    } catch {
        setStatus("error", "copy blocked - select and copy manually");
    }
});

pollOnce();
setInterval(pollOnce, POLL_MS);