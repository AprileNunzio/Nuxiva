import { h, mount } from "../../core/dom.js";
import { go } from "../../core/router.js";
import { store } from "../../core/store.js";
import { onSummary, summary } from "../../core/summary.js";
import { ring } from "../../components/charts.js";
import { Orb } from "../../components/orb.js";
import {
  statTiles,
  processesPanel,
  widgetsConsumptionPanel,
  satellitesControlPanel,
  connectedServersPanel,
  activityPanel,
  componentsPanel,
  freshPanel,
  todoPanel
} from "./panels.js";
import { trackSystem } from "./series.js";
import { cachedWidgets } from "../../core/widgets.js";
import { api } from "../../core/http.js";

trackSystem();

export function renderHome(outlet) {
  const canvas = h("canvas", { "aria-hidden": "true", class: "futuristic-orb-canvas" });
  const sayStatus = h("h2", { class: "home-say-futuristic" }, "Inizializzazione Telemetria Neurale…");
  const ringBox = h("div", { class: "ring-box" });
  const stats = h("div", { class: "stats-futuristic" });
  const processes = h("div", { class: "panel-futuristic" });
  const widgetsConsumption = h("div", { class: "panel-futuristic" });
  const satellites = h("div", { class: "panel-futuristic" });
  const servers = h("div", { class: "panel-futuristic" });
  const todos = h("div", { class: "panel-futuristic" });
  const activity = h("div", { class: "panel-futuristic" });
  const components = h("div", { class: "panel-futuristic" });
  const fresh = h("div", { class: "panel fresh-panel", hidden: true });
  
  const awakeningLink = h("a", { class: "btn primary hud-glow-btn", href: "#/awakening" }, "Configurazione Iniziale (Facoltativa)");

  const view = h("section", { class: "dashboard-view" },
    // HERO: HUD OLOGRAFICO CON SFERA FUTURISTICA
    h("div", { class: "home-hero-futuristic" },
      h("div", { class: "orb-container" },
        h("div", { class: "orb-reticle-ring" }),
        h("div", { class: "orb-radar-sweep" }),
        h("div", { class: "orb-box home-orb" }, canvas),
        h("div", { class: "orb-caption" },
          h("span", { class: "orb-badge-live" }, "NEURAL CORE ACTIVE"))),
      h("div", { class: "home-copy" },
        h("div", { class: "hud-tag-row" },
          h("span", { class: "hud-tag-pill-cyan" }, "DASHBOARD AMMINISTRATIVA :8080"),
          h("span", { class: "hud-tag-pill-green" }, "METODO UNIFICATO")),
        sayStatus,
        h("p", { class: "dashboard-lead" },
          "Monitoraggio centralizzato di consumi e velocità in tempo reale: acceleratori hardware GPU, CPU clock, memoria RAM, matrice processi attivi, consumo di ogni singolo widget, controllo dei satelliti e nodi server cluster."),
        h("div", { class: "ready-futuristic" },
          ringBox,
          h("div", { class: "ready-copy" },
            h("b", {}, "Integrità del Kernel"),
            h("span", { class: "dim-small-block" }, "Verifica continua dello stato dei sottosistemi")),
          awakeningLink))),

    // SEZIONE 1: TELEMETRIA CONSUMI E VELOCITÀ (CPU, GPU, RAM, I/O RETE)
    h("div", { class: "dashboard-section-label" },
      h("span", { class: "sec-num" }, "01"),
      h("span", { class: "sec-title" }, "CONSUMI & VELOCITÀ HARDWARE (LIVE METRICS)")),
    stats,

    // SEZIONE 2: PROCESSI IN TEMPO REALE & SERVER COLLEGATI
    h("div", { class: "dashboard-section-label" },
      h("span", { class: "sec-num" }, "02"),
      h("span", { class: "sec-title" }, "MATRICE PROCESSI & SERVER COLLEGATI")),
    h("div", { class: "cols-2" }, processes, servers),

    // SEZIONE 3: CONTROLLO CONSUMI DEI SATELLITI & CONSUMI DEI WIDGET
    h("div", { class: "dashboard-section-label" },
      h("span", { class: "sec-num" }, "03"),
      h("span", { class: "sec-title" }, "COSTELLAZIONE SATELLITI & RISORSE WIDGET")),
    satellites,
    widgetsConsumption,

    // SEZIONE 4: ATTIVITÀ & EVENTI DEL SISTEMA
    h("div", { class: "dashboard-section-label" },
      h("span", { class: "sec-num" }, "04"),
      h("span", { class: "sec-title" }, "ATTIVITÀ NEURALE & INTEGRAZIONI")),
    fresh,
    h("div", { class: "cols-2" }, todos, activity),
    components
  );

  mount(outlet, view);

  const orb = new Orb(canvas);
  orb.start();

  let currentWidgets = cachedWidgets();
  const loadWidgets = () => api("/api/widgets").then((data) => {
    currentWidgets = (data.widgets || []).filter((w) => w.enabled && w.id !== "alarm");
    if (view.isConnected) mount(widgetsConsumption, widgetsConsumptionPanel(currentWidgets));
  }).catch(() => {});
  loadWidgets();
  const widgetTimer = setInterval(() => (view.isConnected ? loadWidgets() : clearInterval(widgetTimer)), 15000);

  const paintSummary = (data) => {
    if (!data) return;
    orb.setState(data.tone);
    sayStatus.textContent = data.headline?.pilot || data.headline?.explorer || "Sistema Operativo Nuxiva Operativo";
    mount(ringBox, ring(data.health, "Salute dei componenti"));
    const journey = data.awakening || {};
    awakeningLink.textContent = journey.complete
      ? "Rifai Configurazione Iniziale (Facoltativa)"
      : `Configurazione Iniziale (Facoltativa) · ${journey.finished ?? 0}/${journey.total ?? 6}`;
    mount(todos, todoPanel(data.todos || []));
    mount(components, componentsPanel(data.components || []));
    const freshContent = freshPanel(data.fresh);
    fresh.hidden = !freshContent;
    if (freshContent) mount(fresh, freshContent);
  };

  const paintSnapshot = (snapshot) => {
    const sys = snapshot?.system;
    mount(stats, statTiles(sys));
    mount(processes, processesPanel(sys));
    mount(servers, connectedServersPanel(snapshot?.connected_servers));
    mount(satellites, satellitesControlPanel(snapshot?.satellites));
    mount(widgetsConsumption, widgetsConsumptionPanel(currentWidgets));
    mount(activity, activityPanel(snapshot?.events));
  };

  paintSummary(summary());
  paintSnapshot(store.get().snapshot);

  const offSummary = onSummary((data) => {
    if (!view.isConnected) { offSummary(); return; }
    paintSummary(data);
  });

  const offStore = store.subscribe((state, changed) => {
    if (!view.isConnected) { offStore(); return; }
    if (changed.includes("snapshot") || changed.includes("link")) {
      paintSnapshot(state.snapshot);
    }
  });
}
