(() => {
  const CODE = /^[a-z]{2,3}(?:[-_][A-Za-z]{2,4})?$/;

  NuxivaDesk.register("voices_ready", {
    render(el, raw, ctx) {
      const d = raw && typeof raw === "object" ? raw : {};
      const items = ctx.arr(d.items, 40).filter((i) => i && typeof i === "object").map((i) => {
        const code = ctx.str(i.code, 8);
        const count = ctx.num(i.count) ?? ctx.num(ctx.str(i.value, 30).match(/\d+/)?.[0]);
        return { label: ctx.pick(i, ["label", "name"], 40), code: CODE.test(code) ? code.slice(0, 2).toUpperCase() : "", count: count === null ? null : Math.max(0, Math.floor(count)), value: ctx.str(i.value, 40) };
      }).filter((i) => i.label);
      const voices = items.reduce((a, i) => a + (i.count || 0), 0);
      const head = ctx.head({ icon: "mic", label: ctx.t("label"), chip: items.length ? ctx.count("languages", items.length) : "" });
      if (!items.length) { el.innerHTML = `${head}${ctx.empty(ctx.tc("waiting"))}`; return; }
      const shown = items.slice(0, 12);
      const ex = items.find((i) => i.code && i.code !== "IT") || items[0];
      el.innerHTML = `${head}
        ${voices ? `<div class="vr-total"><b>${ctx.esc(ctx.fmt(voices))}</b><span>${ctx.esc(ctx.t("voices"))}</span></div>` : ""}
        <ul class="vr-grid">${shown.map((i, k) => `<li class="vr-lang${k === 0 ? " main" : ""}"><span class="vr-code mono">${ctx.esc(i.code || i.label.slice(0, 2).toUpperCase())}</span>
          <span class="vr-txt"><b>${ctx.esc(i.label)}</b><small>${ctx.esc(i.count !== null ? ctx.count("n_voices", i.count) : i.value)}</small></span></li>`).join("")}</ul>
        ${items.length > shown.length ? `<div class="wk-faint vr-more">${ctx.esc(ctx.t("more", { n: items.length - shown.length }))}</div>` : ""}
        <div class="vr-hint">${ctx.icon("chat")}<span>${ctx.esc(ctx.t("hint", { lang: ex.label.toLowerCase() }))}</span></div>`;
    },
  });
})();
