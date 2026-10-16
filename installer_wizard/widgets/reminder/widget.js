(() => {
  NuxivaDesk.register("reminder", {
    render(el, d, ctx) {
      el.innerHTML = `${ctx.head({ icon: "bell", label: ctx.t("label"), chip: ctx.t("pending"), live: true })}
        <div class="wk-hero"><span class="wk-big">${ctx.icon("clock")}</span>
          <span class="wk-title">${ctx.esc(d.content ? String(d.content).slice(0, 200) : ctx.t("new"))}</span></div>`;
    },
  });
})();
