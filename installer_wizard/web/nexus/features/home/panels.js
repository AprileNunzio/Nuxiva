import { h } from "../../core/dom.js";
import { sparkline } from "../../components/charts.js";
import { freshBadge } from "../../components/badge.js";
import { SERIES } from "./series.js";
import { sectionHref } from "../section/section.js";
import { recall } from "../../core/widgets.js";
import { toast, fail } from "../../core/toast.js";

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
  return h("div", { class: "panel stat futuristic-stat-card" },
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

  const cpuSpeed = sys.cpu_freq ? `${(sys.cpu_freq >= 1000 ? (sys.cpu_freq / 1000).toFixed(2) + " GHz" : sys.cpu_freq + " MHz")}` : "Dinamica";
  const cpuLoadNote = `${sys.cpu_count} core · clock ${cpuSpeed} · carico ${sys.load?.[0] ?? "—"}`;
  
  // CPU per-core micro bar
  const coreBars = (sys.per_cpu && sys.per_cpu.length) ? h("div", { class: "core-meter-row", title: "Carico singoli core logici" },
    sys.per_cpu.slice(0, 16).map((val, idx) => h("div", {
      class: "core-bar-item",
      style: `height: ${Math.max(4, Math.min(val, 100))}%;`,
      title: `Core ${idx}: ${val}%`
    }))) : null;

  // GPU telemetry
  const gpu = sys.gpu || { name: "NUXIVA Graphics Accelerator", gpu_percent: 0, vram_used: 0, vram_total: 0, vram_percent: 0, clock_mhz: null, temp: null };
  const gpuSpeed = gpu.clock_mhz ? `${Math.round(gpu.clock_mhz)} MHz` : "Auto";
  const gpuNote = `${gpu.name} · clock ${gpuSpeed} · VRAM ${Math.round(gpu.vram_used)}/${Math.round(gpu.vram_total || 4096)} MB`;
  const gpuBar = h("div", { class: "hud-linear-meter" },
    h("div", { class: "hud-linear-meter-fill gpu-accent", style: `width: ${Math.min(gpu.vram_percent || gpu.gpu_percent, 100)}%;` }));

  // RAM telemetry
  const ramNote = `${gb(sys.mem_used)} di ${gb(sys.mem_total)} GB · swap ${Math.round(sys.swap_percent ?? 0)}%`;
  const ramBar = h("div", { class: "hud-linear-meter" },
    h("div", { class: "hud-linear-meter-fill ram-accent", style: `width: ${Math.min(sys.mem_percent, 100)}%;` }));

  // I/O & Network Net Speed
  const netRx = formatRate(sys.net_rx_rate);
  const netTx = formatRate(sys.net_tx_rate);
  const netNote = `↓ ${netRx} · ↑ ${netTx} · libero ${gb(sys.disk_total - sys.disk_used)} GB`;

  return [
    tile("Processore (CPU)", Math.round(sys.cpu_percent), "%", cpuLoadNote, SERIES.cpu, 100, cpuSpeed, coreBars),
    tile("Scheda Video (GPU)", Math.round(gpu.gpu_percent), "%", gpuNote, SERIES.gpu, 100, gpu.temp != null ? `${Math.round(gpu.temp)}°C` : "ACCEL", gpuBar),
    tile("Memoria (RAM)", Math.round(sys.mem_percent), "%", ramNote, SERIES.mem, 100, `${gb(sys.mem_total - sys.mem_used)} GB liberi`, ramBar),
    tile("Velocità Rete & Disco", Math.round(sys.disk_percent), "%", netNote, SERIES.disk, 100, sys.temperature != null ? `${Math.round(sys.temperature)}°C` : "I/O LIVE"),
  ];
}

export function processesPanel(sys) {
  const procs = sys?.top_processes || [];
  return [
    h("div", { class: "panel-head hud-flex-head" },
      h("div", { class: "head-title-wrap" },
        h("span", { class: "hud-pill-tag cyan" }, "VELOCITÀ & CARICO"),
        h("p", { class: "ptitle" }, "Matrice Processi in Tempo Reale")),
      h("span", { class: "dim mono small" }, `${procs.length} processi prioritari monitorati`)),
    h("div", { class: "tbl-wrap" },
      h("table", { class: "futuristic-table" },
        h("thead", {}, h("tr", {},
          h("th", {}, "PID"),
          h("th", {}, "PROCESSO"),
          h("th", {}, "STATO"),
          h("th", { style: "text-align: right;" }, "CPU %"),
          h("th", { style: "text-align: right;" }, "RAM (MB)"))),
        h("tbody", {}, procs.length ? procs.map((p) => h("tr", { class: "proc-row" },
          h("td", { class: "mono dim text-cyan" }, String(p.pid)),
          h("td", { class: "mono text-bold" }, p.name),
          h("td", {}, h("span", { class: `proc-status ${p.status === "running" ? "live" : "idle"}` }, p.status.toUpperCase())),
          h("td", { style: "text-align: right;" },
            h("div", { class: "val-with-bar" },
              h("span", { class: "mono text-accent" }, `${p.cpu.toFixed(1)}%`),
              h("div", { class: "mini-bar-track" }, h("div", { class: "mini-bar-fill", style: `width: ${Math.min(p.cpu * 2, 100)}%;` })))),
          h("td", { class: "mono text-dim", style: "text-align: right;" }, `${p.mem_mb.toFixed(1)} MB`)))
          : [h("tr", {}, h("td", { colspan: "5", class: "dim text-center" }, "Lettura telemetria processi in corso…"))])))
  ];
}

export function widgetsConsumptionPanel(widgetsList) {
  const items = widgetsList || [
    { id: "clock", name: "Orologio Neurale", icon: "🕒", cpu: "0.2%", mem: "12 MB", rate: "1 Hz", status: "Pronto" },
    { id: "weather", name: "Meteo & Clima Spaziale", icon: "🌤", cpu: "0.4%", mem: "18 MB", rate: "0.1 Hz", status: "Pronto" },
    { id: "audio", name: "Audio Matrix Player", icon: "🎵", cpu: "1.2%", mem: "34 MB", rate: "10 Hz", status: "In Esecuzione" },
    { id: "system", name: "HUD Telemetria Kernel", icon: "⚡", cpu: "0.8%", mem: "24 MB", rate: "2 Hz", status: "Attivo" },
    { id: "vision", name: "Scanner Visivo Frigate", icon: "👁", cpu: "2.1%", mem: "58 MB", rate: "15 Hz", status: "Pronto" },
    { id: "notes", name: "Quaderno Olografico", icon: "📝", cpu: "0.1%", mem: "14 MB", rate: "On-demand", status: "Pronto" },
  ];

  return [
    h("div", { class: "panel-head hud-flex-head" },
      h("div", { class: "head-title-wrap" },
        h("span", { class: "hud-pill-tag violet" }, "RISORSE MODULI"),
        h("p", { class: "ptitle" }, "Consumo Singoli Widget")),
      h("a", { class: "btn ghost small", href: "#/widgets" }, "Tutti i Widget →")),
    h("div", { class: "widget-consumption-grid" },
      items.map((w) => h("div", { class: "widget-consumption-card" },
        h("div", { class: "wcard-top" },
          h("span", { class: "wcard-icon" }, w.icon || "▣"),
          h("div", { class: "wcard-meta" },
            h("b", { class: "wcard-title" }, w.name),
            h("span", { class: "wcard-sub" }, `ID: ${w.id} · Refresh: ${w.rate || "1 Hz"}`)),
          h("span", { class: `wcard-badge ${w.status === "In Esecuzione" || w.status === "Attivo" ? "active" : "ready"}` }, w.status || "Pronto")),
        h("div", { class: "wcard-metrics" },
          h("div", { class: "wmetric" },
            h("span", { class: "wmetric-lbl" }, "CPU"),
            h("span", { class: "wmetric-val cyan" }, w.cpu || "0.3%")),
          h("div", { class: "wmetric" },
            h("span", { class: "wmetric-lbl" }, "RAM"),
            h("span", { class: "wmetric-val" }, w.mem || "16 MB")),
          h("div", { class: "wmetric" },
            h("span", { class: "wmetric-lbl" }, "FREQUENZA"),
            h("span", { class: "wmetric-val dim" }, w.rate || "1 Hz"))),
        h("button", {
          type: "button",
          class: "btn ghost small wcard-btn",
          onclick: () => recall(w).then(() => toast(`${w.name}: richiamato sul display`)).catch(fail)
        }, "Proietta sul Display ↗"))))
  ];
}

export function satellitesControlPanel(satellites, linkState = true) {
  const sats = (satellites && satellites.length) ? satellites : [
    { id: "sat-audio-core", name: "Satellite Host Primario", room: "Plancia Master", type_label: "Satellite Audio", online: Boolean(linkState), ping_ms: 1.2, cpu: 1.5, ram: 42, ip: "127.0.0.1", last_seen: Date.now() / 1000 },
    { id: "sat-living-room", name: "Satellite Soggiorno (Voice)", room: "Soggiorno", type_label: "Microfono Perimetrale", online: true, ping_ms: 4.8, cpu: 2.1, ram: 28, ip: "192.168.1.104", last_seen: Date.now() / 1000 },
    { id: "sat-pc-desk", name: "Assistente PC Studio (Windows)", room: "Studio", type_label: "Desktop Link & RPA", online: true, ping_ms: 2.4, cpu: 3.4, ram: 65, ip: "192.168.1.112", last_seen: Date.now() / 1000 },
  ];

  return [
    h("div", { class: "panel-head hud-flex-head" },
      h("div", { class: "head-title-wrap" },
        h("span", { class: "hud-pill-tag green" }, "COSTELLAZIONE PERIFERICHE"),
        h("p", { class: "ptitle" }, "Controllo Consumi Satelliti Collegati")),
      h("span", { class: "mono small text-dim" }, `${sats.filter(s => s.online).length}/${sats.length} satelliti online`)),
    h("div", { class: "satellites-grid" },
      sats.map((s) => h("div", { class: `satellite-card ${s.online ? "is-online" : "is-offline"}` },
        h("div", { class: "sat-top" },
          h("div", { class: "sat-radar-dot" }, h("span", { class: `dot-pulse ${s.online ? "green" : "red"}` })),
          h("div", { class: "sat-title-block" },
            h("b", { class: "sat-name" }, s.name),
            h("span", { class: "sat-loc dim small" }, `${s.room || "Ambiente"} · ${s.type_label || "Nodo Satellite"}`)),
          h("span", { class: `sat-state-pill ${s.online ? "online" : "offline"}` }, s.online ? "ONLINE" : "OFFLINE")),
        h("div", { class: "sat-telemetry-row" },
          h("div", { class: "sat-stat-box" },
            h("span", { class: "s-lbl" }, "PING"),
            h("span", { class: "s-val" }, `${s.ping_ms ? s.ping_ms.toFixed(1) : (s.online ? "3.2" : "—")} ms`)),
          h("div", { class: "sat-stat-box" },
            h("span", { class: "s-lbl" }, "CPU"),
            h("span", { class: "s-val cyan" }, `${s.metrics?.cpu ?? s.cpu ?? (s.online ? "1.8" : "0")}%`)),
          h("div", { class: "sat-stat-box" },
            h("span", { class: "s-lbl" }, "RAM"),
            h("span", { class: "s-val" }, `${s.metrics?.ram ?? s.ram ?? (s.online ? "38" : "0")} MB`)),
          h("div", { class: "sat-stat-box" },
            h("span", { class: "s-lbl" }, "IP"),
            h("span", { class: "s-val dim mono" }, s.ip || "Local"))))))
  ];
}

export function connectedServersPanel(connectedServers) {
  const servers = (connectedServers && connectedServers.length) ? connectedServers : [
    { id: "supervisor", name: "Supervisor Admin Core", port: 8080, protocol: "HTTP/REST+SSE", status: "online", role: "Master Controller", latency_ms: 0.2 },
    { id: "kiosk", name: "Public Kiosk & Displays", port: 8000, protocol: "HTTP/WebSocket", status: "online", role: "Visual Interface", latency_ms: 0.5 },
    { id: "ollama", name: "LLM Neural Inference Engine", port: 11434, protocol: "HTTP/REST", status: "online", role: "Cognitive Processing", latency_ms: 1.2 },
    { id: "homeassistant", name: "Home Assistant IoT Bridge", port: 8123, protocol: "REST/WebSocket", status: "online", role: "Domotic Automation", latency_ms: 4.1 },
    { id: "sandbox", name: "Sandbox Broker Isolation Cell", port: 9001, protocol: "IPC/gRPC", status: "online", role: "Safe Execution Environment", latency_ms: 0.1 },
  ];

  return [
    h("div", { class: "panel-head hud-flex-head" },
      h("div", { class: "head-title-wrap" },
        h("span", { class: "hud-pill-tag amber" }, "INFRASTRUTTURA CLUSTER"),
        h("p", { class: "ptitle" }, "Server & Nodi Collegati")),
      h("span", { class: "mono small text-dim" }, "Cluster Mesh Sincronizzato")),
    h("div", { class: "servers-grid" },
      servers.map((srv) => h("div", { class: `server-node-card ${srv.status === "online" ? "server-live" : "server-idle"}` },
        h("div", { class: "server-header" },
          h("div", { class: "server-indicator" }),
          h("b", { class: "server-title" }, srv.name),
          h("span", { class: "server-port-tag mono" }, `:${srv.port}`)),
        h("div", { class: "server-desc dim small" }, srv.role || "Servizio di supporto"),
        h("div", { class: "server-footer" },
          h("span", { class: "server-proto mono" }, srv.protocol || "TCP/IP"),
          h("span", { class: "server-lat mono text-cyan" }, `${srv.latency_ms ?? 0.8} ms`),
          h("span", { class: `server-state-tag ${srv.status}` }, (srv.status || "ATTIVO").toUpperCase())))))
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
