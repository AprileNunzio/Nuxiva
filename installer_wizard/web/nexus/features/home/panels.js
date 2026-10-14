import { h } from "../../core/dom.js";
import { sparkline } from "../../components/charts.js";
import { freshBadge } from "../../components/badge.js";
import { SERIES } from "./series.js";
import { sectionHref } from "../section/section.js";
import { recall } from "../../core/widgets.js";
import { fail } from "../../core/toast.js";

const GB = 1024 ** 3;
const gb = (bytes) => (bytes / GB).toLocaleString(document.documentElement.lang || "it", { maximumFractionDigits: 1 });
const COMPONENT_PILL = { ok: ["ok", "attivo"], warn: ["warn", "a metà"], down: ["bad", "fermo"] };
const EVENT_SEVERITY = { ERROR: "bad", WARN: "warn", INFO: "info" };

function uptime(seconds) {
  const d = Math.floor(seconds / 86400), hrs = Math.floor((seconds % 86400) / 3600), min = Math.floor((seconds % 3600) / 60);
  return d ? `${d} g ${hrs} h` : hrs ? `${hrs} h ${min} min` : `${min} min`;
}

function formatRate(bps) {
  if (!bps || bps < 1024) return `${Math.round(bps || 0)} B/s`;
  if (bps < 1024 * 1024) return `${(bps / 1024).toFixed(1)} KB/s`;
  return `${(bps / (1024 * 1024)).toFixed(1)} MB/s`;
}

function tile(label, value, unit, note, series, max = 100, badge = null, extraBar = null) {
  return h("div", { class: "stat-card-futuristic" },
    h("div", { class: "stat-header" },
      h("p", { class: "ptitle" }, label),
      badge ? h("span", { class: "hud-mini-tag" }, badge) : null),
    h("div", { class: "stat-v" }, value ?? "—", value != null ? h("small", {}, unit) : null),
    extraBar || null,
    h("div", { class: "stat-note" }, note),
    sparkline(series.values, { max }));
}

export function statTiles(sys) {
  if (!sys) return [1, 2, 3, 4].map(() => h("div", { class: "panel stat skeleton-tile" }, h("div", { class: "skeleton" })));

  const cpuSpeed = sys.cpu_freq ? `${(sys.cpu_freq >= 1000 ? (sys.cpu_freq / 1000).toFixed(2) + " GHz" : sys.cpu_freq + " MHz")}` : "—";
  const cpuLoadNote = `${sys.cpu_count} core · clock ${cpuSpeed} · carico ${sys.load?.[0] ?? "—"}`;
  
  // CPU per-core micro bar
  const coreBars = (sys.per_cpu && sys.per_cpu.length) ? h("div", { class: "core-meter-row", title: "Carico singoli core logici" },
    sys.per_cpu.slice(0, 16).map((val, idx) => {
      const coreVal = Number(val) || 0;
      return h("div", {
        class: "core-bar-item",
        style: `height:${Math.max(4, Math.min(coreVal, 100))}%;`,
        title: `Core ${idx}: ${coreVal}%`
      });
    })) : null;

  // GPU telemetry
  const gpu = sys.gpu && sys.gpu.available !== false ? sys.gpu : null;
  const gpuPct = Math.max(0, Math.min(Number(gpu?.vram_percent ?? gpu?.gpu_percent) || 0, 100));
  const gpuNote = gpu
    ? `${gpu.name} · clock ${gpu.clock_mhz ? `${Math.round(gpu.clock_mhz)} MHz` : "—"} · VRAM ${Math.round(gpu.vram_used || 0)}/${Math.round(gpu.vram_total || 0)} MB`
    : "Nessuna GPU dedicata rilevata";
  const gpuBar = gpu ? h("div", { class: "hud-linear-meter" },
    h("div", { class: "meter-fill-gpu", style: `width:${gpuPct}%;` })) : null;

  // RAM telemetry
  const memPct = Math.max(0, Math.min(Number(sys.mem_percent) || 0, 100));
  const ramNote = `${gb(sys.mem_used)} di ${gb(sys.mem_total)} GB · swap ${Math.round(sys.swap_percent ?? 0)}%`;
  const ramBar = h("div", { class: "hud-linear-meter" },
    h("div", { class: "meter-fill-ram", style: `width:${memPct}%;` }));

  // I/O & Network Net Speed
  const netRx = formatRate(sys.net_rx_rate);
  const netTx = formatRate(sys.net_tx_rate);
  const netNote = `↓ ${netRx} · ↑ ${netTx} · libero ${gb(sys.disk_total - sys.disk_used)} GB`;

  return [
    tile("Processore (CPU)", Math.round(sys.cpu_percent), "%", cpuLoadNote, SERIES.cpu, 100, cpuSpeed, coreBars),
    tile("Scheda Video (GPU)", gpu ? Math.round(gpu.gpu_percent || 0) : null, "%", gpuNote, SERIES.gpu, 100, gpu?.temp != null ? `${Math.round(gpu.temp)}°C` : null, gpuBar),
    tile("Memoria (RAM)", Math.round(sys.mem_percent), "%", ramNote, SERIES.mem, 100, `${gb(sys.mem_total - sys.mem_used)} GB liberi`, ramBar),
    tile("Velocità Rete & Disco", Math.round(sys.disk_percent), "%", netNote, SERIES.disk, 100, sys.temperature != null ? `${Math.round(sys.temperature)}°C` : null),
  ];
}

export function processesPanel(sys) {
  const procs = sys?.top_processes || [];
  return [
    h("div", { class: "head-futuristic" },
      h("div", { class: "head-title-wrap" },
        h("span", { class: "hud-pill-tag-cyan" }, "VELOCITÀ & CARICO"),
        h("p", { class: "ptitle" }, "Matrice Processi in Tempo Reale")),
      h("span", { class: "dim-mono-small" }, `${procs.length} processi prioritari monitorati`)),
    h("div", { class: "tbl-wrap" },
      h("table", { class: "futuristic-table" },
        h("thead", {}, h("tr", {},
          h("th", {}, "PID"),
          h("th", {}, "PROCESSO"),
          h("th", {}, "STATO"),
          h("th", { class: "col-r" }, "CPU %"),
          h("th", { class: "col-r" }, "RAM (MB)"))),
        h("tbody", {}, procs.length ? procs.map((p) => {
          const cpuVal = Number(p.cpu) || 0;
          const cpuBarPct = Math.max(0, Math.min(cpuVal * 2, 100));
          return h("tr", { class: "proc-row" },
            h("td", { class: "mono-dim-cyan" }, String(p.pid)),
            h("td", { class: "mono-bold" }, p.name),
            h("td", {}, h("span", { class: `proc-status ${p.status === "running" ? "live" : "idle"}` }, p.status.toUpperCase())),
            h("td", { class: "col-r" },
              h("div", { class: "val-with-bar" },
                h("span", { class: "mono-accent" }, `${cpuVal.toFixed(1)}%`),
                h("div", { class: "mini-bar-track" }, h("div", { class: "mini-bar-fill", style: `width:${cpuBarPct}%;` })))),
            h("td", { class: "mono-dim-r" }, `${(Number(p.mem_mb) || 0).toFixed(1)} MB`));
        })
          : [h("tr", {}, h("td", { colspan: "5", class: "dim-text-center" }, "Lettura telemetria processi in corso…"))])))
  ];
}

export function widgetsConsumptionPanel(widgetsList) {
  const items = widgetsList || [];
  const fmtCost = (c) => (c ? `${c.cpu_percent.toFixed(2)}%` : "—");
  return [
    h("div", { class: "head-futuristic" },
      h("div", { class: "head-title-wrap" },
        h("span", { class: "hud-pill-tag-violet" }, "RISORSE MODULI"),
        h("p", { class: "ptitle" }, "Consumo Singoli Widget")),
      h("a", { class: "btn ghost small", href: "#/widgets" }, "Tutti i Widget →")),
    items.length ? h("div", { class: "widget-consumption-grid" },
      items.map((w) => h("div", { class: "widget-consumption-card" },
        h("div", { class: "wcard-top" },
          h("span", { class: "wcard-icon" }, w.icon || "▣"),
          h("div", { class: "wcard-meta" },
            h("b", { class: "wcard-title" }, w.name),
            h("span", { class: "wcard-sub" }, w.id)),
          h("span", { class: `wcard-badge ${w.on_screen ? "active" : "ready"}` }, w.on_screen ? "Sul display" : "Pronto")),
        h("div", { class: "wcard-metrics" },
          h("div", { class: "wmetric" },
            h("span", { class: "wmetric-lbl" }, "CPU"),
            h("span", { class: "wmetric-val" }, fmtCost(w.cost))),
          h("div", { class: "wmetric" },
            h("span", { class: "wmetric-lbl" }, "ULTIMA LETTURA"),
            h("span", { class: "wmetric-val" }, w.cost ? `${w.cost.last_ms} ms` : "—")),
          h("div", { class: "wmetric" },
            h("span", { class: "wmetric-lbl" }, "LETTURE"),
            h("span", { class: "wmetric-val" }, w.cost ? String(w.cost.calls) : "—"))),
        h("button", {
          type: "button",
          class: "btn ghost small wcard-btn",
          onclick: () => recall(w).catch(fail),
        }, "Proietta sul Display ↗"))))
      : h("p", { class: "dim" }, "Nessun widget attivo."),
    h("p", { class: "dim-small" }, "Il consumo è il tempo di CPU del server speso a leggere i dati di ogni widget; «—» indica un widget senza sorgente dati dal vivo."),
  ];
}

export function satellitesControlPanel(satellites) {
  const sats = satellites || [];
  const metric = (s, key, unit) => (s.metrics?.[key] != null ? `${s.metrics[key]}${unit}` : "—");
  return [
    h("div", { class: "head-futuristic" },
      h("div", { class: "head-title-wrap" },
        h("span", { class: "hud-pill-tag-green" }, "COSTELLAZIONE PERIFERICHE"),
        h("p", { class: "ptitle" }, "Controllo Consumi Satelliti Collegati")),
      h("span", { class: "dim-small" }, `${sats.filter((s) => s.online).length}/${sats.length} satelliti online`)),
    sats.length ? h("div", { class: "satellites-grid" },
      sats.map((s) => h("div", { class: `satellite-card ${s.online ? "is-online" : "is-offline"}` },
        h("div", { class: "sat-top" },
          h("div", { class: "sat-radar-dot" }, h("span", { class: `dot-pulse ${s.online ? "green" : "red"}` })),
          h("div", { class: "sat-title-block" },
            h("b", { class: "sat-name" }, s.name),
            h("span", { class: "sat-loc" }, [s.room, s.type_label].filter(Boolean).join(" · "))),
          h("span", { class: `sat-state-pill ${s.online ? "online" : "offline"}` }, s.online ? "ONLINE" : "OFFLINE")),
        h("div", { class: "sat-telemetry-row" },
          h("div", { class: "sat-stat-box" }, h("span", { class: "s-lbl" }, "CPU"), h("span", { class: "s-val" }, metric(s, "cpu", "%"))),
          h("div", { class: "sat-stat-box" }, h("span", { class: "s-lbl" }, "RAM"), h("span", { class: "s-val" }, metric(s, "ram", "%"))),
          h("div", { class: "sat-stat-box" }, h("span", { class: "s-lbl" }, "IP"), h("span", { class: "s-val" }, s.ip || "—"))))))
      : h("p", { class: "dim" }, "Nessun satellite collegato. Aggiungine uno dalla sezione Dispositivi."),
  ];
}

export function connectedServersPanel(connectedServers) {
  const servers = connectedServers || [];
  return [
    h("div", { class: "head-futuristic" },
      h("div", { class: "head-title-wrap" },
        h("span", { class: "hud-pill-tag-amber" }, "INFRASTRUTTURA CLUSTER"),
        h("p", { class: "ptitle" }, "Server & Nodi Collegati")),
      h("span", { class: "dim-small" }, `${servers.filter((s) => s.status === "online").length}/${servers.length} raggiungibili`)),
    servers.length ? h("div", { class: "servers-grid" },
      servers.map((srv) => h("div", { class: `server-node-card ${srv.status === "online" ? "server-live" : "server-idle"}` },
        h("div", { class: "server-header" },
          h("div", { class: "server-indicator" }),
          h("b", { class: "server-title" }, srv.name),
          h("span", { class: "server-port-tag" }, `:${srv.port}`)),
        h("div", { class: "server-desc" }, srv.role || ""),
        h("div", { class: "server-footer" },
          h("span", { class: "server-proto" }, srv.protocol || ""),
          h("span", { class: "server-lat" }, srv.latency_ms != null ? `${srv.latency_ms} ms` : "—"),
          h("span", { class: `server-state-tag ${srv.status}` }, srv.status === "online" ? "ONLINE" : "OFFLINE")))))
      : h("p", { class: "dim" }, "Verifica dei servizi in corso…"),
  ];
}

export function todoPanel(todos) {
  const items = todos.length
    ? todos.map((t) => h("li", {}, h("a", { class: "todo", href: t.target ? sectionHref(t.target) : `#/${t.zone}` },
      h("span", { class: `sev ${t.severity === "info" ? "" : t.severity}` }), h("span", { class: "todo-text" }, t.text),
      h("span", { class: "todo-go", "aria-hidden": "true" }, "→"))))
    : [h("li", { class: "todo-empty" }, h("span", { class: "sev ok" }), "Nessun intervento richiesto: parametri ottimali.")];
  return [h("p", { class: "ptitle" }, "Cose da fare & Ottimizzazioni"), h("ul", { class: "todos" }, items)];
}

export function activityPanel(events) {
  const recent = (events || []).slice(-7).reverse();
  return [h("p", { class: "ptitle" }, "Attività & Eventi Neurale"),
    recent.length
      ? h("ul", { class: "feed" }, recent.map((e) => h("li", {},
        h("time", { datetime: e.ts }, new Date(e.ts).toLocaleTimeString(document.documentElement.lang || "it", { hour: "2-digit", minute: "2-digit" })),
        h("span", { class: `sev ${EVENT_SEVERITY[e.level] === "info" ? "" : EVENT_SEVERITY[e.level] || ""}` }),
        h("span", { class: "feed-msg" }, e.msg))))
      : h("p", { class: "dim" }, "Ancora nessuna attività registrata.")];
}

export function componentsPanel(components) {
  return [h("p", { class: "ptitle" }, "Componenti del Kernel"),
    h("div", { class: "tbl-wrap" }, h("table", { class: "futuristic-table" },
      h("thead", {}, h("tr", {}, h("th", {}, "Componente"), h("th", {}, "Stato"), h("th", {}, "Dettaglio Telemetrico"))),
      h("tbody", {}, components.map((c) => {
        const [tone, label] = c.on_demand ? ["", "su richiesta"] : COMPONENT_PILL[c.status] || ["", c.status || "—"];
        return h("tr", {}, h("td", { class: "text-bold" }, c.label), h("td", {}, h("span", { class: `pill ${tone}` }, label)),
          h("td", { class: "mono dim cell-detail" }, c.detail || ""));
      }))))];
}

export function freshPanel(fresh) {
  const items = fresh || [];
  if (!items.length) return null;
  return [
    h("p", { class: "ptitle" }, "Novità & Aggiornamenti dell'Orchestratore"),
    h("ul", { class: "fresh-list" }, items.slice(0, 8).map((f) => h("li", {}, h("a", { class: "fresh-item", href: `#/tool/${encodeURIComponent(f.id)}` },
      h("span", { class: "glyph", "aria-hidden": "true" }, f.icon), h("span", { class: "fresh-name" }, f.name), freshBadge(f))))),
  ];
}
