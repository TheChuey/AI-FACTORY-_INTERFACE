// ============================================================
// ui/interface-indicator.js - HEADER PILL: "N update modules"
// ============================================================
// A tiny, quiet status chip for the Modular Interface / update system
// (docs/01_IDEA_AND_ARCHITECTURE.md). Fetches /api/interface/status once;
// when the server is old (no endpoint) or has nothing to show, it renders
// nothing instead of erroring. Clicking it jumps to the "Updates / Interface"
// card on the Settings page.
//
//   index.html  -> renderInterfaceIndicator({ container: parent,
//                                             onMesh: true })
//   config.html -> renderInterfaceIndicator({ container: parent })
// ============================================================

import { getInterfaceStatus } from "../api/api.js";

export async function renderInterfaceIndicator({ container = null, onMesh = false } = {}) {
    let status;
    try {
        status = await getInterfaceStatus();
    } catch (_) {
        return null; // server predates /api/interface/* - stay silent
    }

    const catalog = status.catalog || {};
    const total = Object.keys(catalog).reduce(
        (n, domain) => n + (Array.isArray(catalog[domain]) ? catalog[domain].length : 0),
        0
    );
    if (total === 0) return null;

    const driftCount = status.baseline && status.baseline.drift
        ? Number(status.baseline.drift.modified) || 0
        : 0;
    const runEnabled = Boolean(status.run_enabled);

    const pill = document.createElement("a");
    pill.href = "/static/config.html#interface-section";
    pill.className = "interface-indicator" + (onMesh ? " on-mesh" : "");
    pill.title = "Interface / update modules - open on the Settings page";

    const dot = document.createElement("span");
    dot.className = "dot" + (driftCount > 0 ? " drift" : "");
    pill.appendChild(dot);

    const label = document.createElement("span");
    label.textContent = total + " update" + (total === 1 ? "" : "s");
    pill.appendChild(label);

    if (runEnabled) {
        const run = document.createElement("span");
        run.className = "run-state";
        run.textContent = "\u2022 on";
        pill.appendChild(run);
    }

    if (container) {
        container.appendChild(pill);
    }
    return pill;
}