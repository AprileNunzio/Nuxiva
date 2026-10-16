(() => {
  NuxivaDesk.register("study", {
    render(el, d, ctx) {
      el.innerHTML = `${ctx.head({ icon: "study", label: ctx.t("label"), title: d.level ? String(d.level).slice(0, 40) : "", chip: ctx.t("chip"), live: true })}
        <div class="wk-title">${ctx.esc(d.topic ? String(d.topic).slice(0, 80) : ctx.t("autonomous"))}</div>
        ${d.detail ? `<div class="wk-sub st-d">${ctx.esc(String(d.detail).slice(0, 240))}</div>` : ""}`;
    },
  });
})();
