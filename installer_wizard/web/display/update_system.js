(function (global) {
  "use strict";

  const SVG = "http://www.w3.org/2000/svg";
  const STEPS = Object.freeze(["update", "upgrade"]);
  const STEP_STATES = Object.freeze(["pending", "running", "done", "failed"]);
  const KINDS = Object.freeze(["fetch", "read", "summary", "unpack", "setup", "trigger", "warn", "error", "other"]);
  const EXIT_MS = 1700;
  const RING = 2 * Math.PI * 88;
  const MAX_LINES = 14;
  const ID = /^[0-9a-f]{12}$/;
  let layer = null;
  let refs = {};
  let seen = { id: "", status: "" };
  let exitUntil = 0;
  let exitTimer = 0;

  function el(tag, cls, parent) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (parent) parent.appendChild(node);
    return node;
  }

  function svg(tag, attrs, parent) {
    const node = document.createElementNS(SVG, tag);
    Object.entries(attrs).forEach(([k, v]) => node.setAttribute(k, String(v)));
    if (parent) parent.appendChild(node);
    return node;
  }

  function core(parent) {
    const wrap = el("div", "ups-core", parent);
    const art = svg("svg", { viewBox: "0 0 200 200", "aria-hidden": "true", class: "ups-ring" }, wrap);
    svg("circle", { cx: 100, cy: 100, r: 96, class: "ups-orbit ups-orbit-a" }, art);
    svg("circle", { cx: 100, cy: 100, r: 78, class: "ups-orbit ups-orbit-b" }, art);
    svg("circle", { cx: 100, cy: 100, r: 88, class: "ups-track" }, art);
    refs.arc = svg("circle", { cx: 100, cy: 100, r: 88, class: "ups-arc", "stroke-dasharray": RING, "stroke-dashoffset": RING }, art);
    refs.comet = svg("circle", { cx: 100, cy: 12, r: 3.2, class: "ups-comet" }, art);
    const center = el("div", "ups-center", wrap);
    refs.pct = el("span", "ups-pct", center);
    refs.stepLabel = el("span", "ups-step-label", center);
    refs.pkg = el("span", "ups-pkg", center);
  }

  function stat(parent, key) {
    const box = el("div", "ups-stat", parent);
    const value = el("span", "ups-stat-value", box);
    PageText.bind(el("span", "ups-stat-label", box), key);
    return value;
  }

  function build(root) {
    layer = el("div", "ups-layer hidden", root);
    layer.setAttribute("aria-live", "polite");
    el("div", "ups-grid", layer);
    el("div", "ups-beam", layer);
    const head = el("div", "ups-head", layer);
    PageText.bind(el("p", "ups-phase", head), "ups_phase");
    PageText.bind(el("h2", "ups-title", head), "ups_title");
    PageText.bind(el("p", "ups-sub", head), "ups_subtitle");
    const body = el("div", "ups-body", layer);
    const left = el("div", "ups-left", body);
    core(left);
    const chips = el("ol", "ups-chips", left);
    refs.chips = STEPS.map((id, i) => {
      const chip = el("li", "ups-chip", chips);
      chip.dataset.step = id;
      PageText.plain(el("span", "ups-chip-n", chip), String(i + 1).padStart(2, "0"));
      PageText.bind(el("span", "ups-chip-name", chip), `ups_step_${id}`);
      refs[`chipState_${id}`] = el("span", "ups-chip-state", chip);
      return chip;
    });
    const stats = el("div", "ups-stats", left);
    refs.fetched = stat(stats, "ups_stat_sources");
    refs.total = stat(stats, "ups_stat_packages");
    refs.unpacked = stat(stats, "ups_stat_unpacked");
    refs.configured = stat(stats, "ups_stat_configured");
    const term = el("div", "ups-term", body);
    const bar = el("div", "ups-term-bar", term);
    ["r", "y", "g"].forEach((c) => el("span", `ups-dot ups-dot-${c}`, bar));
    PageText.bind(el("span", "ups-term-title", bar), "ups_console");
    refs.alerts = el("span", "ups-term-alerts", bar);
    refs.lines = el("ol", "ups-lines", term);
    refs.lines.setAttribute("role", "log");
    refs.outcome = el("p", "ups-outcome", layer);
  }

  function num(value) {
    const n = Number(value);
    return Number.isFinite(n) && n >= 0 ? Math.floor(n) : 0;
  }

  function lines(items) {
    const list = Array.isArray(items) ? items.slice(-MAX_LINES) : [];
    const box = refs.lines;
    while (box.children.length > list.length) box.removeChild(box.firstChild);
    while (box.children.length < list.length) el("li", "ups-line", box);
    list.forEach((item, i) => {
      const row = box.children[i];
      const kind = item && KINDS.includes(item.k) ? item.k : "other";
      const text = item && typeof item.t === "string" ? item.t.slice(0, 240) : "";
      row.dataset.kind = kind;
      row.classList.toggle("ups-line-now", i === list.length - 1);
      if (row.textContent !== text) PageText.plain(row, text);
    });
  }

  function steps(data) {
    STEPS.forEach((id) => {
      const raw = data.steps && data.steps[id];
      const state = STEP_STATES.includes(raw) ? raw : "pending";
      const chip = refs.chips[STEPS.indexOf(id)];
      chip.dataset.state = state;
      PageText.bind(refs[`chipState_${id}`], `ups_state_${state}`);
    });
  }

  function paint(data) {
    const pct = Math.min(100, num(data.percent));
    refs.arc.setAttribute("stroke-dashoffset", String(RING * (1 - pct / 100)));
    refs.comet.style.transform = `rotate(${pct * 3.6}deg)`;
    PageText.plain(refs.pct, `${pct}%`);
    const step = STEPS.includes(data.step) ? data.step : "update";
    PageText.bind(refs.stepLabel, `ups_active_${step}`);
    const pkg = typeof data.package === "string" ? data.package.slice(0, 100) : "";
    PageText.plain(refs.pkg, pkg);
    const summary = data.summary && typeof data.summary === "object" ? data.summary : null;
    PageText.plain(refs.fetched, String(num(data.fetched)));
    PageText.plain(refs.total, summary ? String(num(summary.upgraded) + num(summary.installed)) : "—");
    PageText.plain(refs.unpacked, String(num(data.unpacked)));
    PageText.plain(refs.configured, String(num(data.configured)));
    const warn = num(data.warnings) + num(data.errors);
    if (warn) PageText.bind(refs.alerts, "ups_alerts", { count: warn });
    else PageText.plain(refs.alerts, "");
    steps(data);
    lines(data.lines);
    layer.dataset.status = data.status;
    if (data.status === "done") PageText.bind(refs.outcome, "ups_outcome_done");
    else if (data.status === "failed") PageText.bind(refs.outcome, "ups_outcome_failed");
    else PageText.plain(refs.outcome, "");
  }

  function hide() {
    if (!layer) return;
    layer.classList.add("hidden");
    layer.classList.remove("ups-exit");
    exitUntil = 0;
  }

  function sync(root, data) {
    if (!layer || !root.contains(layer)) build(root);
    const valid = data && typeof data === "object" && ID.test(data.id || "");
    if (!valid) {
      hide();
      return false;
    }
    const wasRunning = seen.id === data.id && seen.status === "running";
    seen = { id: data.id, status: data.status };
    if (data.status === "running") {
      clearTimeout(exitTimer);
      layer.classList.remove("hidden", "ups-exit");
      exitUntil = 0;
      paint(data);
      return true;
    }
    if (wasRunning && ["done", "failed"].includes(data.status)) {
      paint(data);
      layer.classList.remove("hidden");
      layer.classList.add("ups-exit");
      exitUntil = Date.now() + EXIT_MS;
      clearTimeout(exitTimer);
      exitTimer = setTimeout(() => {
        hide();
        if (root.classList) root.classList.remove("upd-system-mode");
        root.classList.add("upd-system-after");
        setTimeout(() => root.classList.remove("upd-system-after"), 1200);
      }, EXIT_MS);
      return true;
    }
    if (exitUntil > Date.now()) return true;
    hide();
    return false;
  }

  global.NuxivaUpdateSystem = Object.freeze({ sync, hide });
})(window);
