(function (global) {
  "use strict";

  const STAGES = Object.freeze(["check", "fetch", "verify_ci", "verify_signature", "snapshot", "apply", "integrity", "restart", "confirm"]);
  const STATUSES = Object.freeze(["pending", "running", "done", "skipped", "failed"]);
  const GLYPH = Object.freeze({ pending: "·", running: "›", done: "✓", skipped: "–", failed: "✕" });
  const REV = /^[0-9a-f]{7}$/;
  const LANGS = Object.freeze(["it", "en", "fr", "es"]);
  const NOTE_LIMIT = 5;
  const NOTE_MAX = 320;
  let root = null;
  let notesKey = "";

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
    el("p", "upd-detail", wrap).id = "upd-detail";
    const notes = el("section", "upd-notes hidden", wrap);
    notes.id = "upd-notes";
    PageText.bind(el("h3", "upd-notes-title", notes), "upd_notes_title");
    ["features", "fixes"].forEach((kind) => {
      const group = el("div", "upd-notes-group", notes);
      group.dataset.kind = kind;
      PageText.bind(el("h4", "upd-notes-kind", group), `upd_notes_${kind}`);
      el("ul", "upd-notes-list", group);
      el("p", "upd-notes-more", group);
    });
  }

  function pick(item, lang) {
    if (!item || typeof item !== "object") return "";
    const value = [lang, "en", "it"].map((key) => item[key]).find((v) => typeof v === "string" && v.trim());
    return value ? value.trim().slice(0, NOTE_MAX) : "";
  }

  function noteRows(notes) {
    const box = document.getElementById("upd-notes");
    const lang = LANGS.includes((document.documentElement.lang || "").slice(0, 2)) ? document.documentElement.lang.slice(0, 2) : "en";
    const valid = notes && typeof notes === "object" ? notes : null;
    const key = valid ? `${lang}:${JSON.stringify(valid)}` : "";
    if (key === notesKey) return;
    notesKey = key;
    let any = false;
    box.querySelectorAll(".upd-notes-group").forEach((group) => {
      const kind = group.dataset.kind;
      const items = valid && Array.isArray(valid[kind]) ? valid[kind].map((item) => pick(item, lang)).filter(Boolean) : [];
      const total = valid && Number.isInteger(valid[`total_${kind}`]) ? Math.max(valid[`total_${kind}`], items.length) : items.length;
      const list = group.querySelector(".upd-notes-list");
      list.replaceChildren();
      items.slice(0, NOTE_LIMIT).forEach((text) => PageText.plain(el("li", "upd-notes-item", list), text));
      const more = group.querySelector(".upd-notes-more");
      const rest = total - Math.min(items.length, NOTE_LIMIT);
      if (rest > 0) PageText.bind(more, "upd_notes_more", { count: rest });
      else PageText.plain(more, "");
      group.classList.toggle("hidden", items.length === 0);
      any = any || items.length > 0;
    });
    box.classList.toggle("hidden", !any);
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
    noteRows(run ? run.notes : null);
    root.classList.toggle("upd-failed", !!run && run.outcome === "failed");
    const msg = document.getElementById("upd-message");
    if (run && run.active) PageText.bind(msg, `upd_active_${run.active}`);
    else if (s.message) PageText.plain(msg, s.message);
    else PageText.bind(msg, "upd_waiting");
    const live = run && ["restart", "confirm"].includes(run.active || "") ? String(s.message || "").slice(0, 200) : "";
    PageText.plain(document.getElementById("upd-detail"), live);
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
