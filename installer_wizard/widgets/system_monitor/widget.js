(() => {
  const val = (v) => (v === undefined || v === null || v === "" || !Number.isFinite(Number(v)) ? null : Math.round(Math.max(0, Math.min(100, Number(v)))));
  NuxivaDesk.register("system_monitor", {
    render(el, d, ctx) {
      const cpu = val(d.cpu), ram = val(d.ram);
      const hot = (cpu ?? 0) > 80 || (ram ?? 0) > 85;
      el.innerHTML = `${ctx.head({ icon: "cpu", label: ctx.t("label"), chip: ctx.t(hot ? "loaded" : "nominal"), state: hot ? "warn" : "ok" })}
        <div class="wk-hero">${ctx.ring(cpu ?? 0, cpu === null ? "—" : `${cpu}%`, ctx.t("cpu"))}${ctx.ring(ram ?? 0, ram === null ? "—" : `${ram}%`, ctx.t("ram"))}</div>`;
    },
  });
})();
