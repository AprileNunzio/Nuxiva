(() => {
  NuxivaDesk.register("vram_allocator", {
    render(el, d, ctx) {
      el.innerHTML = `${ctx.head({ icon: "memory", label: ctx.t("label") })}${ctx.metrics(d.content)}`;
    },
  });
})();
