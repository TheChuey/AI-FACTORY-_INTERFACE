// ============================================================
// ui/agent-editor.js - PER-AGENT CONFIGURATION EDITOR (config page)
// ============================================================
// Renders one collapsible card per discovered agent on config.html.
// Each card consolidates EVERYTHING about that single agent in one place:
//   - Configuration:  name / description / mode / model / tools
//   - Behavior:       the agent.md markdown (editable here)
//   - Tests:          that agent's saved chat tests + an inline runner
//
// Data comes from /api/agents/{id}/config and is written back through
// the same endpoint (each agent's files are the source of truth).
// ============================================================

import { getAgentConfig, saveAgentConfig, sendChat } from "../api/api.js";

/** Render one card per agent into `mountEl`. Config is fetched lazily the
 *  first time a card is expanded, so the page stays fast with many agents. */
export async function renderAgentEditors({ mountEl, agents = [], models = [], toolIds = [] }) {
    const heading = el("h2", "config-section-heading", "Agents");
    heading.id = "agents";
    mountEl.appendChild(heading);

    const intro = el("p", "config-note",
        "One place per agent: metadata, tools, model, behavior (agent.md) and its chat tests. " +
        "Changes are written straight to the agent's folder under engine/agent_library/."
    );
    mountEl.appendChild(intro);

    const cards = el("div", "agent-editor-cards");
    mountEl.appendChild(cards);

    agents.forEach((agent) => {
        cards.appendChild(buildCard({ agent, models, toolIds }));
    });
}

// ----------------------------------------------------------------
// CARD SHELL
// ----------------------------------------------------------------

function buildCard({ agent, models, toolIds }) {
    const card = document.createElement("section");
    card.className = "panel agent-editor-card";
    card.id = "agent-" + agent.id;

    const header = document.createElement("header");
    header.className = "agent-editor-header";
    header.style.cssText =
        "display:flex;align-items:center;gap:10px;cursor:pointer;user-select:none;" +
        "padding:14px 16px;border-bottom:1px solid var(--color-border,#e1e5e8);";

    const chevron = el("span", "agent-editor-chevron", "v");
    chevron.style.cssText = "font-size:11px;transition:transform .15s ease;color:var(--color-text-muted,#64748b);font-weight:bold;";

    const nameEl = el("span", "agent-editor-name", agent.name);
    nameEl.style.cssText = "font-weight:700;font-size:15px;flex:1;";
    nameEl.dataset.role = "name";

    const badge = el("span", "badge", agent.mode || "chat");
    badge.dataset.role = "mode-badge";

    const chatLink = document.createElement("a");
    chatLink.className = "btn btn-secondary btn-small";
    chatLink.textContent = "Chat";
    chatLink.href = "/static/chat.html?agent=" + encodeURIComponent(agent.id);
    chatLink.target = "_blank";
    chatLink.rel = "noopener";

    header.append(chevron, nameEl, badge, chatLink);
    card.appendChild(header);

    const body = document.createElement("div");
    body.className = "agent-editor-body";
    body.style.cssText = "padding:14px 16px;display:none;";
    card.appendChild(body);

    let expanded = false;
    header.addEventListener("click", async (event) => {
        if (event.target.closest("a")) return; // links keep working inside the header
        expanded = !expanded;
        body.style.display = expanded ? "" : "none";
        chevron.style.transform = expanded ? "rotate(0deg)" : "rotate(-90deg)";
        if (expanded && !loaded) {
            await load();
        }
    });
    chevron.style.transform = "rotate(-90deg)";

    let loaded = false;
    let state = null;

    async function load() {
        try {
            state = await getAgentConfig(agent.id);
            if (state.agent && state.agent.name) {
                nameEl.textContent = state.agent.name;
                if (badge.dataset.role === "mode-badge") baitBadge(badge, state.agent.mode);
            }
            renderBody();
            loaded = true;
        } catch (error) {
            body.replaceChildren();
            body.appendChild(el("p", "status-message error", "Could not load agent config: " + error.message));
        }
    }

    function baitBadge(badgeNode, mode) {
        badgeNode.textContent = mode || badgeNode.textContent;
    }

    function renderBody() {
        body.replaceChildren();

        const metaTab = el("div", "agent-editor-tab", "Configuration");
        const mdTab = el("div", "agent-editor-tab", "Behavior (agent.md)");
        const testsTab = el("div", "agent-editor-tab", "Tests");
        metaTab.dataset.tab = "meta";
        mdTab.dataset.tab = "md";
        testsTab.dataset.tab = "tests";
        const tabbar = el("div", "agent-editor-tabs");
        tabbar.append(metaTab, mdTab, testsTab);
        body.appendChild(tabbar);

        const paneMeta = buildMetaPane(state, models, toolIds, () => refreshNameAndRefresh());
        const paneMd = buildMarkdownPane(state);
        const paneTests = buildTestsPane(state);
        paneMeta.classList.add("active");

        const panes = el("div", "agent-editor-panes");
        panes.append(paneMeta, paneMd, paneTests);
        body.appendChild(panes);

        tabbar.addEventListener("click", (event) => {
            const tab = event.target.closest("[data-tab]");
            if (!tab) return;
            tabbar.querySelectorAll("[data-tab]").forEach((t) => t.classList.toggle("active", t === tab));
            panes.querySelectorAll(".agent-editor-pane").forEach((p) => p.classList.toggle("active", p.dataset.pane === tab.dataset.tab));
        });
    }

    function refreshNameAndRefresh() {
        if (state && state.agent && state.agent.name) {
            nameEl.textContent = state.agent.name;
        }
    }

    return card;
}

// ----------------------------------------------------------------
// CONFIGURATION PANE (metadata + model + tools)
// ----------------------------------------------------------------

function buildMetaPane(state, models, toolIds, onSaved) {
    const pane = el("div", "agent-editor-pane");
    pane.dataset.pane = "meta";

    const meta = state.meta || {};

    const idField = fieldText("agent-editor-id", "Agent id", String(meta.id || ""), true);
    const nameField = fieldText("", "Name", String(meta.name || ""));
    nameField.querySelector("input").dataset.field = "name";
    const descField = fieldArea("", "Description", String(meta.description || ""));
    descField.querySelector("textarea").dataset.field = "description";

    // Mode select
    const modeField = document.createElement("label");
    modeField.className = "field";
    modeField.appendChild(el("span", "", "Mode"));
    const modeSelect = document.createElement("select");
    modeSelect.dataset.field = "mode";
    [["chat", "Chat (no tools)"], ["agent", "Agent (tool loop)"]].forEach(([value, label]) => {
        const o = new Option(label, value);
        o.selected = (meta.mode || "chat") === value;
        modeSelect.appendChild(o);
    });
    modeField.appendChild(modeSelect);

    // Model select
    const modelField = document.createElement("label");
    modelField.className = "field";
    modelField.appendChild(el("span", "", "Model"));
    const modelSelect = document.createElement("select");
    modelSelect.dataset.field = "model";
    const noneOpt = new Option("(server default)", "");
    noneOpt.selected = !meta.model;
    modelSelect.appendChild(noneOpt);
    (models || []).forEach((m) => {
        const o = new Option(m.name, m.id);
        o.selected = meta.model === m.id;
        modelSelect.appendChild(o);
    });
    modelField.appendChild(modelSelect);

    // Tools (only when the agent uses the standard list format)
    let toolsField = null;
    const toolsRaw = meta.tools;
    const toolsEditable = Array.isArray(toolsRaw);
    if (toolsEditable) {
        toolsField = document.createElement("fieldset");
        toolsField.className = "agent-editor-tools";
        toolsField.appendChild(el("legend", "", "Tools"));
        const grid = el("div", "agent-editor-tools-grid");
        (toolIds || []).forEach((tid) => {
            const label = document.createElement("label");
            label.className = "field field-toggle";
            label.style.borderBottom = "none";
            const cb = document.createElement("input");
            cb.type = "checkbox";
            cb.value = tid;
            cb.checked = (toolsRaw || []).includes(tid);
            label.appendChild(el("span", "", tid));
            label.appendChild(cb);
            label.appendChild(el("span", "field-switch", ""));
            grid.appendChild(label);
        });
        toolsField.appendChild(grid);
        if (!(toolIds || []).length) {
            toolsField.appendChild(el("p", "config-note",
                "Tool list could not be loaded - restart the server if it was just updated."));
        }
    }

    const wrapCols = document.createElement("div");
    wrapCols.className = "agent-editor-fields";
    wrapCols.append(idField, nameField, descField, modeField, modelField);
    if (toolsField) wrapCols.appendChild(toolsField);

    const actions = el("div", "section-actions");
    const saveBtn = el("button", "btn btn-primary", "Save configuration");
    const statusEl = el("span", "config-note", "");
    actions.append(saveBtn, statusEl);

    saveBtn.addEventListener("click", async () => {
        const payloadMeta = {
            id: meta.id || state.agent.id,
            name: valueOf("[data-field=name]"),
            description: valueOf("[data-field=description]"),
            mode: valueOf("[data-field=mode]"),
            model: valueOf("[data-field=model]") || "",
        };
        if (toolsEditable) {
            const checked = Array.from(pane.querySelectorAll(".agent-editor-tools input[type=checkbox]:checked"))
                .map((cb) => cb.value);
            payloadMeta.tools = checked;
        }
        saveBtn.disabled = true;
        try {
            const updated = await saveAgentConfig(state.agent.id, { meta: payloadMeta });
            state = updated;
            onSaved();
            statusEl.textContent = "Configuration saved.";
            statusEl.style.color = "var(--color-success,#16803c)";
            refreshPaneFromState();
        } catch (error) {
            statusEl.textContent = error.message;
            statusEl.style.color = "var(--color-danger,#b91c1c)";
        } finally {
            saveBtn.disabled = false;
        }
    });

    pane.append(wrapCols, actions);

    function valueOf(selector) {
        const node = pane.querySelector(selector);
        return node ? node.value : "";
    }

    function refreshPaneFromState() {
        const fresh = buildMetaPane(state, models, toolIds, onSaved);
        fresh.classList.add("active");
        pane.replaceWith(fresh);
    }

    return pane;
}

// ----------------------------------------------------------------
// BEHAVIOR PANE (agent.md)
// ----------------------------------------------------------------

function buildMarkdownPane(state) {
    const pane = el("div", "agent-editor-pane");
    pane.dataset.pane = "md";

    const note = el("p", "config-note",
        "Behavior prose for this agent. Sections start with \"##\" (## role, ## purpose, ## boundaries, ...). " +
        "Saved verbatim to agent.md."
    );
    pane.appendChild(note);

    const textarea = document.createElement("textarea");
    textarea.className = "agent-editor-markdown";
    textarea.spellcheck = false;
    textarea.rows = 14;
    textarea.value = state.markdown || "";

    const actions = el("div", "section-actions");
    const saveBtn = el("button", "btn btn-primary", "Save agent.md");
    const statusEl = el("span", "config-note", "");
    actions.append(saveBtn, statusEl);

    saveBtn.addEventListener("click", async () => {
        saveBtn.disabled = true;
        try {
            const updated = await saveAgentConfig(state.agent.id, { markdown: textarea.value });
            state = updated;
            statusEl.textContent = "agent.md saved.";
            statusEl.style.color = "var(--color-success,#16803c)";
        } catch (error) {
            statusEl.textContent = error.message;
            statusEl.style.color = "var(--color-danger,#b91c1c)";
        } finally {
            saveBtn.disabled = false;
        }
    });

    pane.append(textarea, actions);
    return pane;
}

// ----------------------------------------------------------------
// TESTS PANE (this agent's tests, per-agent storage)
// ----------------------------------------------------------------

function buildTestsPane(state) {
    const pane = el("div", "agent-editor-pane");
    pane.dataset.pane = "tests";

    const intro = el("p", "config-note",
        "Automated tests that run against THIS agent via /api/chat. Saved to the agent's own agent.json."
    );
    pane.appendChild(intro);

    const toolbar = el("div", "chat-tests-toolbar");
    const enableBtn = el("button", "btn btn-secondary btn-small", "Enable all");
    const disableBtn = el("button", "btn btn-secondary btn-small", "Disable all");
    toolbar.append(enableBtn, disableBtn);
    pane.appendChild(toolbar);

    const statusEl = el("p", "config-note", "");
    statusEl.className = "test-run-status";
    statusEl.style.cssText = "font-size:12px;font-weight:600;margin:0 0 6px;min-height:16px;";
    const resultsEl = document.createElement("div");
    resultsEl.className = "test-run-results";
    resultsEl.style.marginBottom = "10px";
    resultsEl.style.display = "none";

    const listEl = el("div", "agent-test-list");
    pane.appendChild(listEl);

    const hr = document.createElement("hr");
    hr.style.cssText = "border:none;border-top:1px dashed var(--color-border,#e1e5e8);margin:14px 0;";
    pane.appendChild(hr);

    const builderTitle = el("p", "", "Add a new test");
    builderTitle.style.cssText = "font-weight:700;margin:0 0 10px;font-size:12px;color:var(--color-text-muted,#64748b);text-transform:uppercase;letter-spacing:.4px;";
    pane.appendChild(builderTitle);
    pane.appendChild(buildStepBuilder(state, listEl, statusEl));

    const hr2 = document.createElement("hr");
    hr2.style.cssText = "border:none;border-top:1px dashed var(--color-border,#e1e5e8);margin:14px 0;";
    pane.appendChild(hr2);

    const runnerWrap = el("div", "agent-test-runner");
    const runBtn = el("button", "btn btn-primary btn-small", "Run tests for " + state.agent.name);
    const stopBtn = el("button", "btn btn-secondary btn-small", "Stop");
    stopBtn.style.marginLeft = "6px";
    stopBtn.style.display = "none";
    runnerWrap.append(statusEl, resultsEl, runBtn, stopBtn);
    pane.appendChild(runnerWrap);

    const runState = {
        running: false,
        cancelled: false,
        results: [],
        sessionId: "",
        history: [],
    };

    // Enable/disable all + list
    enableBtn.addEventListener("click", () => setAll(true));
    disableBtn.addEventListener("click", () => setAll(false));

    function setAll(enabled) {
        state.tests.forEach((t) => { if (t) t.enabled = enabled; });
        persist();
    }

    async function persist() {
        try {
            const updated = await saveAgentConfig(state.agent.id, { tests: state.tests });
            state.tests = updated.tests || [];
            renderList(listEl, state, statusEl, renderResults);
        } catch (error) {
            statusEl.textContent = error.message;
            statusEl.style.color = "var(--color-danger,#b91c1c)";
        }
    }

    function renderResults() {
        resultsEl.replaceChildren();
        if (runState.results.length) {
            resultsEl.style.display = "";
            runState.results.forEach((r) => {
                const row = document.createElement("div");
                row.style.cssText = "display:flex;justify-content:space-between;gap:8px;padding:4px 0;font-size:12px;border-bottom:1px dashed var(--color-border,#e1e5e8);";
                const name = el("span", "", r.name);
                name.style.cssText = "overflow:hidden;white-space:nowrap;text-overflow:ellipsis;";
                name.title = r.detail || r.name;
                const verdict = el("span", "", r.status);
                verdict.style.cssText = "flex:0 0 auto;font-weight:700;color:" +
                    (r.ok ? "var(--color-success,#16803c)" : "var(--color-danger,#b91c1c)");
                verdict.title = r.detail || r.status;
                row.append(name, verdict);
                resultsEl.appendChild(row);
            });
        } else {
            resultsEl.style.display = "none";
        }
    }

    function renderStatus() {
        const failed = runState.results.some((r) => !r.ok);
        const errored = runState.results.some((r) => r.status === "Error");
        if (runState.running) {
            statusEl.textContent = "Running...  (" + runState.results.length + " done)";
            statusEl.style.color = "var(--color-primary,#075985)";
        } else if (runState.status) {
            statusEl.textContent = runState.status;
            statusEl.style.color = errored ? "var(--color-danger,#b91c1c)" : (failed ? "#b45309" : "var(--color-success,#16803c)");
        }
    }

    runBtn.addEventListener("click", () => runTests());
    stopBtn.addEventListener("click", () => { runState.cancelled = true; stopBtn.disabled = true; });

    async function runTests() {
        if (runState.running) return;
        const tests = enabledTests(state.tests);
        if (!tests.length) {
            runState.status = "No enabled tests for this agent.";
            renderStatus();
            return;
        }
        runState.running = true;
        runState.cancelled = false;
        runState.results = [];
        runState.sessionId = "";
        runState.history = [];
        runBtn.disabled = true;
        runBtn.textContent = "Running...";
        stopBtn.style.display = "";
        stopBtn.disabled = false;
        renderResults();
        renderStatus();

        try {
            for (const test of tests) {
                if (runState.cancelled) break;
                const script = testScript(test);
                const expectations = Array.isArray(test.expectations) ? test.expectations : [];
                let finalReply = null;
                let failedStep = null;
                let errorMsg = "";

                for (let index = 0; index < script.length; index++) {
                    if (runState.cancelled) break;
                    try {
                        const result = await sendChat({
                            message: script[index],
                            agentId: state.agent.id,
                            model: "",
                            history: runState.history,
                            sessionId: runState.sessionId,
                            title: test.name,
                            newChat: !runState.sessionId,
                        });
                        if (!runState.sessionId) {
                            runState.sessionId = result.session_id || "";
                        }
                        finalReply = result.reply || "";
                        runState.history.push({ role: "user", content: script[index] });
                        runState.history.push({ role: "assistant", content: finalReply });
                        const expected = expectations[index];
                        if (expected) {
                            const check = checkExpectation(finalReply, expected);
                            if (!check.ok) { failedStep = check.message + " (step " + (index + 1) + ")"; break; }
                        }
                    } catch (error) {
                        errorMsg = error.message;
                        finalReply = null;
                        break;
                    }
                }

                if (errorMsg) {
                    runState.results.push({ id: test.id, name: test.name, ok: false, status: "Error", detail: errorMsg });
                } else if (failedStep) {
                    runState.results.push({ id: test.id, name: test.name, ok: false, status: "Failed", detail: failedStep });
                } else if (runState.cancelled) {
                    runState.results.push({ id: test.id, name: test.name, ok: false, status: "Stopped", detail: "Run stopped." });
                } else {
                    let verdict = { ok: true, status: "Passed", detail: "" };
                    if (test.expectedResult) {
                        const check = checkExpectation(finalReply, test.expectedResult);
                        if (!check.ok) verdict = { ok: false, status: "Failed", detail: check.message };
                    }
                    runState.results.push({ id: test.id, name: test.name, ...verdict });
                }
                renderResults();
                renderStatus();
            }
        } finally {
            runState.running = false;
            runBtn.disabled = false;
            runBtn.textContent = "Run tests for " + state.agent.name;
            stopBtn.style.display = "none";
            const passed = runState.results.filter((r) => r.ok).length;
            const errored = runState.results.some((r) => r.status === "Error");
            runState.status = runState.cancelled
                ? "Stopped after " + runState.results.length + "/" + tests.length + " tests."
                : (errored ? "Errored - " + passed + "/" + runState.results.length + " passed"
                           : passed + "/" + runState.results.length + " passed" + (runState.results.length ? "" : " (no tests)"));
            renderResults();
            renderStatus();
        }
    }

    renderList(listEl, state, statusEl, renderResults);
    return pane;
}

// ----------------------------------------------------------------
// TEST LIST + STEP BUILDER (per-agent)
// ----------------------------------------------------------------

function renderList(container, state, statusEl, onRender) {
    container.replaceChildren();
    const tests = state.tests || [];

    if (!tests.length) {
        container.appendChild(el("p", "config-note", "No tests yet. Add one below."));
        return;
    }

    tests.forEach((test) => {
        const row = document.createElement("div");
        row.className = "test-row";
        row.style.cssText = "display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px dashed var(--color-border,#e1e5e8);font-size:13px;";

        const toggle = document.createElement("input");
        toggle.type = "checkbox";
        toggle.checked = test.enabled !== false;
        toggle.title = "Toggle test enabled";
        toggle.addEventListener("change", async () => {
            test.enabled = toggle.checked;
            try {
                const updated = await saveAgentConfig(state.agent.id, { tests: state.tests });
                state.tests = updated.tests || [];
            } catch (error) {
                statusEl.textContent = error.message;
                statusEl.style.color = "var(--color-danger,#b91c1c)";
            }
            onRender();
        });
        row.appendChild(toggle);

        const name = el("span", "", test.name || test.id);
        name.style.cssText = "flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;";
        name.title = test.name || test.id;
        row.appendChild(name);

        const steps = getSteps(test);
        const badge = el("span", "badge", steps.length + " step" + (steps.length !== 1 ? "s" : ""));
        badge.style.cssText = "font-size:10px;";
        row.appendChild(badge);

        const del = document.createElement("button");
        del.type = "button";
        del.className = "btn btn-small";
        del.textContent = "x";
        del.title = "Delete this test";
        del.style.cssText = "padding:2px 7px;font-size:11px;color:var(--color-danger,#b91c1c);border-color:var(--color-danger,#b91c1c);";
        del.addEventListener("click", async () => {
            state.tests = (state.tests || []).filter((t) => t.id !== test.id);
            try {
                const updated = await saveAgentConfig(state.agent.id, { tests: state.tests });
                state.tests = updated.tests || [];
            } catch (error) {
                statusEl.textContent = error.message;
                statusEl.style.color = "var(--color-danger,#b91c1c)";
            }
            renderList(container, state, statusEl, onRender);
            onRender();
        });
        row.appendChild(del);

        container.appendChild(row);
    });
}

function buildStepBuilder(state, listEl, statusEl) {
    const wrapper = document.createElement("div");

    const inputRow = document.createElement("div");
    inputRow.style.cssText = "display:flex;gap:8px;margin-bottom:8px;";

    const stepInput = document.createElement("input");
    stepInput.type = "text";
    stepInput.placeholder = "Type a message / question for the agent...";
    stepInput.style.cssText = "flex:1;padding:7px 10px;border:1px solid var(--color-border,#e1e5e8);border-radius:6px;font:inherit;font-size:13px;color:var(--color-text,#0f172a);background:var(--color-surface,#fff);";

    const addBtn = el("button", "btn btn-secondary btn-small", "+ Add Step");
    inputRow.append(stepInput, addBtn);
    wrapper.appendChild(inputRow);

    const draftSteps = [];
    const draftList = document.createElement("div");
    draftList.style.cssText = "min-height:32px;padding:7px 9px;border:1px dashed var(--color-border-strong,#cbd5e1);border-radius:7px;background:var(--color-surface-alt,#fafafa);font-size:12px;margin-bottom:10px;color:var(--color-text-faint,#94a3b8);font-style:italic;";
    draftList.textContent = "No steps yet.";
    wrapper.appendChild(draftList);

    function refreshDraft() {
        draftList.replaceChildren();
        draftList.style.fontStyle = "";
        draftList.style.color = "";
        if (!draftSteps.length) {
            draftList.style.fontStyle = "italic";
            draftList.style.color = "var(--color-text-faint,#94a3b8)";
            draftList.textContent = "No steps yet.";
            return;
        }
        draftSteps.forEach((step, i) => {
            const row = document.createElement("div");
            row.style.cssText = "display:flex;gap:7px;padding:3px 0;" + (i > 0 ? "border-top:1px dashed var(--color-border,#e1e5e8);" : "");
            const idx = el("span", "", (i + 1) + ".");
            idx.style.cssText = "color:var(--color-text-faint,#94a3b8);min-width:18px;text-align:right;font-weight:600;";
            row.append(idx, el("span", "", step));
            draftList.appendChild(row);
        });
    }

    addBtn.addEventListener("click", () => {
        const val = stepInput.value.trim();
        if (!val) return;
        draftSteps.push(val);
        stepInput.value = "";
        stepInput.focus();
        refreshDraft();
    });

    stepInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); addBtn.click(); }
    });

    const actionRow = document.createElement("div");
    actionRow.style.cssText = "display:flex;gap:8px;flex-wrap:wrap;align-items:center;";
    const commitBtn = el("button", "btn btn-primary btn-small", "Commit as Test");
    const clearBtn = el("button", "btn btn-secondary btn-small", "Clear Steps");
    actionRow.append(commitBtn, clearBtn);
    wrapper.appendChild(actionRow);

    const localStatus = el("span", "config-note", "");
    localStatus.style.cssText = "font-size:11px;";
    wrapper.appendChild(localStatus);

    clearBtn.addEventListener("click", () => {
        draftSteps.length = 0;
        refreshDraft();
    });

    commitBtn.addEventListener("click", async () => {
        if (!draftSteps.length) {
            localStatus.textContent = "Add at least one step first.";
            return;
        }
        const name = draftSteps[0].length > 60
            ? draftSteps[0].slice(0, 60).trimEnd() + "..."
            : draftSteps[0];

        const newTest = {
            id: "custom-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 6),
            name,
            steps: [...draftSteps],
            expectedResult: { mode: "type", value: "nonEmpty" },
            enabled: true,
        };

        state.tests = (state.tests || []).concat([newTest]);
        try {
            const updated = await saveAgentConfig(state.agent.id, { tests: state.tests });
            state.tests = updated.tests || [];
            draftSteps.length = 0;
            refreshDraft();
            localStatus.textContent = 'Test "' + name + '" saved.';
            setTimeout(() => { localStatus.textContent = ""; }, 3500);
            renderList(listEl, state, statusEl);
        } catch (error) {
            localStatus.textContent = "Save failed: " + error.message;
        }
    });

    return wrapper;
}

// ----------------------------------------------------------------
// HELPERS
// ----------------------------------------------------------------

function enabledTests(tests) {
    return (tests || []).filter((t) => t && t.enabled !== false);
}

function getSteps(test) {
    if (Array.isArray(test.steps) && test.steps.length) return test.steps;
    return String(test.input || "").split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
}

function testScript(test) {
    if (Array.isArray(test.steps) && test.steps.length) {
        return test.steps.map((step) => String(step).trim()).filter(Boolean);
    }
    return String(test.input || "").split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
}

function checkExpectation(reply, expectation) {
    const mode = expectation.mode || (typeof expectation === "string" ? "string" : "regex");
    const value = typeof expectation === "string" ? expectation : expectation.value;
    const text = String(reply || "");

    switch (mode) {
        case "string": {
            if (text.toLowerCase().includes(String(value).toLowerCase())) return { ok: true };
            return { ok: false, message: `Expected "${value}" in reply.` };
        }
        case "regex": {
            try {
                if (new RegExp(value, "i").test(text)) return { ok: true };
                return { ok: false, message: `Reply did not match "${value}".` };
            } catch (_) {
                return { ok: false, message: `Bad regex "${value}".` };
            }
        }
        case "type": {
            if (value === "nonEmpty") {
                if (text.trim()) return { ok: true };
                return { ok: false, message: "Reply was empty." };
            }
            if (value === "number") {
                const digits = text.replace(/[^\d.-]/g, "");
                if (digits && !Number.isNaN(Number(digits))) return { ok: true };
                return { ok: false, message: "Reply was not a number." };
            }
            return { ok: false, message: `Unknown type check "${value}".` };
        }
        default:
            return { ok: false, message: `Unknown mode "${mode}".` };
    }
}

function fieldText(id, label, value, readonly = false) {
    const wrap = document.createElement("label");
    wrap.className = "field";
    wrap.appendChild(el("span", "", label));
    const input = document.createElement("input");
    input.type = "text";
    if (id) input.id = id;
    input.value = value || "";
    if (readonly) input.readOnly = true;
    wrap.appendChild(input);
    return wrap;
}

function fieldArea(id, label, value) {
    const wrap = document.createElement("label");
    wrap.className = "field";
    wrap.appendChild(el("span", "", label));
    const area = document.createElement("textarea");
    if (id) area.id = id;
    area.rows = 3;
    area.value = value || "";
    wrap.appendChild(area);
    return wrap;
}

function el(tag, className = "", text = "") {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text) node.textContent = text;
    return node;
}