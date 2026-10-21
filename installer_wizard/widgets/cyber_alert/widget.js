(() => {
  NuxivaDesk.register("cyber_alert", {
    render(el, d, ctx) {
      el.innerHTML = `${ctx.head({ icon: "shield", label: ctx.t("label"), title: d.title || ctx.t("fallback_title"), chip: String(d.threat_level || ctx.t("threat_default")).toLowerCase(), live: true, state: "bad" })}
        <dl class="wk-kv"><dt>${ctx.esc(ctx.t("origin"))}</dt><dd class="mono wk-accent">${ctx.esc(d.source_ip || "—")}</dd>
        <dt>${ctx.esc(ctx.t("attack"))}</dt><dd>${ctx.esc(d.attack_type || "—")}</dd>
        <dt>${ctx.esc(ctx.t("action"))}</dt><dd class="wk-accent">${ctx.esc(d.action_taken || "—")}</dd></dl>`;
    },
  });
})();
