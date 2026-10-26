(() => {
  NuxivaDesk.register("crypto_ticker", {
    render(el, d, ctx) {
      el.innerHTML = `${ctx.head({ icon: "trend", label: ctx.t("label") })}${ctx.metrics(d.content)}`;
    },
  });
})();
