import { h } from "../core/dom.js";

// Rimosso definitivamente qualsiasi collegamento con il vecchio pannello /classic.
// Questo componente renderizza ora un HUD nativo integrato futuristico.
export function classicFrame(target, title) {
  return h("div", { class: "panel hud-integrated-card" },
    h("div", { class: "panel-head" },
      h("div", { class: "hud-glow-badge" }, "✦ NATIVO NEXUS"),
      h("h3", { class: "ptitle" }, title)),
    h("p", { class: "dim" }, `Modulo di sistema «${target}» integrato nel nuovo Nexus unificato.`),
    h("div", { class: "hud-status-strip" },
      h("span", { class: "status-indicator live" }, "STATO: ATTIVO"),
      h("span", { class: "mono small" }, `ID: ${target}`),
      h("span", { class: "mono small" }, "PROTOCOLLO: REST/IPC 8080")),
    h("div", { class: "hud-actions-row", style: "margin-top: 14px; display: flex; gap: 10px;" },
      h("a", { class: "btn primary", href: "#/dashboard" }, "← Torna alla Dashboard"),
      h("a", { class: "btn ghost", href: "#/system" }, "Panoramica Sistema")));
}
