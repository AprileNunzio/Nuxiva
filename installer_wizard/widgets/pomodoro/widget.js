(() => {
  NuxivaDesk.register("pomodoro", {
    render(el, d, ctx) {
      el.innerHTML = `${ctx.head({ icon: "tomato", label: ctx.t("label"), title: ctx.t("title") })}
        <div class="wk-text">${ctx.esc(d.content ? String(d.content).slice(0, 400) : ctx.t("preparing"))}</div>`;
    },
  });
})();
