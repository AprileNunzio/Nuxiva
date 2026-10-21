(() => {
  NuxivaDesk.register("net_topology", {
    render(el, d, ctx) {
      el.innerHTML = `${ctx.head({ icon: "network", label: ctx.t("label"), title: ctx.t("title") })}
        <div class="wk-text">${d.content ? ctx.esc(String(d.content).slice(0, 600)) : ctx.esc(ctx.t("loading"))}</div>`;
    },
  });
})();
