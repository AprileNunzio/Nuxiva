(() => {
  NuxivaDesk.register("thermostat", {
    render(el, d, ctx) {
      const cur = Number(d.current), target = Number(d.target);
      const fill = Number.isFinite(cur) ? ((cur - 10) / 20) * 100 : 0;
      el.innerHTML = `${ctx.head({ icon: "therm", label: ctx.t("label"), title: d.room || "", chip: d.status || ctx.t("standby"), live: !!d.status })}
        <div class="wk-hero" style="align-items:center">${ctx.ring(fill, Number.isFinite(cur) ? `${cur}°` : "—", ctx.t("now"))}
          <dl class="wk-kv" style="flex:1"><dt>${ctx.esc(ctx.t("target"))}</dt><dd class="mono">${Number.isFinite(target) ? `${target}°` : "—"}</dd>
          <dt>${ctx.esc(ctx.t("humidity"))}</dt><dd>${ctx.esc(d.humidity ?? "—")}%</dd></dl></div>`;
    },
  });
})();
