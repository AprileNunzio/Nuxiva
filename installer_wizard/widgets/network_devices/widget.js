(() => {
  const clean = (s) => String(s ?? "").replace(/^[^\p{L}\p{N}]+/u, "").trim();
  NuxivaDesk.register("network_devices", {
    render(el, d, ctx) {
      const items = Array.isArray(d.items) ? d.items : [];
      const shown = items.slice(0, 10);
      el.innerHTML = `${ctx.head({ icon: "network", label: ctx.t("label"), chip: ctx.count("connected", items.length), live: items.length > 0 })}
        <ul class="wk-list">${shown.map((i) => `<li class="wk-row"><b>${ctx.esc(clean(i.label))}</b><span class="wk-val">${ctx.esc(i.value)}</span></li>`).join("")}</ul>
        ${items.length > shown.length ? `<div class="wk-sub wk-faint">${ctx.esc(ctx.t("more", { n: items.length - shown.length }))}</div>` : ""}`;
    },
  });
})();
