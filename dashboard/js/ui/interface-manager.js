// ============================================================
// ui/interface-manager.js - "Updates / Interface" card (config.html)
// ============================================================
// Drives the Modular Interface / update system from the browser
// (docs/01_IDEA_AND_ARCHITECTURE.md). Shows the live module catalog, the
// external archive, the trace-log tail and the known-good baseline; offers
// Apply / Snapshot / Restore actions, plus an explicitly-armable
// "module execution" panel (arbitrary code execution - OFF by default and
// gated both here in the UI and server-side via /api/interface/toggle-run).
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
        "Modular update modules (interface/updates/<domain>/) are discovered at server " +
        "startup and re-loaded through Apply. Snapshot publishes the current tree as the " +
        "known-good baseline; Restore rolls changed files back to it (dry-run first)."));

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

        const baseline = status.baseline || {};
        let driftText = "(no baseline)";
        let driftClass = "";
        if (baseline.drift) {
            const n = baseline.drift.modified;
            driftText = n === 0
                ? "up to date"
                : n + " file" + (n === 1 ? "" : "s") + " differ \u2014 run Snapshot to rebaseline";
            driftClass = n === 0 ? "ok" : "warn";
        }
        grid.appendChild(label("Baseline", baseline.folder || "", driftText, driftClass));

        const manifest = baseline.manifest;
        if (manifest) {
            grid.appendChild(label("Baseline manifest",
                (manifest.created || "?") + " \u00b7 " + (manifest.files ?? "?") + " files"));
        }

        const actions = el("div", "iface-actions");
        actions.appendChild(actionBtn("\u21bb Apply", "Reload update modules + regenerate docs", async (btn) => {
            return await applyInterface();
        }));
        actions.appendChild(actionBtn("\u2756 Snapshot", "Publish the current tree as the new baseline", async (btn) => {
            return await snapshotInterface();
        }));
        actions.appendChild(actionBtn("\u21a9 Restore (dry-run)",
            "Preview what a rollback would change", async (btn) => {
                return await restoreInterface({ dryRun: true });
            }));
        actions.appendChild(actionBtn("\u21a9 Restore (real)",
            "Back up + roll changed files back to the baseline",
            async (btn) => {
                if (!confirm("Restore the live tree from the baseline?\n\nChanged files are backed up to data/snapshots/pre_restore_backup/ first.")) {
                    return { cancelled: true };
                }
                return await restoreInterface({ dryRun: false });
            }));

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

    function actionBtn(text, title, run) {
        const btn = el("button", "btn", text);
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
        if (result.dry_run !== undefined) {
            return action + ": " + (result.modified === 0
                ? "clean - live tree matches the baseline."
                : result.modified + " file(s) would change" + (result.skipped ? ", " + result.skipped + " baseline-only" : "") + ".");
        }
        if (result.files !== undefined) {
            return action + ": baseline published with " + result.files + " files.";
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
            const mapping = currentCatalog;
            const mods = (mapping[domainSel.value] || []);
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