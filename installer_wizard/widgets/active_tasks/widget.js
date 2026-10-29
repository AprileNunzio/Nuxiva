(() => {
  const STATES = new Set(["running", "queued", "waiting", "done", "failed"]);
  const ALIAS = { active: "running", working: "running", in_progress: "running", pending: "queued", todo: "queued", blocked: "waiting", paused: "waiting", ok: "done", completed: "done", error: "failed", ko: "failed" };
  const ICON = { running: "refresh", queued: "clock", waiting: "timer", done: "check", failed: "error" };
  const ORDER = { running: 0, failed: 1, waiting: 2, queued: 3, done: 4 };
  const LIMIT = 8;

  function normalize(raw, ctx, i) {
    if (typeof raw === "string" || typeof raw === "number") {
      const title = ctx.str(raw, 160);
      return title ? { title, state: i === 0 ? "running" : "queued", detail: "", progress: null, since: null } : null;
    }
    if (!raw || typeof raw !== "object") return null;
    const title = ctx.pick(raw, ["title", "name", "text", "task", "label"], 160);
    if (!title) return null;
    const s = ctx.str(raw.state || raw.status, 20).toLowerCase();
    const state = STATES.has(s) ? s : ALIAS[s] || (i === 0 ? "running" : "queued");
    const p = ctx.num(raw.progress ?? raw.percent);
    return {
      title,
      state,
      detail: ctx.pick(raw, ["detail", "agent", "step", "description"], 120),
      progress: p === null ? null : Math.max(0, Math.min(100, p <= 1 && String(raw.progress ?? raw.percent).includes(".") ? p * 100 : p)),
      since: ctx.stamp(raw.started_at ?? raw.since ?? raw.at),
    };
  }

  NuxivaDesk.register("active_tasks", {
    render(el, d, ctx) {
      const all = ctx.arr(d && d.tasks, 60).map((t, i) => normalize(t, ctx, i)).filter(Boolean)
        .map((t, i) => ({ ...t, i })).sort((a, b) => ORDER[a.state] - ORDER[b.state] || a.i - b.i);
      const running = all.filter((t) => t.state === "running").length;
      const open = all.filter((t) => t.state !== "done").length;
      const failed = all.some((t) => t.state === "failed");
      const shown = all.slice(0, LIMIT);
      const rows = shown.map((t) => {
        const meta = [t.detail, t.since ? ctx.ago(t.since) : ""].filter(Boolean).join(" · ");
        return `<li class="at-row at-${t.state}">
          <span class="at-ic" title="${ctx.esc(ctx.t(`state_${t.state}`))}">${ctx.icon(ICON[t.state])}</span>
          <span class="at-main"><b>${ctx.esc(t.title)}</b>${meta ? `<small>${ctx.esc(meta)}</small>` : ""}
          ${t.progress !== null ? ctx.bar(t.progress, t.state === "failed" ? "bad" : "") : ""}</span>
          ${t.progress !== null ? `<span class="wk-val">${Math.round(t.progress)}%</span>` : `<span class="at-state">${ctx.esc(ctx.t(`state_${t.state}`))}</span>`}
        </li>`;
      }).join("");
      const more = all.length - shown.length;
      el.innerHTML = `${ctx.head({ icon: "brain", label: ctx.t("label"), chip: open ? ctx.count("active", open) : all.length ? ctx.t("all_done") : "", live: running > 0, state: failed ? "bad" : open ? "" : "ok" })}
        ${rows ? `<ul class="at-list" role="list" aria-live="polite">${rows}</ul>${more > 0 ? `<div class="wk-sub at-more">${ctx.esc(ctx.count("more", more))}</div>` : ""}` : ctx.empty(ctx.t("idle"))}`;
    },
  });
})();
