(() => {
  NuxivaDesk.register("alert_error", {
    render(el, d, ctx) {
      el.innerHTML = `${ctx.head({ icon: "error", label: ctx.t("label"), chip: ctx.t("chip"), live: true, state: "bad" })}
        <div class="wk-title">${ctx.esc(String(d.title || ctx.t("fallback_title")).slice(0, 120))}</div>
        ${d.content ? `<div class="wk-text wk-faint">${ctx.esc(String(d.content).slice(0, 600))}</div>` : ""}`;
    },
  });
})();
