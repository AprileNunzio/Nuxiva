(function (global) {
  "use strict";

  const STAGES = Object.freeze(["check", "fetch", "verify_ci", "verify_signature", "snapshot", "apply", "integrity", "restart", "confirm"]);
  const STATUSES = Object.freeze(["pending", "running", "done", "skipped", "failed"]);
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
    const top = el("div", "upd-top", root);
    const brand = el("p", "upd-brand", top);
    el("span", "upd-pulse", brand);
    PageText.bind(el("span", "", brand), "upd_kicker");
    el("p", "upd-revs", top).id = "upd-revs";
    const main = el("div", "upd-main", root);
    global.NuxivaUpdateNotes.mount(main);
    const foot = el("div", "upd-foot", root);
    const line = el("div", "upd-foot-line", foot);
    el("span", "upd-pct", line).id = "upd-pct";
    const now = el("span", "upd-now", line);
    el("span", "upd-step", now).id = "upd-step";
    el("span", "upd-message", now).id = "upd-message";
    PageText.bind(el("span", "upd-hint", line), "upd_hint");
    const track = el("ol", "upd-track", foot);
    track.id = "upd-track";
    track.setAttribute("role", "progressbar");
    track.setAttribute("aria-valuemin", "0");
    track.setAttribute("aria-valuemax", "100");
    STAGES.forEach((id) => {
      const seg = el("li", "upd-seg", track);
      seg.dataset.stage = id;
      el("span", "upd-seg-fill", seg);
    });
    el("p", "upd-detail", foot).id = "upd-detail";
  }

  function stageRows(stages) {
    const byId = new Map((stages || []).map((s) => [s.id, STATUSES.includes(s.status) ? s.status : "pending"]));
    let current = "";
    root.querySelectorAll(".upd-seg").forEach((seg) => {
      const status = byId.get(seg.dataset.stage) || "pending";
      seg.dataset.status = status;
      if (status === "running" || (status === "failed" && !current)) current = seg.dataset.stage;
    });
    return current;
  }

  function progress(run, s) {
    const pct = Math.min(100, Math.max(0, Math.round(run ? run.percent : s.progress || 0)));
    document.getElementById("upd-pct").textContent = `${pct}%`;
    document.getElementById("upd-track").setAttribute("aria-valuenow", String(pct));
    const current = stageRows(run ? run.stages : []);
    const step = document.getElementById("upd-step");
    if (current) PageText.bind(step, "upd_step", { n: STAGES.indexOf(current) + 1, total: STAGES.length });
    else PageText.plain(step, "");
    const msg = document.getElementById("upd-message");
    if (run && run.active) PageText.bind(msg, `upd_active_${run.active}`);
    else if (s.message) PageText.plain(msg, String(s.message).slice(0, 200));
    else PageText.bind(msg, "upd_waiting");
    const live = run && ["restart", "confirm"].includes(run.active || "") ? String(s.message || "").slice(0, 200) : "";
    PageText.plain(document.getElementById("upd-detail"), live);
  }

  function ready(run) {
    if (!run || !Array.isArray(run.stages)) return false;
    return run.stages.some((st) => st && st.id === "check" && ["done", "skipped", "failed"].includes(st.status)) || !!run.outcome;
  }

  function render(s) {
    if (!root) build();
    const back = root.classList.contains("hidden");
    root.classList.remove("hidden");
    if (global.NuxivaResources) global.NuxivaResources.claim("update");
    const run = s.update_progress || null;
    const revs = document.getElementById("upd-revs");
    if (run && REV.test(run.from || "") && REV.test(run.to || "")) PageText.plain(revs, `${run.from} → ${run.to}`);
    else PageText.plain(revs, "");
    root.classList.toggle("upd-failed", !!run && run.outcome === "failed");
    progress(run, s);
    global.NuxivaUpdateNotes.update(run ? run.notes : null, ready(run));
    if (back) global.NuxivaUpdateNotes.relayout();
  }

  function clear() {
    if (!root || root.classList.contains("hidden")) return;
    root.classList.add("hidden");
    if (global.NuxivaResources) global.NuxivaResources.release("update");
    global.NuxivaUpdateNotes.stop();
  }

  function wanted(s) {
    if (s.phase === "UPDATING") return true;
    const run = s.update_progress;
    return !!run && !run.outcome && !["READY", "DEGRADED", "SETUP"].includes(s.phase) && ["restart", "confirm"].includes(run.active || "");
  }

  global.NuxivaUpdateScreen = Object.freeze({ render, clear, wanted });
})(window);
