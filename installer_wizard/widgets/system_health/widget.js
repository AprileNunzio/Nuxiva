(() => {
  const ICON = { cpu: "cpu", memory: "memory", disk: "server", temperature: "therm" };
  NuxivaDesk.register("system_health", {
    render(el, d, ctx) {
      const items = Array.isArray(d.items) ? d.items.slice(0, 6) : [];
      const state = (p) => (p >= 90 ? "bad" : p >= 75 ? "warn" : "");
      el.innerHTML = `${ctx.head({ icon: "gauge", label: ctx.t("label"), title: ctx.t("title") })}
        ${items.length ? `<ul class="wk-list">${items.map((i) => `<li class="wk-row ic${state(i.percent) ? ` ${state(i.percent)}` : ""}">${ctx.icon(ICON[i.id] || "chip")}
          <span><b>${ctx.esc(i.id && ICON[i.id] ? ctx.t(`res_${i.id}`) : i.label)}</b>${ctx.bar(i.percent, state(i.percent))}</span><span class="wk-val">${ctx.esc(i.value)}</span></li>`).join("")}</ul>`
          : `${ctx.empty(ctx.t("unavailable"))}`}`;
    },
  });
})();
