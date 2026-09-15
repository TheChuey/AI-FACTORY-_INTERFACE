// ============================================================
// ui/header-nav.js - SHARED APP NAVIGATION (used by every page)
// ============================================================
// One place that lists the app's pages. Future options = add one
// entry to PAGES. Each page renders the row and marks its own link
// with "current":
//   index.html  -> renderHeaderNav("dashboard")  (via js/app.js)
//   config.html -> renderHeaderNav("config")     (via js/config-page.js)
//   chat.html   -> renderHeaderNav("chat")       (static anchors in markup)
//
// renderDynamicHeaderButtons (Phase 2 - Dynamic UI Manifests) mounts extra
// buttons declared by drop-in custom modules (interface/custom_module_manager.py)
// via GET /api/interface/status -> ui_manifests. Adding a new .py module with
// a UI_MANIFEST (see about/set_title.py's `create-module` generator) is
// enough to get a new header button - no edits to this file or index.html.
// ============================================================

import { getInterfaceStatus } from "../api/api.js";

const PAGES = [
    { id: "dashboard", label: "Dashboard", href: "/static/index.html" },
    { id: "chat", label: "Chat", href: "/static/chat.html" },
    { id: "config", label: "Settings", href: "/static/config.html" },
];

/** Build the shared nav row, highlighting the entry whose id === currentId. */
export function renderHeaderNav(currentId = "") {
    const nav = document.createElement("nav");
    nav.className = "app-header-nav";
    nav.setAttribute("aria-label", "Primary");

    PAGES.forEach((page) => {
        const link = document.createElement("a");
        link.href = page.href;
        link.textContent = page.label;
        link.className = "header-nav-link" + (page.id === currentId ? " current" : "");
        if (page.id === currentId) {
            link.setAttribute("aria-current", "page");
        }
        nav.appendChild(link);
    });

    return nav;
}

/**
 * Fetch /api/interface/status and mount every registered custom module's
 * UI_MANIFEST buttons into `container` (Phase 2 - Dynamic UI Manifests).
 *
 * @param {HTMLElement} container       - element to append buttons into
 *                                         (e.g. the #app-nav slot)
 * @param {(btnConfig: object) => void} onActionTriggered - called with the
 *                                         button's manifest entry on click
 *
 * Fail-soft by design: a server without /api/interface/status (or with no
 * custom modules loaded) simply renders nothing extra.
 */
export async function renderDynamicHeaderButtons(container, onActionTriggered) {
    if (!container) {
        return;
    }
    try {
        const status = await getInterfaceStatus();
        const manifests = status.ui_manifests || [];

        manifests.forEach((manifest) => {
            (manifest.buttons || []).forEach((btnConfig) => {
                if (document.getElementById(btnConfig.id)) return; // avoid duplicates

                const btn = document.createElement("button");
                btn.type = "button";
                btn.id = btnConfig.id;
                btn.className = "header-nav-link";
                btn.textContent = btnConfig.label;
                btn.title = btnConfig.title || "";
                btn.style.cursor = "pointer";

                btn.addEventListener("click", () => {
                    if (onActionTriggered) {
                        onActionTriggered(btnConfig);
                    }
                });

                container.appendChild(btn);
            });
        });
    } catch (err) {
        console.warn("[UI] Could not render dynamic header buttons:", err);
    }
}
