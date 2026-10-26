(() => {
  const OPEN = /^(open|aperta|abierto|abierta|ouvert|ouverte)$/i;
  NuxivaDesk.register("port_scanner", {
    render(el, d, ctx) {
      const lines = ctx.lines(d.content, 12, 8000);
      let open = 0;
      const rows = lines.map((l) => {
        const m = l.match(/^(\d{1,5})\/(tcp|udp)\s+(\S+)\s*(.*)$/i);
        if (!m) return `<li class="wk-row"><span><small>${ctx.esc(l)}</small></span></li>`;
        const on = OPEN.test(m[3]);
        if (on) open += 1;
        return `<li class="wk-row ic${on ? " on" : ""}">${ctx.icon("port")}<span><b class="wk-mono">${ctx.esc(m[1])}/${ctx.esc(m[2].toLowerCase())}</b><small>${ctx.esc(m[4] || "—")}</small></span><span class="wk-chip${on ? " warn" : ""}">${ctx.esc(m[3].toLowerCase())}</span></li>`;
      }).join("");
      el.innerHTML = `${ctx.head({ icon: "port", label: ctx.t("label"), chip: open ? ctx.count("open", open) : "", state: open ? "warn" : "" })}
        ${rows ? `<ul class="wk-list">${rows}</ul>` : ctx.empty(ctx.tc("waiting"))}`;
    },
  });
})();
