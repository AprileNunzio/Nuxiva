(() => {
  const IP = /\b(?:\d{1,3}\.){3}\d{1,3}\b/g;
  NuxivaDesk.register("firewall_logs", {
    render(el, d, ctx) {
      const lines = ctx.lines(d.content, 14, 8000);
      const out = lines.map((l) => ctx.esc(l).replace(IP, (m) => `<em>${m}</em>`)).join("\n");
      el.innerHTML = `${ctx.head({ icon: "shield", label: ctx.t("label"), chip: lines.length ? ctx.count("blocked", lines.length) : "", live: lines.length > 0, state: "bad" })}
        ${out ? `<pre class="wk-pre">${out}</pre>` : ctx.empty(ctx.t("none"))}`;
    },
  });
})();
