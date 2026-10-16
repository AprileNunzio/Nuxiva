(() => {
  NuxivaDesk.register("cam_stream", {
    render(el, d, ctx) {
      const motion = !!d.motion_detected;
      el.innerHTML = `${ctx.head({ icon: "camera", label: ctx.t("label"), title: d.camera || "", chip: ctx.t(motion ? "chip_motion" : "chip_listening"), live: true, state: motion ? "bad" : "" })}
        <div class="wk-media cs-feed"><span class="wk-faint wk-mono">${ctx.esc(ctx.t("no_stream"))}</span></div>
        <dl class="wk-kv cs-kv"><dt>${ctx.esc(ctx.t("source"))}</dt><dd>${ctx.esc(d.camera || "—")}</dd>
        <dt>${ctx.esc(ctx.t("state"))}</dt><dd class="${motion ? "wk-accent" : "wk-faint"}">${ctx.esc(ctx.t(motion ? "motion" : "no_motion"))}</dd></dl>`;
    },
  });
})();
