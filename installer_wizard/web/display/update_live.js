(function (global) {
  "use strict";

  const TICK_MS = 1000;
  const LINK_STALE_MS = 15000;
  const SILENT_S = 30;
  const HEAVY_S = 120;
  const PKG = /^[a-z][a-z0-9-]{1,47}$/;
  const STAGE = /^[a-z_]{2,32}$/;
  const KNOWN_PKGS = Object.freeze(["nuxiva-native", "nuxiva-egress", "nuxiva-netguard", "nuxiva-bench", "nuxiva-agency", "nuxiva-display", "nuxiva-screenshot"]);
  const CONFIDENCE = Object.freeze(["low", "medium", "high"]);
  let panel = null;
  let refs = {};
  let timer = 0;
  let offsetMs = 0;
  let lastNow = 0;
  let model = { run: null, live: null };

  function el(tag, cls, parent) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (parent) parent.appendChild(node);
    return node;
  }

  function text(node, key, params) {
    const sig = `${key}|${JSON.stringify(params || {})}`;
    if (node.dataset.uplSig === sig) return;
    node.dataset.uplSig = sig;
    PageText.bind(node, key, params);
  }

  function plain(node, value) {
    const sig = `=${value}`;
    if (node.dataset.uplSig === sig) return;
    node.dataset.uplSig = sig;
    PageText.plain(node, value);
  }

  function clock(seconds) {
    const s = Math.max(0, Math.floor(Number.isFinite(seconds) ? seconds : 0));
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const ss = String(s % 60).padStart(2, "0");
    return h > 0 ? `${h}:${String(m).padStart(2, "0")}:${ss}` : `${m}:${ss}`;
  }

  function number(value) {
    const lang = document.documentElement.lang || undefined;
    try {
      return new Intl.NumberFormat(lang, { maximumFractionDigits: 1 }).format(value);
    } catch (_) {
      return String(Math.round(value * 10) / 10);
    }
  }

  function pkgKey(pkg) {
    return KNOWN_PKGS.includes(pkg) ? `upl_pkg_${pkg.replace(/-/g, "_")}` : "upl_pkg_other";
  }

  function tile(parent, labelKey) {
    const box = el("div", "upl-tile", parent);
    text(el("span", "upl-label", box), labelKey);
    const value = el("span", "upl-value", box);
    const sub = el("span", "upl-sub", box);
    return { box, value, sub };
  }

  function mount(parent, before) {
    panel = el("section", "upl hidden", null);
    parent.insertBefore(panel, before || null);
    refs.alert = el("p", "upl-alert hidden", panel);
    refs.alert.setAttribute("role", "alert");
    const grid = el("div", "upl-grid", panel);
    refs.elapsed = tile(grid, "upl_elapsed");
    text(refs.elapsed.sub, "upl_elapsed_sub");
    refs.phase = tile(grid, "upl_phase_time");
    refs.units = tile(grid, "upl_units");
    refs.bar = el("span", "upl-bar", refs.units.box);
    refs.barFill = el("span", "upl-bar-fill", refs.bar);
    refs.rate = tile(grid, "upl_rate");
    text(refs.rate.sub, "upl_rate_sub");
    refs.eta = tile(grid, "upl_eta");
    const phases = el("div", "upl-phases", panel);
    text(el("span", "upl-phases-title", phases), "upl_phases");
    refs.phases = el("ol", "upl-phase-list", phases);
  }

  function serverNow() {
    return (Date.now() + offsetMs) / 1000;
  }

  function sync(run, live) {
    if (live && Number.isFinite(live.now) && live.now !== lastNow) {
      lastNow = live.now;
      offsetMs = live.now * 1000 - Date.now();
    }
    model = { run: run || null, live: live || null };
    const show = !!(model.live || (model.run && Number.isFinite(model.run.started_at)));
    panel.classList.toggle("hidden", !show);
    if (show && !timer) timer = setInterval(paint, TICK_MS);
    if (!show) stop();
    if (show) paint();
    return show;
  }

  function stop() {
    if (timer) clearInterval(timer);
    timer = 0;
  }

  function linkSilence() {
    const last = global.NuxivaDelta && global.NuxivaDelta.lastFrameAt ? global.NuxivaDelta.lastFrameAt() : 0;
    return last ? Date.now() - last : 0;
  }

  function paintAlert(cur, now) {
    const link = linkSilence();
    let key = "";
    let params = {};
    let tone = "warn";
    if (link > LINK_STALE_MS) {
      key = "upl_link_lost";
      params = { time: clock(link / 1000) };
    } else if (cur && now - cur.last_beat > SILENT_S) {
      key = "upl_stall_silent";
      params = { time: clock(now - cur.last_beat) };
    } else if (cur && cur.crate && now - (cur.last_unit || cur.started) > HEAVY_S) {
      key = "upl_heavy";
      params = { crate: String(cur.crate).slice(0, 80), time: clock(now - (cur.last_unit || cur.started)) };
      tone = "info";
    }
    refs.alert.classList.toggle("hidden", !key);
    refs.alert.dataset.tone = tone;
    if (key) text(refs.alert, key, params);
  }

  function paintEta(cur, now) {
    const est = (cur && cur.estimate) || {};
    const drift = Math.max(0, now - (lastNow || now));
    if (est.remaining === 0) {
      text(refs.eta.value, "upl_eta_linking");
      text(refs.eta.sub, "upl_eta_linking_sub");
      return;
    }
    if (!Number.isFinite(est.eta)) {
      text(refs.eta.value, "upl_eta_learning");
      plain(refs.eta.sub, "");
      return;
    }
    const eta = est.eta - drift;
    if (eta <= 0) text(refs.eta.value, "upl_eta_soon");
    else text(refs.eta.value, "upl_eta_value", { eta: clock(eta) });
    const confidence = CONFIDENCE.includes(est.confidence) ? est.confidence : "low";
    refs.eta.box.dataset.confidence = confidence;
    text(refs.eta.sub, `upl_eta_range_${confidence}`, {
      low: clock(Math.max(0, est.eta_low - drift)),
      high: clock(Math.max(0, est.eta_high - drift)),
    });
  }

  function paintBuild(cur, now) {
    [refs.units.box, refs.rate.box, refs.eta.box].forEach((box) => box.classList.toggle("hidden", !cur));
    if (!cur) return;
    plain(refs.phase.value, clock(now - cur.started));
    text(refs.phase.sub, pkgKey(cur.pkg), { pkg: cur.pkg });
    const total = cur.total > 0 ? cur.total : 0;
    plain(refs.units.value, total ? `${cur.n}/${total}` : String(cur.n));
    refs.barFill.style.transform = `scaleX(${total ? Math.min(1, cur.n / total) : 0})`;
    if (cur.crate) text(refs.units.sub, "upl_crate", { crate: String(cur.crate).slice(0, 80) });
    else text(refs.units.sub, "upl_crate_wait");
    const rate = cur.estimate && Number.isFinite(cur.estimate.rate_per_min) ? cur.estimate.rate_per_min : null;
    if (rate === null) plain(refs.rate.value, "–");
    else text(refs.rate.value, "upl_rate_value", { rate: number(rate) });
    paintEta(cur, now);
  }

  function stageRows(run, now) {
    return (run && Array.isArray(run.stages) ? run.stages : [])
      .filter((s) => s && STAGE.test(s.id || "") && Number.isFinite(s.t0) && s.status !== "skipped")
      .map((s) => ({ key: `upd_stage_${s.id}`, params: {}, status: s.status, seconds: (Number.isFinite(s.t1) ? s.t1 : now) - s.t0 }));
  }

  function buildRows(live, now) {
    const rows = (live && Array.isArray(live.segments) ? live.segments : [])
      .filter((s) => s && PKG.test(s.pkg || ""))
      .map((s) => ({ key: pkgKey(s.pkg), params: { pkg: s.pkg }, status: s.status === "done" ? "done" : "failed", seconds: s.seconds }));
    const cur = live && live.current;
    if (cur && PKG.test(cur.pkg || "")) rows.push({ key: pkgKey(cur.pkg), params: { pkg: cur.pkg }, status: "running", seconds: now - cur.started });
    return rows;
  }

  function paintPhases(rows) {
    const list = refs.phases;
    while (list.children.length > rows.length) list.lastChild.remove();
    rows.forEach((row, i) => {
      let item = list.children[i];
      if (!item) {
        item = el("li", "upl-phase", list);
        el("span", "upl-phase-name", item);
        el("span", "upl-phase-time", item);
      }
      item.dataset.status = row.status;
      text(item.firstChild, row.key, row.params);
      plain(item.lastChild, clock(row.seconds));
    });
    list.parentElement.classList.toggle("hidden", rows.length === 0);
  }

  function paint() {
    if (!panel || panel.classList.contains("hidden")) return;
    const now = serverNow();
    const { run, live } = model;
    const cur = live && live.current && PKG.test(live.current.pkg || "") ? live.current : null;
    const started = run && Number.isFinite(run.started_at) ? run.started_at : cur ? cur.started : now;
    plain(refs.elapsed.value, clock(now - started));
    refs.phase.box.classList.toggle("hidden", !cur);
    paintBuild(cur, now);
    paintAlert(cur, now);
    paintPhases([...stageRows(run, now), ...buildRows(live, now)]);
  }

  function hide() {
    stop();
    if (panel) panel.classList.add("hidden");
  }

  global.NuxivaUpdateLive = Object.freeze({ mount, sync, hide, clock });
})(window);
