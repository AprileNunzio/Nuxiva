(() => {
  NuxivaDesk.register("ssh_sessions", {
    render(el, d, ctx) {
      const lines = ctx.lines(d.content, 10);
      const rows = lines.map((l) => {
        const p = ctx.pair(l, 64);
        const root = /^root@/i.test(p ? p[1] : l);
        return p
          ? `<li class="wk-row ic${root ? " warn" : ""}">${ctx.icon("terminal")}<span><b>${ctx.esc(p[1])}</b></span><span class="wk-val">${ctx.esc(p[2])}</span></li>`
          : `<li class="wk-row ic${root ? " warn" : ""}">${ctx.icon("terminal")}<span><b>${ctx.esc(l)}</b></span></li>`;
      }).join("");
      el.innerHTML = `${ctx.head({ icon: "terminal", label: ctx.t("label"), chip: lines.length ? ctx.count("active", lines.length) : "", live: lines.length > 0 })}
        ${rows ? `<ul class="wk-list">${rows}</ul>` : ctx.empty(ctx.t("none"))}`;
    },
  });
})();
