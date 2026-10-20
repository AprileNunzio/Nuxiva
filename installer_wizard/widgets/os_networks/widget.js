(() => {
  NuxivaDesk.register("os_networks", {
    render(el, d, ctx) {
      const devs = Array.isArray(d.devices) ? d.devices.slice(0, 12) : [];
      const rows = devs.map((n) => {
        const ic = /bluetooth/i.test(String(n.name || "")) || n.type === "bluetooth" ? "bt" : n.secure ? "lock" : "unlock";
        return `<li class="wk-row ic${n.connected ? " on" : ""}">${ctx.icon(ic)}<span><b>${ctx.esc(n.name)}</b>${ctx.bar(n.signal)}</span>
          ${n.connected ? `<span class="wk-chip live">${ctx.esc(ctx.t("connected"))}</span>` : `<span></span>`}</li>`;
      }).join("");
      el.innerHTML = `${ctx.head({ icon: "wifi", label: ctx.t("label"), title: devs.length ? ctx.count("nearby", devs.length) : "" })}
        ${rows ? `<ul class="wk-list">${rows}</ul>` : ctx.empty(ctx.t("none"))}`;
    },
  });
})();
