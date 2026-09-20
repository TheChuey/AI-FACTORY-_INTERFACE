// ============================================================
// ui/interface-manager.js - "Updates / Interface" card (config.html)
// ============================================================
// Drives the Modular Interface / update system from the browser: the live
// module catalog, the external archive, the trace-log tail and the MASTER
// COPY recovery (current-known-good-copy/). Actions: Apply (reload modules),
// "Save current state as master", and "Restore to master copy" - the latter
// guarded by a warning dialog. Plus an explicitly-armable "module execution"
// panel (arbitrary code execution - OFF by default and gated both here in
// the UI and server-side via /api/interface/toggle-run).
// ============================================================

import {
    getInterfaceStatus,
    applyInterface,
    snapshotInterface,
    restoreInterface,
    runInterface,
    setRunEnabled,
} from "../api/api.js";

export async function renderInterfaceSection(mount) {
    if (!mount) return;

    mount.appendChild(el("h2", "config-section-heading", "Updates / Interface"));
    mount.appendChild(el("p", "config-note",
        "Update modules (interface/updates/<domain>/) are discovered at server startup " +
        "and reloaded through Apply. 'Save current state as master' stores a known-good " +
        "master copy of the app; 'Restore to master copy' rolls every file back to it " +
        "(a backup of changed files is saved first, then docs are regenerated)."));

    const statusEl = el("div", "status-message");
    const statusBody = el("div", "");

    const refresh = el("button", "btn btn-small", "\u21bb refresh");
    refresh.type = "button";
    refresh.title = "Re-fetch the interface status from the server";
    refresh.addEventListener("click", async () => {
        refresh.disabled = true;
        await loadStatus();
        refresh.disabled = false;
    });

    mount.appendChild(refresh);
    mount.appendChild(statusBody);
    mount.appendChild(statusEl);

    // ---- run-module panel (gated) ----
    const runBlock = buildRunPanel();
    mount.appendChild(runBlock.root);

    async function loadStatus() {
        let status;
        try {
            status = await getInterfaceStatus();
        } catch (error) {
            setStatus(error.message, "warn");
            return;
        }
        renderStatus(status);
        runBlock.sync(status);
    }

    function renderStatus(status) {
        const box = el("div", "interface-status");
        const catalog = status.catalog || {};

        const grid = el("div", "iface-grid");
        grid.appendChild(label("Update modules", Object.keys(catalog).length
            ? Object.entries(catalog).map(([d, mods]) =>
                d + "/ -> " + ((mods && mods.length) ? mods.join(", ") : "(none)")).join("\n")
            : "(none loaded)"));

        const archived = status.archived || {};
        const archivedCount = Object.values(archived).reduce(
            (n, list) => n + (Array.isArray(list) ? list.length : 0), 0);
        grid.appendChild(label("Archive (retired modules)",
            status.archive_dir || "", archivedCount
                ? Object.entries(archived).map(([d, list]) =>
                    d + "/ -> " + (list.length ? list.join(", ") : "(none)")).join("\n")
                : "empty"));

        // Master copy status (server-side RestoreManager.status()).
        const baseline = status.baseline || {};
        let driftText = "(no master copy)";
        let driftClass = "warn";
        if (baseline.exists) {
            driftText = baseline.modified === 0
                ? "up to date"
                : baseline.modified + " file" + (baseline.modified === 1 ? "" : "s") +
                  " differ \u2014 run 'Save current state as master' to rebaseline";
            driftClass = baseline.modified === 0 ? "ok" : "warn";
        } else if (baseline.error) {
            driftText = baseline.error;
        }
        grid.appendChild(label("Master copy", baseline.folder || "", driftText, driftClass));
        if (baseline.exists && baseline.created) {
            grid.appendChild(label("Master manifest",
                baseline.created + " \u00b7 " + baseline.files + " files"));
        }

        const actions = el("div", "iface-actions");
        actions.appendChild(actionBtn("\u21bb Apply", "Reload update modules + regenerate docs", async (btn) => {
            return await applyInterface();
        }));
        actions.appendChild(actionBtn("\u2756 Save current state as master",
            "Publish the current tree as the known-good master copy", async (btn) => {
                return await snapshotInterface();
            }));
        actions.appendChild(actionBtn("\u21a9 Restore to master copy",
            "Roll every file back to the master copy (warning dialog first)",
            async (btn) => {
                const proceed = await confirmRestoreDialog();
                if (!proceed) return { cancelled: true };
                return await restoreInterface();
            },
            "btn-danger"));

        const trace = el("div", "iface-trace");
        trace.appendChild(el("div", "iface-trace-title", "Trace log tail (" + (status.trace_log || "") + ")"));
        const pre = el("pre", "iface-trace-pre",
            (status.trace_tail && status.trace_tail.length)
                ? status.trace_tail.join("\n")
                : "(trace log is empty)");
        trace.appendChild(pre);

        box.appendChild(grid);
        box.appendChild(actions);
        box.appendChild(trace);
        statusBody.replaceChildren(box);
    }

    function actionBtn(text, title, run, extraClass = "") {
        const btn = el("button", "btn" + (extraClass ? " " + extraClass : ""), text);
        btn.type = "button";
        btn.title = title;
        btn.addEventListener("click", async () => {
            btn.disabled = true;
            try {
                const result = await run(btn);
                if (result && result.cancelled) return;
                setStatus(summarise(text, result), "ok");
                await loadStatus();
            } catch (error) {
                setStatus(text + " failed \u2014 " + (error.message || error), "error");
            } finally {
                btn.disabled = false;
            }
        });
        return btn;
    }

    function summarise(action, result) {
        if (!result || typeof result !== "object") return action + " done.";
        if (result.files !== undefined) {
            return "Master copy published with " + result.files + " files.";
        }
        if (result.restored !== undefined) {
            const changed = result.restored + result.added;
            if (changed === 0) {
                return "Restore complete - the live tree already matched the master copy.";
            }
            return "Restore complete: " + result.restored + " overwritten, " +
                result.added + " added" +
                (result.backup_dir ? ". Backup at " + result.backup_dir : "") +
                ". Docs " + (result.docs_regenerated ? "regenerated." : "NOT regenerated.");
        }
        if (result.catalog) {
            return action + ": modules reloaded per domain \u2014 " +
                Object.entries(result.catalog).map(([d, m]) => d + ":" + m.length).join(", ") + ".";
        }
        return action + " done.";
    }

    function setStatus(text, kind) {
        statusEl.textContent = text;
        statusEl.className = "status-message " + (kind || "");
    }

    // ------------------------------------------------------------ run panel

    function buildRunPanel() {
        const root = el("div", "iface-run-panel");

        const toggleRow = el("div", "iface-run-toggle");
        const enable = document.createElement("input");
        enable.type = "checkbox";
        enable.id = "iface-run-enable";
        const enableLabel = el("label", "", "");
        enableLabel.htmlFor = "iface-run-enable";
        enableLabel.appendChild(enable);
        enableLabel.appendChild(document.createTextNode(" Enable module execution (arbitrary code)"));
        toggleRow.appendChild(enableLabel);
        root.appendChild(toggleRow);

        const pane = el("div", "iface-run-pane");
        pane.hidden = true;
        root.appendChild(pane);

        const fieldWrap = el("div", "iface-run-fields");
        const domainSel = el("select", "text-input");
        const moduleSel = el("select", "text-input");
        const fnInput = el("input", "text-input");
        fnInput.type = "text";
        fnInput.placeholder = "function name (e.g. secondary_engine_action)";
        const argsInput = el("input", "text-input");
        argsInput.type = "text";
        argsInput.placeholder = "args  [5]  (JSON array, optional)";
        const kwargsInput = el("input", "text-input");
        kwargsInput.type = "text";
        kwargsInput.placeholder = "kwargs  {\"x\": 2}  (JSON object, optional)";

        const runBtn = el("button", "btn btn-primary", "\u25b6 Run");
        runBtn.type = "button";

        const resultPre = el("pre", "iface-run-result", "");
        const runStatus = el("div", "status-message run-result-status");

        function fillDomains(domains) {
            domainSel.replaceChildren();
            domains.forEach((d) => {
                const opt = document.createElement("option");
                opt.value = d;
                opt.textContent = d;
                domainSel.appendChild(opt);
            });
        }
        function fillModules(modules) {
            moduleSel.replaceChildren();
            modules.forEach((name) => {
                const opt = document.createElement("option");
                opt.value = name;
                opt.textContent = name;
                moduleSel.appendChild(opt);
            });
        }

        domainSel.addEventListener("change", () => {
            const mods = (currentCatalog[domainSel.value] || []);
            fillModules(mods.length ? mods : ["(none)"]);
        });

        runBtn.addEventListener("click", async () => {
            runBtn.disabled = true;
            runStatus.textContent = "";
            try {
                const args = parseArg(argsInput.value, []);
                const kwargs = parseArg(kwargsInput.value, {});
                const result = await runInterface({
                    domain: domainSel.value,
                    module: moduleSel.value,
                    function: fnInput.value.trim(),
                    args,
                    kwargs,
                });
                resultPre.textContent = formatResult(result);
                runStatus.textContent = "OK - returned a result (see trace in server console / data/interface_trace.log).";
                runStatus.className = "status-message ok";
            } catch (error) {
                runStatus.textContent = error.message || String(error);
                runStatus.className = "status-message error";
            } finally {
                runBtn.disabled = false;
            }
        });

        [domainSel, moduleSel, fnInput, argsInput, kwargsInput].forEach((node) => {
            fieldWrap.appendChild(labeledWrap(node));
        });
        pane.appendChild(fieldWrap);
        pane.appendChild(runBtn);
        pane.appendChild(runStatus);
        pane.appendChild(resultPre);

        let currentCatalog = {};

        enable.addEventListener("change", async () => {
            try {
                await setRunEnabled(enable.checked);
                pane.hidden = !enable.checked;
                runStatus.textContent = enable.checked
                    ? "Module execution is ON for this server process. /api/interface/run is now armed."
                    : "Module execution is OFF.";
                runStatus.className = "status-message " + (enable.checked ? "ok" : "warn");
            } catch (error) {
                enable.checked = !enable.checked;
                runStatus.textContent = error.message || String(error);
                runStatus.className = "status-message error";
            }
        });

        // sync() is called after every status fetch.
        return {
            root,
            sync(status) {
                currentCatalog = status.catalog || {};
                const domains = Object.keys(currentCatalog);
                if (domains.length && !domainSel.options.length) {
                    fillDomains(domains);
                    fillModules(currentCatalog[domains[0]] || ["(none)"]);
                }
                const serverEnabled = Boolean(status.run_enabled);
                if (enable.checked !== serverEnabled) {
                    enable.checked = serverEnabled;
                }
                pane.hidden = !serverEnabled;
            },
        };
    }
}

// -------------------------------------------------- confirm-restore dialog

function confirmRestoreDialog() {
    ensureModalStyles();
    return new Promise((resolve) => {
        const overlay = el("div", "iface-modal-overlay");
        const dialog = el("div", "iface-modal");
        dialog.appendChild(el("h3", "", "Restore the application?"));

        const warn = el("div", "iface-modal-warn",
            "This will restore the system to its original parameters. Every " +
            "application file will be replaced with the saved master copy, and " +
            "any changes made since the master was saved will be overwritten.\n\n" +
            "Chats, telemetry, settings and other runtime data are NOT touched. " +
            "A backup of every overwritten file is saved before restoring, and " +
            "the docs are regenerated afterwards.");
        dialog.appendChild(warn);

        const actions = el("div", "iface-modal-actions");
        const cancelBtn = el("button", "btn", "Cancel");
        const restoreBtn = el("button", "btn btn-danger", "Restore now");

        function close(result) {
            overlay.remove();
            return resolve(result);
        }
        restoreBtn.addEventListener("click", () => close(true));
        cancelBtn.addEventListener("click", () => close(false));
        overlay.addEventListener("click", (event) => {
            if (event.target === overlay) close(false);
        });
        document.addEventListener("keydown", function esc(e) {
            if (e.key === "Escape") {
                document.removeEventListener("keydown", esc);
                close(false);
            }
        });

        actions.appendChild(cancelBtn);
        actions.appendChild(restoreBtn);
        dialog.appendChild(actions);
        overlay.appendChild(dialog);
        document.body.appendChild(overlay);
    });
}

function ensureModalStyles() {
    if (document.getElementById("iface-modal-styles")) return;
    const style = document.createElement("style");
    style.id = "iface-modal-styles";
    style.textContent = `
        .iface-modal-overlay {
            position: fixed; inset: 0; z-index: 1000;
            display: flex; align-items: center; justify-content: center;
            background: rgba(0, 0, 0, 0.55);
        }
        .iface-modal {
            background: var(--color-surface, #ffffff);
            color: var(--color-text, #1c2024);
            border: 1px solid var(--color-border, #e1e5e8);
            border-radius: 10px; padding: 18px 22px;
            max-width: 460px; width: calc(100vw - 40px);
            box-shadow: 0 18px 50px rgba(0, 0, 0, 0.45);
        }
        .iface-modal h3 { margin: 0 0 10px; font-size: 16px; }
        .iface-modal-warn {
            white-space: pre-wrap; font-size: 13px; line-height: 1.55;
            color: var(--color-text, #1c2024); opacity: 0.85;
        }
        .iface-modal-actions {
            display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px;
        }
        .btn-danger {
            background: #b91c1c; border-color: #991b1b; color: #ffffff;
        }
        .btn-danger:hover:not(:disabled) { background: #dc2626; }
        .btn-danger:disabled { opacity: 0.65; }
    `;
    document.head.appendChild(style);
}

// ---------------------------------------------------------------- helpers

function parseArg(raw, fallback, flag) {
    const value = String(raw || "").trim();
    if (!value) return fallback;
    try {
        return JSON.parse(value);
    } catch (_) {
        throw new Error((flag || "Arguments") + " must be valid JSON: " + value);
    }
}

function formatResult(result) {
    if (!result || typeof result !== "object") return String(result);
    return JSON.stringify(result, null, 2);
}

function labeledWrap(input) {
    const wrap = el("label", "iface-run-field");
    const name = input.placeholder
        ? String(input.placeholder).split(" ")[0]
        : (input.id || "value");
    wrap.appendChild(el("span", "iface-run-field-label", name));
    wrap.appendChild(input);
    return wrap;
}

function label(heading, body, sub = "", subClass = "") {
    const wrap = el("div", "iface-grid-item");
    wrap.appendChild(el("div", "iface-item-label", heading));
    wrap.appendChild(el("div", "iface-item-body", body));
    if (sub) {
        const s = el("div", "iface-item-sub " + subClass, sub);
        wrap.appendChild(s);
    }
    return wrap;
}

function el(tag, className = "", text = "") {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text) node.textContent = text;
    return node;
}