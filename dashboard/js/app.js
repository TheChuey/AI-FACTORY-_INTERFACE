// ==========================================
// js/app.js - ENTRY POINT (the only script index.html loads)
// ==========================================
// BOOT:
//   1. Render the AI agent card grid (ui/agents.js)
//   2. Build ONE persistent floating chat widget (classes/chat-window.js
//      in flyout mode) that sits in the corner of the screen. It targets
//      the first agent by default and can switch agents via the dropdown
//      in its header. Clicking an agent card also switches + expands it.
//      The ChatWindow ONLY renders; all AI/session/persist logic lives here.
//   (All configuration/settings now live on /static/config.html.)
//
// FOLDER MAP:
//   js/app.js                        -> boot + wiring (this file)
//   js/logic/                        -> pure logic (models, chat-formatter)
//   js/classes/ChatSession.js        -> chat data model (no DOM)
//   js/classes/chat-window.js        -> reusable flyout chat engine
//   js/api/                          -> every server call (api.js)
//   js/ui/                           -> agents, markdown, appearance (+ config-page)

import { renderAgents } from "./ui/agents.js";
import { applyAppearance } from "./ui/appearance.js";
import { renderHeaderNav, renderDynamicHeaderButtons } from "./ui/header-nav.js";
import { ChatSession } from "./classes/ChatSession.js";
import { ChatFactory } from "./classes/chat-window.js";
import { pushToolLogs, pushStartupLogs } from "./classes/terminal-window-out.js";
import { renderMarkdown } from "./ui/markdown.js";
import { renderInterfaceIndicator } from "./ui/interface-indicator.js";
import * as api from "./api/api.js";

// ---- app-level state ----
let settings = {};            // cached app settings (chatSavePath, defaults)
let agents = [];              // the list of discovered agents
let widget = null;            // the single persistent ChatWindow (flyout)
let activeAgentId = null;     // which agent the widget is currently talking to

// One ChatSession per agent so history survives switching agents in the
// single widget. Sending routes through the currently active session.
const agentSessions = new Map(); // agentId -> ChatSession

// Auto-"say hi" feature (experimental, may be removed).
const AUTO_HI_TEXT = "hi";     // message injected into a brand-new chat
const AUTO_HI_DEFAULT = true;  // default state of the auto-hi toggle

// ---- boot ----
async function boot() {
    // 0. Cache server settings and apply the stored appearance (font + size)
    //    to THIS page right away - chat.html applies its own copy on load.
    try {
        settings = await api.loadAppSettings();
    } catch (_) {
        settings = {};
    }
    applyAppearance(settings);

    // 0b. Header: shared nav + the editable H1/tagline from about/about.json.
    //     Fail-soft - a stale server or missing /api/about keeps the defaults
    //     already written into the HTML.
    const navSlot = document.getElementById("app-nav");
    if (navSlot) {
        navSlot.replaceChildren(renderHeaderNav("dashboard"));

        // Phase 2 - Dynamic UI Manifests: mount any header buttons declared
        // by drop-in custom modules (interface/custom_module_manager.py).
        // Fail-soft; adds nothing on a server with no custom modules loaded.
        // Handles: prompt_input, dropdown menus, schema modals and Q&A wizards,
        // plus the green success-status dot (endpoint returns indicate_success).
        renderDynamicHeaderButtons(navSlot, async (btnConfig, parentBtn) => {
            const markSuccessDot = () => {
                if (parentBtn && !parentBtn.querySelector(".status-dot")) {
                    const dot = document.createElement("span");
                    dot.className = "status-dot";
                    parentBtn.appendChild(dot);
                }
            };

            // 1. ACTION: Prompt Input (original; posts { input } generically so
            //    any module's execute route can read payload.get("input")).
            if (btnConfig.action === "prompt_input") {
                const userInput = window.prompt(btnConfig.prompt_message || "Enter value:");
                if (userInput && userInput.trim()) {
                    try {
                        const response = await fetch(btnConfig.api_endpoint, {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({ input: userInput.trim() }),
                        });
                        const resData = await response.json();
                        alert(resData.message || "Action completed!");
                        if (resData.indicate_success) markSuccessDot();
                    } catch (error) {
                        alert(`Action failed: ${error.message}`);
                    }
                }
            }

            // 2. ACTION: Open Schema Modal Dialog.
            else if (btnConfig.action === "open_modal") {
                try {
                    const schemaRes = await fetch(btnConfig.schema_endpoint);
                    const schema = await schemaRes.json();
                    openModal(schema.title, (modalBody, closeModal) => {
                        const form = document.createElement("form");

                        (schema.components || []).forEach((item) => {
                            const field = document.createElement("div");
                            field.className = "field";

                            if (item.type === "input") {
                                const label = document.createElement("label");
                                label.textContent = item.label || "";
                                const input = document.createElement("input");
                                input.type = "text";
                                input.name = item.name;
                                input.placeholder = item.placeholder || "";
                                field.append(label, input);
                            } else if (item.type === "select") {
                                const label = document.createElement("label");
                                label.textContent = item.label || "";
                                const select = document.createElement("select");
                                select.name = item.name;
                                (item.options || []).forEach((opt) => {
                                    const option = document.createElement("option");
                                    option.value = opt;
                                    option.textContent = opt;
                                    select.appendChild(option);
                                });
                                field.append(label, select);
                            } else if (item.type === "checkbox") {
                                field.className = "field field-toggle";
                                const span = document.createElement("span");
                                span.textContent = item.label || "";
                                const sw = document.createElement("label");
                                sw.className = "field-switch";
                                const cb = document.createElement("input");
                                cb.type = "checkbox";
                                cb.name = item.name;
                                if (item.value) cb.checked = true;
                                sw.appendChild(cb);
                                field.append(span, sw);
                            } else if (item.type === "button") {
                                const submit = document.createElement("button");
                                submit.type = "submit";
                                submit.className = "btn btn-primary";
                                submit.textContent = item.label || "Submit";
                                field.appendChild(submit);
                            }
                            form.appendChild(field);
                        });

                        form.addEventListener("submit", async (e) => {
                            e.preventDefault();
                            const payload = {};
                            new FormData(form).forEach((val, key) => { payload[key] = val; });
                            try {
                                const execRes = await fetch(schema.target_endpoint, {
                                    method: "POST",
                                    headers: { "Content-Type": "application/json" },
                                    body: JSON.stringify(payload),
                                });
                                const execData = await execRes.json();
                                closeModal();
                                alert(execData.message || "Submitted successfully!");
                                if (execData.indicate_success) markSuccessDot();
                            } catch (error) {
                                alert(`Submit failed: ${error.message}`);
                            }
                        });

                        modalBody.appendChild(form);
                    });
                } catch (error) {
                    alert(`Could not load dialog schema: ${error.message}`);
                }
            }

            // 3. ACTION: Interactive Q&A Wizard (step-by-step choice survey).
            else if (btnConfig.action === "qa_survey") {
                let step = 1;
                const answers = {};
                openModal("Interactive Q&A Wizard", (modalBody, closeModal) => {
                    const renderStep = async () => {
                        modalBody.replaceChildren();
                        try {
                            const res = await fetch(btnConfig.qa_endpoint, {
                                method: "POST",
                                headers: { "Content-Type": "application/json" },
                                body: JSON.stringify({ step, answers }),
                            });
                            const data = await res.json();

                            if (data.completed) {
                                const doneWrap = document.createElement("div");
                                const heading = document.createElement("h3");
                                heading.textContent = data.message || "Complete!";
                                const pre = document.createElement("pre");
                                pre.textContent = data.summary || "";
                                const doneBtn = document.createElement("button");
                                doneBtn.className = "btn btn-primary";
                                doneBtn.textContent = "Done";
                                doneBtn.onclick = () => {
                                    closeModal();
                                    if (data.indicate_success) markSuccessDot();
                                };
                                doneWrap.append(heading, pre, doneBtn);
                                if (data.record_path) {
                                    const saved = document.createElement("p");
                                    saved.className = "status-message ok";
                                    saved.textContent = "Record saved: " + data.record_path;
                                    doneWrap.appendChild(saved);
                                }
                                modalBody.appendChild(doneWrap);
                                return;
                            }

                            const qEl = document.createElement("h3");
                            qEl.textContent = `Step ${data.step}: ${data.question}`;
                            modalBody.appendChild(qEl);

                            const optionsGrid = document.createElement("div");
                            optionsGrid.className = "qa-options-grid";
                            (data.options || []).forEach((opt) => {
                                const optBtn = document.createElement("button");
                                optBtn.className = "qa-option-btn";
                                optBtn.textContent = opt;
                                optBtn.onclick = () => {
                                    answers[`step_${step}`] = opt;
                                    step += 1;
                                    renderStep();
                                };
                                optionsGrid.appendChild(optBtn);
                            });
                            modalBody.appendChild(optionsGrid);
                        } catch (error) {
                            modalBody.replaceChildren();
                            const errEl = document.createElement("p");
                            errEl.className = "status-message error";
                            errEl.textContent = "Q&A failed: " + error.message;
                            modalBody.appendChild(errEl);
                        }
                    };
                    renderStep();
                });
            }
        });
    }
    try {
        const about = await api.getAbout();
        setPageTitle(about.title, about.subtitle);
    } catch (_) {
        /* keep the hardcoded defaults */
    }

    // 0c. Interface pill: "N update modules" in the header (hidden on servers
    //     without /api/interface/* or when nothing is loaded).
    renderInterfaceIndicator({
        container: document.querySelector(".app-header-row"),
        onMesh: true,
    });

    // 1. Render agent cards (returns the full agent list).
    agents = await renderAgents({
        containerId: "agent-cards",
        statusId: "agent-status-area",
        onSelect: onAgentSelected,
    });

    // 2. Create the persistent corner widget for the first agent (if any).
    //    (The old inline config panel moved to /static/config.html - see the
    //    "Settings" link in the header.)

    // 3. Create the persistent corner widget for the first agent (if any).
    if (agents.length > 0) {
        buildWidget();
    }

    // 4. Console drawer: surface the captured boot metadata ([llm], [paths],
    //    [interface], [wiring], [custom-modules]) filter-logged to the chat
    //    window's main body. Fail-soft - an older server without the endpoint
    //    simply leaves the drawer absent until real tool logs arrive.
    if (widget) {
        try {
            const consoleLog = await api.getConsoleLogs();
            pushStartupLogs(widget, consoleLog.logs);
        } catch (_) {
            /* no /api/logs/console -> nothing extra to show */
        }
    }
}

/** Update the header H1 + tagline (fall back to the current text when a
 *  value is empty). Directly driven by about/about.json on the server. */
function setPageTitle(title, subtitle) {
    const titleEl = document.getElementById("app-title");
    const taglineEl = document.getElementById("app-tagline");
    if (titleEl && title && title.trim()) {
        titleEl.textContent = title.trim();
    }
    if (taglineEl && subtitle && subtitle.trim()) {
        taglineEl.textContent = subtitle.trim();
    }
    // Browser-tab title: "Genessis - <subtitle>" (falls back to the raw title).
    const cleanSub = (subtitle && subtitle.trim()) ? " \u2014 " + subtitle.trim() : "";
    document.title = ((title && title.trim()) ? title.trim() : "") + cleanSub;
}

/** Create the single persistent flyout widget + wire its agent switcher. */
function buildWidget() {
    const defaultAgent = agents[0];
    const config = buildAgentConfig(defaultAgent);
    config.layout.flyout = true;
    // Wider flyout so the console drawer reads comfortably (was 780).
    config.layout.width = 920;

    widget = ChatFactory.create(config);

    // Feed the switcher with all selectable agents.
    widget.setAgents(agents);

    // Console drawer: list the discovered agents as clickable chips. Clicking
    // one switches the chat to that agent (kept in sync by switchToAgent).
    widget.setConsoleAgents(agents, activeAgentId);
    widget.onConsoleAgent((agentId) => {
        const agent = agents.find((a) => String(a.id) === String(agentId));
        if (agent) {
            switchToAgent(agent, false);
        }
    });

    // Present the default agent (fresh session, no auto-hi on startup).
    selectSession(defaultAgent, false);
    widget.setActiveConsoleAgent(defaultAgent.id);

    // Route sends to the active session.
    widget.onSend((text) => {
        const session = activeSession();
        if (session) {
            handleSend(session, widget, text);
        }
    });

    widget.onAction("saveChat", () => {
        const session = activeSession();
        if (session) {
            handleSaveAction(session, widget);
        }
    });
    widget.onAction("clearChat", () => {
        const session = activeSession();
        if (session) {
            handleClearAction(session, widget);
        }
    });

    // Switcher in the widget header changes the active agent.
    widget.onSwitchAgent((agentId) => {
        const agent = agents.find((a) => String(a.id) === String(agentId));
        if (agent) {
            switchToAgent(agent, false);
        }
    });
}

/** The ChatSession for the agent currently shown in the widget. */
function activeSession() {
    return activeAgentId ? agentSessions.get(activeAgentId) : null;
}

// ---- agent card click -> switch + expand the widget ----
function onAgentSelected(agent) {
    if (!widget) {
        return;
    }
    switchToAgent(agent);
    if (!widget.isOpen) {
        widget.open();
    }
}

/** (Re)point the widget at an agent, keeping its per-agent session. */
function switchToAgent(agent, autoHi = true) {
    if (!widget) {
        return;
    }
    widget.setActiveAgent(agent.id);
    widget.setActiveConsoleAgent(agent.id);
    selectSession(agent, autoHi);
}

/**
 * Ensure a ChatSession exists for the agent and load it into the widget.
 * The auto-"say hi" fires only the first time we meet this agent, and only
 * once the widget is expanded so the injected message can be sent.
 */
function selectSession(agent, autoHi = false) {
    let session = agentSessions.get(agent.id);
    const created = !session;
    if (!session) {
        session = new ChatSession({
            agentId: agent.id,
            agentName: agent.name,
            model: settings.defaultModel || "",
        });
        agentSessions.set(agent.id, session);
    }
    activeAgentId = agent.id;

    if (created && autoHi && widget && widget.isOpen && widget.getPanelValues().autoHi === true) {
        // Prefill "hi" so the chat starts itself after you've named it (the
        // "Chat title" field in the panel). No auto-send: you get a chance
        // to title the chat first.
        widget.setInputValue(AUTO_HI_TEXT);
        widget._input?.focus();
    }
    return created;
}

/**
 * The entity config that drives the chat window for one AI agent.
 * The right panel is generated fully from `sections` - no HTML edits
 * needed to change an agent's controls/branding.
 */
function buildAgentConfig(agent) {
    const commitOnSave =
        settings.rag && typeof settings.rag.commitOnSave === "boolean"
            ? settings.rag.commitOnSave
            : false;
    return {
        id: agent.id,
        type: "agent",
        name: agent.name,
        title: agent.name,
        description: agent.description || "AI agent",
        layout: { rightPanel: true, resizable: true, collapsible: true, panelWidth: 300 },
        renderMarkdown,
        headerToggle: {
            name: "ragCommit",
            label: "Save to memory",
            value: commitOnSave,
        },
        sections: [
            {
                title: "Agent Information",
                fields: [
                    { type: "text", label: "Status", value: "Ready" },
                    { type: "text", label: "Category", value: agent.mode || "General" },
                ],
            },
            {
                title: "Chat",
                fields: [
                    {
                        type: "input",
                        name: "chatTitle",
                        label: "Chat title",
                        placeholder: "Name this chat...",
                        value: "",
                    },
                ],
            },
            {
                title: "Actions",
                fields: [
                    { type: "button", label: "Save chat", action: "saveChat" },
                    { type: "button", label: "Clear chat", action: "clearChat" },
                ],
            },
            {
                title: "Behavior",
                fields: [
                    {
                        type: "toggle",
                        name: "autoHi",
                        label: '"Say hi" on a new chat',
                        value: AUTO_HI_DEFAULT,
                    },
                ],
            },
        ],
    };
}

// ---- send flow (the ChatWindow already showed the user bubble) ----
async function handleSend(session, chat, text) {
    session.addUserMessage(text);
    chat.setWaiting(true);

    try {
        const panelValues = widget.getPanelValues();
        const userTitle = String(panelValues.chatTitle || "").trim();

        const result = await api.sendChat({
            message: text,
            agentId: session.agentId,
            model: session.model,
            history: session.getApiHistory(),
            sessionId: session.sessionId || "",
            title: userTitle,
            newChat: !session.sessionId,
            rag: Boolean(panelValues.ragCommit),
        });

        // Console drawer: tool-execution logs from this request (no bubbles).
        pushToolLogs(chat, result.tool_events);

        session.addAssistantMessage(result.reply);
        chat.addAssistantMessage(result.reply, session.agentName);
        session.setSessionId(result.session_id, result.title);
        chat.setSaveStatus(
            session.sessionId ? "Chat tracked on the server." : "Chat saved.",
            "ok"
        );
    } catch (error) {
        chat.addSystemMessage(`Sorry - that failed. ${error.message}`);
        chat.setSaveStatus(`Send failed: ${error.message}`, "error");
    } finally {
        chat.setWaiting(false);
    }
}

// ---- save handlers ----
/**
 * "Save chat" action: finalize the active chat on the server. The server
 * writes the transcript to data/chatlog/agent-text-records/<title>[-v].txt and
 * logs it. If you keep chatting after saving, the next save writes the next
 * version.
 *
 * If no subject was set in the panel, prompt for one so every chat ends up
 * meaningfully named (works the same for every agent).
 */
async function handleSaveAction(session, chat) {
    if (!session || !session.sessionId) {
        chat.setSaveStatus("No active chat to save yet.", "error");
        return;
    }

    try {
        const panelValues = widget.getPanelValues();
        let title = String(panelValues.chatTitle || "").trim();

        if (!title) {
            const subject = window.prompt(
                "Name this chat:",
                session.title !== "New chat" ? session.title : ""
            );
            if (subject !== null && subject.trim()) {
                title = subject.trim();
            }
        }

        const result = await api.endChat({
            title,
            rag: Boolean(widget.getPanelValues().ragCommit),
        });
        chat.setSaveStatus(
            result.saved
                ? `Saved: ${result.file} (v${result.version})`
                : `Save failed: ${result.error || "no active chat"}`,
            result.saved ? "ok" : "error"
        );
    } catch (error) {
        chat.setSaveStatus(`Save failed: ${error.message}`, "error");
    }
}

/** "Clear chat" action: wipe the session data and the rendered bubbles. */
function handleClearAction(session, chat) {
    session.newChat();
    chat.clearMessages();
    chat.setSaveStatus("Chat cleared.", "ok");
}

/**
 * Universal modal launcher for dynamic module actions
 * ("open_modal" / "qa_survey"). Builds an overlay card and hands the
 * body + a close() function to `builderFn`.
 * @returns {{ close: () => void }}
 */
function openModal(titleText, builderFn) {
    const overlay = document.createElement("div");
    overlay.className = "genessis-modal-overlay";

    const card = document.createElement("div");
    card.className = "genessis-modal-card";

    const header = document.createElement("div");
    header.className = "genessis-modal-header";
    const title = document.createElement("h2");
    title.textContent = titleText || "";
    const closeBtn = document.createElement("button");
    closeBtn.className = "genessis-modal-close";
    closeBtn.textContent = "\u2715";
    closeBtn.type = "button";
    closeBtn.setAttribute("aria-label", "Close");
    header.append(title, closeBtn);

    const body = document.createElement("div");
    body.className = "genessis-modal-body";

    card.append(header, body);
    overlay.appendChild(card);
    document.body.appendChild(overlay);

    const closeModal = () => overlay.remove();
    closeBtn.onclick = closeModal;
    overlay.addEventListener("click", (e) => {
        if (e.target === overlay) {
            closeModal();
        }
    });

    if (typeof builderFn === "function") {
        builderFn(body, closeModal);
    }
    return { close: closeModal };
}

// ---- go ----
boot();
