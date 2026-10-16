(() => {
  NuxivaDesk.register("people_seen", {
    render(el, d, ctx) {
      const items = (Array.isArray(d.items) ? d.items : []).filter((i) => i && i.label && !i.none).slice(0, 8);
      el.innerHTML = `${ctx.head({ icon: "eye", label: ctx.t("label") })}
        ${items.length ? `<ul class="wk-list">${items.map((i) => `<li class="wk-row ic${i.status === "ok" ? " on" : ""}">${ctx.icon(i.status === "ok" ? "user" : "users")}
          <b>${ctx.esc(i.label)}</b><span class="wk-val">${ctx.esc(i.value)}</span></li>`).join("")}</ul>`
          : ctx.empty(ctx.t("none"))}`;
    },
  });
})();
