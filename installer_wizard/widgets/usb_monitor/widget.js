(() => {
  NuxivaDesk.register("usb_monitor", {
    render(el, d, ctx) {
      el.innerHTML = `${ctx.head({ icon: "usb", label: ctx.t("label"), chip: ctx.t("chip"), live: true })}
        <div class="wk-hero"><span class="wk-num sm">${ctx.esc(d.size || "—")}</span><span class="wk-sub">${ctx.esc(d.vendor || "—")}</span></div>
        <dl class="wk-kv" style="margin-top:10px"><dt>${ctx.esc(ctx.t("mounted"))}</dt><dd class="mono">${ctx.esc(d.mount || "—")}</dd>
        <dt>${ctx.esc(ctx.t("product"))}</dt><dd>${ctx.esc(d.product || "—")}</dd><dt>${ctx.esc(ctx.t("serial"))}</dt><dd class="mono wk-faint">${ctx.esc(d.serial || "—")}</dd></dl>`;
    },
  });
})();
