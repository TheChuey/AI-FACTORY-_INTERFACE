// ==========================================
// classes/terminal-window-out.js
// ==========================================
// Formats server-side log payloads into plain-text console blocks for the
// ChatWindow's console drawer (dashboard/js/classes/chat-window.js). The
// drawer lives in the chat window's MAIN BODY container - never chat bubbles.
//
//   1. pushToolLogs(...)    - structured tool_events from POST /api/chat
//   2. pushStartupLogs(...) - captured boot output from GET /api/logs/console
//   3. filterConsoleLines() - shared pure filter used by BOTH the drawer and
//                             the standalone pop-out page (logs.html) so they
//                             always agree on what counts as noise.
//
// Keeping the formatting here (instead of inside chat-window.js) means it can
// grow into full stdout/stderr streaming later without touching the window.

export function cleanPreview(text) {
    return String(text ?? "").replace(/[\r\n]+/g, " ").slice(0, 200);
}

// CSI escape codes from uvicorn's colored logs. Stripped here as a fallback
// for captures taken before server/console_log.py began sanitizing the buffer
// (a long-running server may still hold dirty lines until it restarts).
const ANSI_RE = /\x1b\[[0-9;?]*[A-Za-z]/g;

function stripAnsi(line) {
    return line.replace(ANSI_RE, "");
}

export function formatArgs(args) {
    try {
        const str = JSON.stringify(args || {});
        return str.length > 240 ? str.slice(0, 237) + "..." : str;
    } catch {
        return "";
    }
}

/**
 * Strip uvicorn/server noise from raw console lines. Used identically by the
 * chat drawer and the pop-out logs page.
 * @param {string | string[]} rawLogs - raw log text or array of lines
 * @returns {string[]} cleaned, non-empty lines
 */
export function filterConsoleLines(rawLogs) {
    const lines = Array.isArray(rawLogs)
        ? rawLogs
        : String(rawLogs ?? "").split("\n");

    return lines
        .map((line) => stripAnsi(String(line).trim()))
        .filter((line) => {
            if (!line) {
                return false;
            }
            // Uvicorn "INFO:" startup / access lines.
            if (/^INFO:/.test(line)) {
                return false;
            }
            // Access-log entries that slipped through without an INFO prefix,
            // e.g. '127.0.0.1 - "GET / HTTP/1.1" 200 OK'.
            if (/\b(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s+\/[^\s"]* HTTP/i.test(line)) {
                return false;
            }
            return true;
        });
}

/**
 * Render structured tool events (from POST /api/chat -> tool_events) into the
 * chat window's console drawer.
 * @param {import("./chat-window.js").ChatWindow} chat - target ChatWindow
 * @param {Array<Object>} toolEvents - event list from the backend
 */
export function pushToolLogs(chat, toolEvents = []) {
    if (!Array.isArray(toolEvents) || toolEvents.length === 0) {
        return;
    }
    const lines = ["[TOOL OUTPUT]"];
    toolEvents.forEach((evt) => {
        const time = evt.time || "--:--:--";
        const tool = evt.tool || "?";
        const argStr = formatArgs(evt.args);
        if (evt.status === "error") {
            lines.push(`[${time}] [ERR]  ${tool}(${argStr})`);
            lines.push(`    ERROR: ${cleanPreview(evt.error)}`);
        } else if (evt.status === "missing") {
            lines.push(`[${time}] [MISS] ${tool}(${argStr}) - not available`);
        } else {
            lines.push(`[${time}] [OK]   ${tool}(${argStr})`);
            if (evt.result_preview) {
                lines.push(`    -> ${cleanPreview(evt.result_preview)}`);
            }
        }
    });
    chat.appendConsoleBlock(lines.join("\n"));
}

/**
 * Publish captured boot output (GET /api/logs/console) into the chat window's
 * console drawer, filtered to the meaningful startup metadata ([llm], [paths],
 * [interface], [wiring], [custom-modules]).
 * @param {import("./chat-window.js").ChatWindow} chat - target ChatWindow
 * @param {string | string[]} rawLogs - captured console output
 */
export function pushStartupLogs(chat, rawLogs = []) {
    const kept = filterConsoleLines(rawLogs);
    if (kept.length === 0) {
        return;
    }
    chat.appendConsoleBlock(["[SYSTEM STARTUP LOGS]", ...kept].join("\n"));
}