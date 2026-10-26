(() => {
  NuxivaDesk.register("context_window", {
    render(el, d, ctx) {
      el.innerHTML = `${ctx.head({ icon: "brain", label: ctx.t("label") })}${ctx.metrics(d.content)}`;
    },
  });
})();
