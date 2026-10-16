(() => {
  NuxivaDesk.register("thinking_tree", {
    render(el, d, ctx) {
      const lines = ctx.plain(d.content, 8000).split("\n").map((l) => l.replace(/\s+$/, "")).filter((l) => l.trim()).slice(0, 24);
      const out = lines.map((l) => (/^\S/.test(l) || /[✓✔]/.test(l) ? `<em>${ctx.esc(l)}</em>` : ctx.esc(l))).join("\n");
      el.innerHTML = `${ctx.head({ icon: "tree", label: ctx.t("label"), chip: lines.length ? ctx.count("steps", lines.length) : "" })}
        ${out ? `<pre class="wk-pre">${out}</pre>` : `${ctx.empty(ctx.tc("waiting"))}`}`;
    },
  });
})();
