(() => {
  const ICON = { done: "✓", running: "●", waiting: "⏸", failed: "✕", pending: "○" };
  const ACTIONS = { running: ["pause", "cancel"], planning: ["pause", "cancel"], paused: ["resume", "cancel"], failed: ["retry"] };
  const control = (id, action) => fetch(`/api/projects/${encodeURIComponent(id)}/control/${action}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" }).catch(() => {});
  const studio = (id) => fetch(`/api/models3d/${encodeURIComponent(id)}/studio/open`, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" }).catch(() => {});

  NuxivaDesk.register("project_status", {
    render(el, d, ctx) {
      const actions = (ACTIONS[d.status] || []).map((a) => `<button type="button" class="wk-btn" data-act="${a}">${ctx.esc(ctx.t(`action_${a}`))}</button>`).join("");
      const model = d.model_id ? `<button type="button" class="wk-btn" data-studio="1">${ctx.icon("cube")} ${ctx.esc(ctx.t("open_studio"))}</button>` : "";
      const steps = (Array.isArray(d.steps) ? d.steps : []).slice(0, 12);
      const state = d.status === "failed" ? "bad" : d.status === "done" ? "ok" : "";
      const rows = steps.map((s) => `<li class="wk-row ${ctx.esc(s.status)}"><span>${ICON[s.status] || "○"}</span><span><b>${ctx.esc(String(s.text).slice(0, 120))}</b>${s.expert ? `<small>${ctx.esc(s.expert)}</small>` : ""}</span></li>`).join("");
      el.innerHTML = `${ctx.head({ icon: "board", label: ctx.t("label"), title: String(d.title || "").slice(0, 80), chip: ctx.t(`status_${d.status}`), live: d.status === "running", state })}
        <div class="wk-hero"><span class="wk-num sm">${Number(d.progress) || 0}%</span><span class="wk-sub">${ctx.esc(ctx.t("steps_done", { done: d.done || 0, total: d.total || 0 }))}</span></div>${ctx.bar(Number(d.progress) || 0, state)}
        ${d.expert ? `<div class="wk-faint">${ctx.esc(d.expert)} · ${ctx.esc(String(d.current).slice(0, 100))}</div>` : ""}
        ${d.error ? `<div class="wk-faint">${ctx.esc(String(d.error).slice(0, 200))}</div>` : ""}
        ${rows ? `<ul class="wk-list">${rows}</ul>` : ctx.empty(ctx.t("planning"))}
        ${actions || model ? `<div class="wk-actions">${actions}${model}</div>` : ""}`;
      el.onclick = (e) => {
        const b = e.target.closest("button");
        if (!b) return;
        if (b.dataset.act) control(d.id, b.dataset.act);
        if (b.dataset.studio) studio(d.model_id);
      };
    },
  });
})();
