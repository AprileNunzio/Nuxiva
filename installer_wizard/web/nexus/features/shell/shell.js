import { h, mount } from "../../core/dom.js";
import { api } from "../../core/http.js";
import { go } from "../../core/router.js";
import { store } from "../../core/store.js";
import { onSummary, summary } from "../../core/summary.js";
import { open as openPalette } from "../../components/palette.js";
import { countBadge, freshBadge, isSeen, markSeen } from "../../components/badge.js";
import { unseenFresh } from "../../components/tool-card.js";
import { GROUPS, ZONES, zone } from "./zones.js";

export function createShell(root) {
  const nav = h("nav", { class: "nav", "aria-label": "Zone del pannello" });
  const title = h("h1", { id: "nx-title" }, "Dashboard");
  const linkDot = h("span", { class: "link-state", role: "img", "aria-label": "Collegato ad Nuxiva" });
  const statusChip = h("div", { class: "nx-hud-chip" },
    h("span", { class: "chip-dot" }),
    h("span", { class: "chip-text" }, "NEXUS UNIFIED · 8080"));
  const outlet = h("main", { class: "outlet", id: "nx-outlet", tabindex: "-1" });
  const languages = { it: "Italiano", en: "English", fr: "Français" };
  const current = (window.NuxivaI18n?.language?.() || document.documentElement.lang || "it").slice(0, 2);
  const langPick = h("select", { class: "lang-pick", "aria-label": "Lingua", onchange: (e) => window.NuxivaI18n?.setLanguage(e.target.value) },
    Object.entries(languages).map(([code, label]) => h("option", { value: code, selected: code === current ? true : null }, label)));
  const top = h("header", { class: "top" }, title, linkDot, statusChip,
    h("button", { class: "search", type: "button", onclick: openPalette, "aria-label": "Cerca ovunque" },
      h("span", {}, "Cerca pagine, strumenti, azioni…"), h("kbd", {}, "Ctrl K")),
    langPick);
  mount(root, h("div", { class: "app" }, nav, h("div", { class: "main" }, top, outlet)));

  function zoneMarker(z) {
    const fresh = (summary()?.tools || []).filter((t) => t.zone === z.id && unseenFresh(t)).length;
    if (fresh) return countBadge(fresh, `${fresh} novità o aggiornamenti`);
    return z.added && !isSeen(`zone:${z.id}:${z.added}`) && Date.now() - Date.parse(z.added) < 14 * 86400000
      ? freshBadge({ badge: "new", since: Date.parse(z.added) / 1000 }) : null;
  }

  function favoriteLinks() {
    const { favorites } = store.get();
    const tools = (summary()?.tools || []).filter((t) => favorites.includes(t.id));
    if (!tools.length) return [];
    return [h("div", { class: "navsec" }, "Preferiti"), ...tools.map((t) => h("a", { class: "nv nv-fav", href: `#/tool/${encodeURIComponent(t.id)}` },
      h("span", { class: "g", "aria-hidden": "true" }, t.icon), h("span", { class: "lb" }, t.name)))];
  }

  function renderNav() {
    const { route, user } = store.get();
    const currentActive = (route === "dashboard" || route === "home") ? "home" : route;
    const sections = GROUPS.flatMap((group) => {
      const items = ZONES.filter((z) => z.group === group);
      if (!items.length) return [];
      return [h("div", { class: "navsec" }, group), ...items.map((z) => h("a", {
        class: `nv${z.accent ? " accent" : ""}`, href: `#/${z.id}`, "aria-current": z.id === currentActive ? "page" : null,
      }, h("span", { class: "g", "aria-hidden": "true" }, z.glyph), h("span", { class: "lb" }, z.title), zoneMarker(z)))];
    });
    mount(nav,
      h("a", { class: "brand", href: "#/home" }, "NUXIVA", h("small", {}, "DASHBOARD · 8080")),
      sections,
      favoriteLinks(),
      h("div", { class: "nav-foot" },
        h("button", { class: "nv", type: "button", onclick: logout }, h("span", { class: "g", "aria-hidden": "true" }, "⎋"), h("span", { class: "lb" }, "Esci")),
        h("div", { class: "who" }, user ? `Connesso come ${user}` : "")));
  }

  async function logout() {
    try { await api("/api/auth/logout", { method: "POST" }); } catch (err) { console.warn("Uscita non confermata", err); }
    location.reload();
  }

  store.subscribe((state, changed) => {
    if (["route", "user", "favorites"].some((key) => changed.includes(key))) renderNav();
    if (changed.includes("link")) {
      linkDot.classList.toggle("down", !state.link);
      linkDot.setAttribute("aria-label", state.link ? "Collegato ad Nuxiva" : "Collegamento con Nuxiva perso");
      statusChip.classList.toggle("down", !state.link);
      const text = statusChip.querySelector(".chip-text");
      if (text) text.textContent = state.link ? "NEXUS UNIFIED · 8080" : "OFFLINE / DISCONNESSO";
    }
  });
  renderNav();
  onSummary(renderNav);

  return {
    outlet,
    show(route, render) {
      const targetId = (route.id === "dashboard") ? "home" : route.id;
      const z = zone(targetId);
      if (z?.added) { markSeen(`zone:${z.id}:${z.added}`); renderNav(); }
      const displayTitle = (route.id === "home" || route.id === "dashboard") ? "Dashboard" : (z ? z.title : { tool: "Strumento", section: "Sezione" }[route.id] || "Nexus");
      title.textContent = displayTitle;
      document.title = `${displayTitle} · Nuxiva Dashboard`;
      render(outlet, route);
      outlet.scrollTop = 0;
    },
  };
}
