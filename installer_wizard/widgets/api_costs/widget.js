(() => {
  NuxivaDesk.register("api_costs", {
    render(el, d, ctx) {
      el.innerHTML = `${ctx.head({ icon: "coin", label: ctx.t("label") })}${ctx.metrics(d.content)}`;
    },
  });
})();
