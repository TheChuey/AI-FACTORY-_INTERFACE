// ============================================================
// ui/header-nav.js - SHARED APP NAVIGATION (used by every page)
// ============================================================
// One place that lists the app's pages. Future options = add one
// entry to PAGES. Each page renders the row and marks its own link
// with "current":
//   index.html  -> renderHeaderNav("dashboard")  (via js/app.js)
//   config.html -> renderHeaderNav("config")     (via js/config-page.js)
//   chat.html   -> renderHeaderNav("chat")       (static anchors in markup)
// ============================================================

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