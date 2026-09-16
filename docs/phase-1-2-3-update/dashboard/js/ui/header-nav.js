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
 * A manifest button with `action: "dropdown_menu"` is rendered as a flyout:
 * its `items` become sub-buttons, and each one is handed to
 * `onActionTriggered` (with the parent button, so a status dot can attach).
 *
 * @param {HTMLElement} container       - element to append buttons into
 *                                         (e.g. the #app-nav slot)
 * @param {(btnConfig: object, parentBtn?: HTMLElement) => void} onActionTriggered
 *                                         - called with the trigger config (and
 *                                         parent button for dropdown items) on click
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

        // One delegated listener closes any open dropdown on an outside click,
        // instead of binding a per-dropdown global handler on every render.
        document.addEventListener("click", () => {
            document.querySelectorAll(".nav-dropdown-menu").forEach(
                (menu) => menu.classList.add("hidden")
            );
        });

        manifests.forEach((manifest) => {
            (manifest.buttons || []).forEach((btnConfig) => {
                if (document.getElementById(btnConfig.id)) return; // avoid duplicates

                if (btnConfig.action === "dropdown_menu") {
                    const wrapper = document.createElement("div");
                    wrapper.className = "nav-dropdown-wrapper";

                    const btn = document.createElement("button");
                    btn.type = "button";
                    btn.id = btnConfig.id;
                    btn.className = "header-nav-link";
                    btn.textContent = (btnConfig.label || "Menu") + " \u25be";
                    btn.title = btnConfig.title || "";
                    btn.style.cursor = "pointer";

                    const menu = document.createElement("div");
                    menu.className = "nav-dropdown-menu hidden";

                    (btnConfig.items || []).forEach((subItem) => {
                        const itemBtn = document.createElement("button");
                        itemBtn.type = "button";
                        itemBtn.className = "nav-dropdown-item";
                        itemBtn.textContent = subItem.label;
                        itemBtn.onclick = () => {
                            menu.classList.add("hidden");
                            if (onActionTriggered) {
                                onActionTriggered(subItem, btn);
                            }
                        };
                        menu.appendChild(itemBtn);
                    });

                    btn.addEventListener("click", (e) => {
                        e.stopPropagation();
                        document.querySelectorAll(".nav-dropdown-menu").forEach(
                            (m) => m.classList.add("hidden")
                        );
                        menu.classList.toggle("hidden");
                    });

                    wrapper.appendChild(btn);
                    wrapper.appendChild(menu);
                    container.appendChild(wrapper);
                    return;
                }

                // Regular header button (prompt_input / open_modal / qa_survey...).
                const btn = document.createElement("button");
                btn.type = "button";
                btn.id = btnConfig.id;
                btn.className = "header-nav-link";
                btn.textContent = btnConfig.label;
                btn.title = btnConfig.title || "";
                btn.style.cursor = "pointer";

                btn.addEventListener("click", () => {
                    if (onActionTriggered) {
                        onActionTriggered(btnConfig, btn);
                    }
                });

                container.appendChild(btn);
            });
        });
    } catch (err) {
        console.warn("[UI] Could not render dynamic header buttons:", err);
    }
}
