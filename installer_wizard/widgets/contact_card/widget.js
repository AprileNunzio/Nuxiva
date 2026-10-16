(() => {
  NuxivaDesk.register("contact_card", {
    render(el, d, ctx) {
      const name = String(d.name || "");
      el.innerHTML = `${ctx.head({ icon: "contact", label: ctx.t("label") })}
        <div class="wk-hero cc-hero"><span class="cc-ini">${name ? ctx.esc(name.charAt(0).toUpperCase()) : ctx.icon("user")}</span>
          <span><div class="wk-title">${ctx.esc(name || ctx.t("unknown"))}</div>
          <div class="wk-sub">${ctx.esc(d.company || "")}</div></span></div>
        <dl class="wk-kv cc-kv"><dt>${ctx.esc(ctx.t("phone"))}</dt><dd class="mono wk-accent">${ctx.esc(d.phone || ctx.t("no_number"))}</dd>
        ${d.email ? `<dt>${ctx.esc(ctx.t("email"))}</dt><dd class="wk-faint">${ctx.esc(d.email)}</dd>` : ""}</dl>`;
    },
  });
})();
