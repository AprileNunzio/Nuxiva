(() => {
  NuxivaDesk.register("energy_chart", {
    render(el, d, ctx) {
      el.innerHTML = `${ctx.head({ icon: "bolt", label: ctx.t("label") })}${ctx.metrics(d.content)}`;
    },
  });
})();
