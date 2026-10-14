import { h, mount } from "../../core/dom.js";
import { widgetLauncher } from "../../components/widget-launcher.js";
import { widgetsConsumptionPanel } from "../home/panels.js";
import { cachedWidgets } from "../../core/widgets.js";
import { api } from "../../core/http.js";

export function renderWidgets(outlet) {
  const consumptionBox = h("div", { class: "panel-futuristic" });

  const view = h("section", { class: "view dashboard-view" },
    h("div", { class: "view-head" },
      h("p", { class: "eyebrow" }, "Controllo & Telemetria Moduli"),
      h("h2", {}, "Matrice Widget"),
      h("p", {}, "Tocca un widget per proiettarlo subito sul display centrale. Di seguito puoi monitorare il consumo CPU e la latenza dei dati dal vivo.")),
    h("div", { class: "panel" }, widgetLauncher({ search: true })),
    consumptionBox,
    h("div", { class: "panel min-pilot" },
      h("p", { class: "ptitle" }, "Priorità, posizioni e widget personalizzati"),
      h("div", { class: "chips" }, h("a", { class: "btn ghost", href: "#/tool/desktop" }, "Apri il desktop a widget"))));

  mount(outlet, view);

  let currentWidgets = cachedWidgets();
  const updateConsumption = (list) => {
    if (view.isConnected) mount(consumptionBox, widgetsConsumptionPanel(list));
  };
  updateConsumption(currentWidgets);

  api("/api/widgets").then((data) => {
    currentWidgets = (data.widgets || []).filter((w) => w.enabled && w.id !== "alarm");
    updateConsumption(currentWidgets);
  }).catch(() => {});
}
