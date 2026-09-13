// ==========================================
// api/api.js - THE ONLY FILE THAT TALKS TO THE SERVER
// ==========================================
// Every HTTP request in the app goes through this module. No other
// file is allowed to call fetch() directly.
//
// ENDPOINTS USED:
//   getModels()            -> GET  /api/models
//   getAgents()            -> GET  /api/agents
//   sendChat(...)          -> POST /api/chat
//   loadAppSettings()      -> GET  /api/settings
//   saveAppSettings(...)   -> POST /api/settings   (merges)
//   saveChatSession(...)   -> POST /api/chat-save  (writes .txt file)

// "" (default) -> requests go to the SAME origin serving this page.
const API_BASE_URL = "";

/**
 * Low-level fetch helper: JSON in/out, readable error messages.
 */
async function request(path, options = {}) {
    let response;

    try {
        response = await fetch(API_BASE_URL + path, {
            headers: { "Content-Type": "application/json" },
            ...options,
        });
    } catch (networkError) {
        throw new Error(
            `Cannot reach the server at "${API_BASE_URL || window.location.origin}". Is it running? (python server.py)`
        );
    }

    if (!response.ok) {
        throw new Error(`Server error ${response.status} for ${path}`);
    }

    return response.json();
}

/** Model list for dropdowns. Returns [] when no Ollama models. */
export async function getModels() {
    const data = await request("/api/models");
    return data.models || [];
}

/** All discovered agents. Returns [] when agent_library/ is empty. */
export async function getAgents() {
    const data = await request("/api/agents");
    return data.agents || [];
}

/** Every tool id an agent can pick in its config. */
export async function getTools() {
    const data = await request("/api/tools");
    return data.tools || [];
}

/** Site identity for the H1 header: {title, subtitle} from about/about.json. */
export async function getAbout() {
    return request("/api/about");
}

// ---------------------------------------------------------------- interface

/** Full status blob for the Settings "Updates / Interface" card:
 * { catalog, archived, trace_tail, baseline, run_enabled, updates_dir, ... }. */
export async function getInterfaceStatus() {
    return request("/api/interface/status");
}

/** Reload update modules from disk + regenerate the docs snapshots. */
export async function applyInterface() {
    return request("/api/interface/apply", { method: "POST" });
}

/** Publish the current live tree as the new baseline (rebaseline). */
export async function snapshotInterface() {
    return request("/api/interface/snapshot", { method: "POST" });
}

/** Compare live vs baseline and report (or apply) the rollback.
 * DRY-RUN by default; send apply:true to actually restore. */
export async function restoreInterface({ baseline = "", apply = false, dryRun = true } = {}) {
    return request("/api/interface/restore", {
        method: "POST",
        body: JSON.stringify({ baseline, apply, dryRun }),
    });
}

/** Execute one update-module function by string names. May return 403 when
 * module execution is disabled (see setRunEnabled). */
export async function runInterface({ domain, module, function: fn, args = [], kwargs = {} }) {
    return request("/api/interface/run", {
        method: "POST",
        body: JSON.stringify({ domain, module, function: fn, args, kwargs }),
    });
}

/** Arm/disarm /api/interface/run for the current server process. */
export async function setRunEnabled(enabled) {
    return request("/api/interface/toggle-run", {
        method: "POST",
        body: JSON.stringify({ enabled }),
    });
}

/**
 * One agent's consolidated config for the settings page:
 * { agent, meta, markdown, tests, sharedTests }.
 */
export async function getAgentConfig(agentId) {
    return request(`/api/agents/${encodeURIComponent(agentId)}/config`);
}

/**
 * Partial update of one agent's config: {meta?, markdown?, tests?}.
 * Returns the fresh consolidated config object.
 */
export async function saveAgentConfig(agentId, partialConfig) {
    return request(`/api/agents/${encodeURIComponent(agentId)}/config`, {
        method: "PUT",
        body: JSON.stringify(partialConfig),
    });
}

/**
 * Send one chat message and return the server's reply + the tracked session.
 *
 * The server now owns the conversation: it returns a session_id you must send
 * back on every later message so the same chat keeps its own start/middle/end.
 * Pass newChat=true (or leave session_id empty) to start a fresh chat, which
 * finalizes whatever chat was active before.
 */
export async function sendChat({ message, agentId = "", model = "", history = [], sessionId = "", title = "", newChat = false, rag = false }) {
    const data = await request("/api/chat", {
        method: "POST",
        body: JSON.stringify({
            message,
            model,
            agent_id: agentId,
            history,
            session_id: sessionId,
            title,
            new_chat: newChat,
            rag,
        }),
    });
    return { reply: data.reply, session_id: data.session_id, title: data.title, events: data.events || [] };
}

/** Header rows for every saved chat + the active one, newest first. */
export async function listChats() {
    const data = await request("/api/chats");
    return data.chats || [];
}

/** One chat: its log row + the .txt content + parsed messages. */
export async function getChat(chatId) {
    return request(`/api/chats/${encodeURIComponent(chatId)}`);
}

/**
 * Finalize the active chat: writes its .txt (next version on a name collision)
 * and logs it. Safe to call even when nothing is active.
 * rag: optional bool override - commit this chat to the RAG memory store.
 */
export async function endChat({ title = "", rag = undefined } = {}) {
    const body = { title };
    if (typeof rag === "boolean") {
        body.rag = rag;
    }
    return request("/api/chats/end", {
        method: "POST",
        body: JSON.stringify(body),
    });
}

/** RAG store info: location + indexed chunk count. */
export async function ragStatus() {
    return request("/api/rag/status");
}

/** Re-index every saved transcript into the RAG store. */
export async function rebuildRag() {
    return request("/api/rag/rebuild", { method: "POST" });
}

/** Delete the RAG store (transcripts + chat records are untouched). */
export async function resetRag() {
    return request("/api/rag/reset", { method: "POST" });
}

/** Load the stored browser settings; {} when nothing saved yet. */
export async function loadAppSettings() {
    const data = await request("/api/settings");
    return data.settings || {};
}

/**
 * Load settings plus the meta flags from /api/settings.
 * Returns { settings, restartNeeded, platform } where restartNeeded is true
 * when the stored path settings changed since the server started (restart
 * required) and platform is "win", "linux" or "mac" (which path fields to
 * highlight).
 */
export async function loadAppSettingsWithMeta() {
    const data = await request("/api/settings");
    return {
        settings: data.settings || {},
        restartNeeded: Boolean(data.restartNeeded),
        platform: data.platform || "nix",
    };
}

/** Merge partial settings into what's stored (the rest survives). */
export async function saveAppSettings(partialSettings) {
    const data = await request("/api/settings", {
        method: "POST",
        body: JSON.stringify(partialSettings),
    });
    return data;
}

/**
 * Save a chat session as a nicely-formatted .txt file on the server.
 *
 * The transcript + a suggested file name + the configured output path
 * are all sent here and written by /api/chat-save.
 */
export async function saveChatSession({
    path = "",
    fileName = "",
    title = "",
    agentName = "",
    model = "",
    content = "",
}) {
    const result = await request("/api/chat-save", {
        method: "POST",
        body: JSON.stringify({ path, fileName, title, agentName, model, content }),
    });

    if (!result.saved) {
        throw new Error(result.error || "The server refused to save the chat.");
    }

    return result; // { saved, file }
}
