(() => {
  const ICON = { done: "✓", running: "●", waiting: "⏸", failed: "✕", pending: "○" };
  NuxivaDesk.register("project_status", {
    render(el, d, ctx) {
      const steps = (Array.isArray(d.steps) ? d.steps : []).slice(0, 12);
      const state = d.status === "failed" ? "bad" : d.status === "done" ? "ok" : "";
      const rows = steps.map((s) => `<li class="wk-row ${ctx.esc(s.status)}"><span>${ICON[s.status] || "○"}</span><span><b>${ctx.esc(String(s.text).slice(0, 120))}</b>${s.expert ? `<small>${ctx.esc(s.expert)}</small>` : ""}</span></li>`).join("");
      el.innerHTML = `${ctx.head({ icon: "board", label: ctx.t("label"), title: String(d.title || "").slice(0, 80), chip: ctx.t(`status_${d.status}`), live: d.status === "running", state })}
        <div class="wk-hero"><span class="wk-num sm">${Number(d.progress) || 0}%</span><span class="wk-sub">${ctx.esc(ctx.t("steps_done", { done: d.done || 0, total: d.total || 0 }))}</span></div>${ctx.bar(Number(d.progress) || 0, state)}
        ${d.expert ? `<div class="wk-faint">${ctx.esc(d.expert)} · ${ctx.esc(String(d.current).slice(0, 100))}</div>` : ""}
        ${d.error ? `<div class="wk-faint">${ctx.esc(String(d.error).slice(0, 200))}</div>` : ""}
        ${rows ? `<ul class="wk-list">${rows}</ul>` : ctx.empty(ctx.t("planning"))}`;
    },
  });
})();
