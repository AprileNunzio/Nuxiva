(() => {
  NuxivaDesk.register("alert_info", {
    render(el, d, ctx) {
      el.innerHTML = `${ctx.head({ icon: "info", label: ctx.t("label") })}
        <div class="wk-title">${ctx.esc(String(d.title || ctx.t("fallback_title")).slice(0, 120))}</div>
        ${d.content ? `<div class="wk-sub">${ctx.esc(String(d.content).slice(0, 600))}</div>` : ""}`;
    },
  });
})();
