(() => {
  NuxivaDesk.register("lan_device", {
    render(el, d, ctx) {
      el.innerHTML = `${ctx.head({ icon: "lan", label: ctx.t("label"), title: d.hostname || "", chip: ctx.t("chip"), live: true })}
        <dl class="wk-kv"><dt>IP</dt><dd class="mono">${ctx.esc(d.ip || "—")}</dd><dt>MAC</dt><dd class="mono wk-faint">${ctx.esc(d.mac || "—")}</dd>
        <dt>${ctx.esc(ctx.t("vendor"))}</dt><dd>${ctx.esc(d.vendor || "—")}</dd></dl>`;
    },
  });
})();
