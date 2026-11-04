(() => {
  const STATE = { studying: ["chip", true, "", "brain"], paused: ["paused", false, "warn", "stop"], waiting: ["waiting", false, "", "clock"], idle: ["idle", false, "ok", "check"] };

  NuxivaDesk.register("study", {
    render(el, raw, ctx) {
      const d = raw && typeof raw === "object" ? raw : {};
      const [key, live, state, icon] = STATE[ctx.str(d.state, 20)] || STATE.studying;
      const topic = ctx.str(d.topic, 80);
      const n = Math.floor(ctx.num(d.level_n) || 0);
      const target = Math.max(n, Math.min(5, Math.floor(ctx.num(d.target) || 0)));
      const prog = ctx.num(d.progress);
      const pct = prog === null ? null : ctx.pct(prog <= 1 ? prog * 100 : prog);
      const mins = ctx.num(d.today_minutes);
      const cells = ctx.num(d.cells);
      const steps = n >= 1 && n <= 5 ? [1, 2, 3, 4, 5].map((i) => `<i class="${i < n ? "done" : i === n ? "now" : ""}${target && i === target ? " goal" : ""}"></i>`).join("") : "";
      el.innerHTML = `${ctx.head({ icon: "study", label: ctx.t("label"), title: ctx.str(d.level, 40), chip: ctx.t(key), live, state })}
        <div class="sd-top"><span class="sd-ic${live ? " live" : ""}">${ctx.icon(icon)}</span><span class="wk-title sd-topic">${ctx.esc(topic || ctx.t("autonomous"))}</span></div>
        ${steps ? `<div class="sd-levels" title="${ctx.esc(ctx.t("level_of", { n, total: 5 }))}">${steps}</div>` : ""}
        ${pct !== null && topic ? `<div class="sd-prog"><span>${ctx.esc(ctx.t("level_progress"))}</span><b class="mono">${Math.round(pct)}%</b></div>${ctx.bar(pct)}` : ""}
        ${d.detail ? `<div class="wk-sub sd-d">${ctx.esc(ctx.str(d.detail, 240))}</div>` : ""}
        ${mins !== null || cells !== null ? `<div class="sd-stats">${mins !== null ? `<span>${ctx.icon("clock")}${ctx.esc(ctx.t("today", { n: ctx.fmt(Math.max(0, mins)) }))}</span>` : ""}${cells !== null ? `<span>${ctx.icon("memory")}${ctx.esc(ctx.t("cells", { n: ctx.fmt(Math.max(0, cells)) }))}</span>` : ""}</div>` : ""}`;
    },
  });
})();
