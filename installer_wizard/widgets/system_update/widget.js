(() => {
  NuxivaDesk.register("system_update", {
    render(el, d, ctx) {
      const changes = Array.isArray(d.changes) ? d.changes.slice(0, 6) : [];
      el.innerHTML = `${ctx.head({ icon: "download", label: ctx.t("label"), chip: ctx.t("available"), live: true })}
        <dl class="wk-kv"><dt>${ctx.esc(ctx.t("installed"))}</dt><dd class="mono wk-faint">${ctx.esc(d.local || "—")}</dd><dt>${ctx.esc(ctx.t("new"))}</dt><dd class="mono wk-accent">${ctx.esc(d.remote || "—")}</dd></dl>
        ${changes.length ? `<ul class="wk-list">${changes.map((c) => `<li class="wk-row"><b>${ctx.esc(c)}</b><span></span></li>`).join("")}</ul>` : ""}`;
    },
  });
})();
