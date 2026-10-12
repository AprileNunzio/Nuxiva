import { h } from "./dom.js";
import { api } from "./http.js";
import { toast } from "./toast.js";

const tr = (key, ...args) => (window.NuxivaI18n?.translate ? window.NuxivaI18n.translate(key, ...args) : key);

const MESSAGES = {
  live: (name) => `${name}: aperto sul display con i dati dal vivo`,
  last: (name) => `${name}: riaperto sul display con gli ultimi dati`,
  preview: (name) => `${name}: anteprima sul display. Chiedilo ad Nuxiva per i dati veri`,
};
let cache = null, pending = null;

export async function widgets() {
  if (cache) return cache;
  if (!pending) {
    pending = api("/api/widgets").then((data) => {
      cache = (data.widgets || []).filter((w) => w.enabled && w.id !== "alarm");
      return cache;
    }).finally(() => { pending = null; });
  }
  return pending;
}

export const cachedWidgets = () => cache || [];

function pickTarget(targets, widgetName) {
  return new Promise((resolve) => {
    const close = (val) => { overlay.remove(); document.removeEventListener("keydown", onKey); resolve(val); };
    const onKey = (e) => { if (e.key === "Escape") close(null); };
    const items = targets.map((t) => {
      const b = h("button", { type: "button", class: "btn ghost" },
        h("span", {}, t.name),
        h("span", { class: "dim" }, t.type || ""));
      b.style.display = "flex";
      b.style.justifyContent = "space-between";
      b.style.alignItems = "center";
      b.style.width = "100%";
      b.style.minHeight = "44px";
      b.style.marginBottom = "8px";
      b.style.touchAction = "manipulation";
      b.onclick = () => close(t.id);
      return b;
    });

    const box = h("div", { class: "confirm-box", role: "dialog", "aria-modal": "true" },
      h("h2", {}, tr("Dove vuoi mostrare l'anteprima?")),
      h("p", { class: "dim" }, tr("Scegli lo schermo o satellite su cui proiettare «{0}»:", widgetName)),
      h("div", { class: "target-list" }, items),
      h("div", { class: "aw-nav" },
        h("button", { class: "btn ghost", type: "button", onclick: () => close(null) }, tr("Annulla"))));
    box.style.maxWidth = "480px";
    box.style.width = "100%";

    const overlay = h("div", { class: "pal", onclick: (e) => { if (e.target === overlay) close(null); } }, box);
    document.addEventListener("keydown", onKey);
    document.body.append(overlay);
  });
}

export async function recall(widget, targetId = null) {
  let target = targetId;
  if (!target) {
    try {
      const resp = await api("/api/widgets/targets");
      const targets = resp?.targets || [];
      if (targets.length > 1) {
        target = await pickTarget(targets, widget.name);
        if (!target) return null;
      }
    } catch (e) {}
  }
  const result = await api(`/api/widgets/${encodeURIComponent(widget.id)}/recall`, {
    method: "POST",
    body: target ? { target } : {},
  });
  toast((MESSAGES[result.origin] || MESSAGES.preview)(widget.name));
  return result.origin;
}
