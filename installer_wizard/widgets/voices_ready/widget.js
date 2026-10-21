(() => {
  NuxivaDesk.register("voices_ready", {
    render(el, d, ctx) {
      const items = Array.isArray(d.items) ? d.items.slice(0, 10) : [];
      el.innerHTML = `${ctx.head({ icon: "mic", label: ctx.t("label"), chip: ctx.count("languages", items.length) })}
        <ul class="wk-list">${items.map((i) => `<li class="wk-row"><b>${ctx.esc(i.label)}</b><span class="wk-val">${ctx.esc(i.value)}</span></li>`).join("")}</ul>`;
    },
  });
})();
