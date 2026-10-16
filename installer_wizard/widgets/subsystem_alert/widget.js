(() => {
  NuxivaDesk.register("subsystem_alert", {
    render(el, d, ctx) {
      const items = Array.isArray(d.items) ? d.items.slice(0, 8) : [];
      el.innerHTML = `${ctx.head({ icon: "alert", label: ctx.t("label"), title: ctx.t("title"), chip: ctx.count("faults", items.length), live: true, state: "bad" })}
        <ul class="wk-list">${items.map((i) => `<li class="wk-row bad"><span><b>${ctx.esc(i.label)}</b><small>${ctx.esc(i.detail)}</small></span><span></span></li>`).join("")}</ul>`;
    },
  });
})();
