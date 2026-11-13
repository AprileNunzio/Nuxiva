(() => {
  const ALERTS = ["engine_unavailable", "decision_drift", "engine_errors", "memory_cold"];
  const obj = (v) => (v && typeof v === "object" ? v : {});

  function read(d, ctx) {
    const squad = obj(d.squad), engine = obj(d.engine), memory = obj(d.memory);
    const alerts = (Array.isArray(d.alerts) ? d.alerts : []).filter((a) => ALERTS.includes(a));
    return {
      agents: ctx.num(squad.agents), busy: ctx.num(squad.busy), persons: ctx.num(memory.persons),
      mode: ["python", "shadow", "rust"].includes(engine.mode) ? engine.mode : "", alerts,
    };
  }

  NuxivaDesk.register("team_health", {
    headline(d, ctx) {
      const c = read(obj(d), ctx);
      if (c.agents === null) return "";
      return c.alerts.length ? { text: ctx.t("say_attention"), tone: "warn" } : { text: ctx.t("say_fine"), tone: "ok" };
    },
    render(el, d, ctx) {
      const c = read(obj(d), ctx);
      const state = c.alerts.length ? "warn" : "";
      el.innerHTML = `${ctx.head({ icon: "brain", label: ctx.t("label"), chip: c.alerts.length ? ctx.t("attention") : "", state })}
        <div class="th-grid">
          <span class="wk-num sm">${ctx.esc(ctx.fmt(c.agents ?? 0))}<small> ${ctx.esc(ctx.t("agents"))}</small></span>
          <span class="wk-num sm">${ctx.esc(ctx.fmt(c.busy ?? 0))}<small> ${ctx.esc(ctx.t("busy"))}</small></span>
          <span class="wk-num sm">${ctx.esc(ctx.fmt(c.persons ?? 0))}<small> ${ctx.esc(ctx.t("people"))}</small></span>
        </div>
        ${c.alerts.length ? `<ul class="th-alerts">${c.alerts.map((a) => `<li>${ctx.esc(ctx.t(`alert_${a}`))}</li>`).join("")}</ul>` : ""}`;
    },
  });
})();
