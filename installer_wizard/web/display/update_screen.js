(function (global) {
  "use strict";

  const STAGES = Object.freeze(["check", "fetch", "verify_ci", "verify_signature", "snapshot", "apply", "integrity", "restart", "confirm"]);
  const STATUSES = Object.freeze(["pending", "running", "done", "skipped", "failed"]);
  const GLYPH = Object.freeze({ pending: "·", running: "›", done: "✓", skipped: "–", failed: "✕" });
  const REV = /^[0-9a-f]{7}$/;
  let root = null;

  function el(tag, cls, parent) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (parent) parent.appendChild(node);
    return node;
  }

  function build() {
    root = el("section", "upd-screen", document.body);
    root.id = "update-overlay";
    root.setAttribute("role", "status");
    root.setAttribute("aria-live", "polite");
    const wrap = el("div", "upd-wrap", root);
    const head = el("header", "upd-head", wrap);
    PageText.bind(el("p", "upd-kicker", head), "upd_kicker");
    PageText.bind(el("h2", "upd-title", head), "upd_title");
    el("p", "upd-revs", head).id = "upd-revs";
    const meter = el("div", "upd-meter", wrap);
    el("span", "upd-pct", meter).id = "upd-pct";
    PageText.bind(el("span", "upd-hint", meter), "upd_hint");
    const bar = el("div", "upd-bar", wrap);
    el("div", "upd-fill", bar).id = "upd-fill";
    bar.setAttribute("role", "progressbar");
    bar.setAttribute("aria-valuemin", "0");
    bar.setAttribute("aria-valuemax", "100");
    el("ol", "upd-stages", wrap).id = "upd-stages";
    el("p", "upd-message", wrap).id = "upd-message";
  }

  function stageRows(stages) {
    const list = document.getElementById("upd-stages");
    if (!list.childElementCount) {
      STAGES.forEach((id) => {
        const row = el("li", "upd-stage", list);
        row.dataset.stage = id;
        el("span", "upd-glyph", row);
        PageText.bind(el("span", "upd-name", row), `upd_stage_${id}`);
        el("span", "upd-state", row);
      });
    }
    const byId = new Map((stages || []).map((s) => [s.id, STATUSES.includes(s.status) ? s.status : "pending"]));
    list.querySelectorAll(".upd-stage").forEach((row) => {
      const status = byId.get(row.dataset.stage) || "pending";
      if (row.dataset.status === status) return;
      row.dataset.status = status;
      row.querySelector(".upd-glyph").textContent = GLYPH[status];
      PageText.bind(row.querySelector(".upd-state"), `upd_status_${status}`);
    });
  }

  function render(s) {
    if (!root) build();
    root.classList.remove("hidden");
    const run = s.update_progress || null;
    const pct = Math.min(100, Math.max(0, Math.round(run ? run.percent : s.progress || 0)));
    document.getElementById("upd-pct").textContent = `${pct}%`;
    document.getElementById("upd-fill").style.width = `${pct}%`;
    root.querySelector(".upd-bar").setAttribute("aria-valuenow", String(pct));
    const revs = document.getElementById("upd-revs");
    if (run && REV.test(run.from || "") && REV.test(run.to || "")) PageText.plain(revs, `${run.from} → ${run.to}`);
    else PageText.plain(revs, "");
    stageRows(run ? run.stages : []);
    root.classList.toggle("upd-failed", !!run && run.outcome === "failed");
    const msg = document.getElementById("upd-message");
    if (run && run.active) PageText.bind(msg, `upd_active_${run.active}`);
    else if (s.message) PageText.plain(msg, s.message);
    else PageText.bind(msg, "upd_waiting");
  }

  function clear() {
    if (root && !root.classList.contains("hidden")) root.classList.add("hidden");
  }

  function wanted(s) {
    if (s.phase === "UPDATING") return true;
    const run = s.update_progress;
    return !!run && !run.outcome && !["READY", "DEGRADED", "SETUP"].includes(s.phase) && ["restart", "confirm"].includes(run.active || "");
  }

  global.NuxivaUpdateScreen = Object.freeze({ render, clear, wanted });
})(window);
