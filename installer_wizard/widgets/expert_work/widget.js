(() => {
  const STATUS = new Set(["thinking", "working", "waiting", "done"]);
  const color = (c) => (/^#[0-9a-f]{6}$/i.test(c || "") ? c : "#29e0ff");
  NuxivaDesk.register("expert_work", {
    render(el, d, ctx) {
      const status = STATUS.has(d.status) ? d.status : "thinking";
      const steps = Array.isArray(d.steps) ? d.steps.slice(-8) : [];
      const busy = status === "thinking" || status === "working";
      el.innerHTML = `${ctx.head({ icon: "brain", label: ctx.t("label"), chip: ctx.t(`status_${status}`), live: busy })}
        <div class="ew-who" style="--ew:${color(d.color)}">
          <span class="ew-avatar${busy ? " busy" : ""}">${ctx.esc(d.icon || "◆")}</span>
          <div><b>${ctx.esc(d.name || "")}</b><small>${ctx.esc(d.role || "")}</small></div>
        </div>
        ${d.question ? `<div class="ew-q"><span>${ctx.esc(ctx.t("question"))}</span>${ctx.esc(d.question)}</div>` : ""}
        ${steps.length ? `<div class="ew-steps" aria-label="${ctx.esc(ctx.t("steps"))}">${steps.map((s) => `<span class="${s.ok ? "ok" : "ko"}">${ctx.esc(s.tool || "")}</span>`).join("")}</div>` : ""}
        ${status === "done" && d.answer ? `<div class="ew-a"><span>${ctx.esc(ctx.t("answer"))}</span>${ctx.esc(d.answer)}</div>` : ""}`;
    },
  });
})();
