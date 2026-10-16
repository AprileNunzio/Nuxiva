(() => {
  NuxivaDesk.register("audio_spectrum", {
    render(el, d, ctx) {
      const [first = "", ...rest] = ctx.lines(d.content, 4, 2000);
      el.innerHTML = `${ctx.head({ icon: "wave", label: ctx.t("label"), chip: first ? ctx.tc("live") : "", live: !!first })}
        <div class="as-bars" aria-hidden="true">${"<i></i>".repeat(48)}</div>
        ${first ? `<div class="wk-title">${ctx.esc(first)}</div>${rest.map((l) => `<div class="wk-sub">${ctx.esc(l)}</div>`).join("")}` : ctx.empty(ctx.t("silent"))}`;
    },
  });
})();
