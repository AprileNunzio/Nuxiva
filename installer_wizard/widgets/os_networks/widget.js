(() => {
  function signal(v, ctx) {
    const n = ctx.num(v);
    if (n === null) return null;
    if (n < 0) return Math.max(0, Math.min(100, 2 * (n + 100)));
    return Math.max(0, Math.min(100, n <= 1 && !Number.isInteger(n) ? n * 100 : n));
  }

  function band(o, ctx) {
    const f = ctx.num(o.frequency ?? o.freq), ch = ctx.num(o.channel);
    const mhz = f === null ? null : f < 100 ? f * 1000 : f;
    if (mhz !== null) return mhz >= 5925 ? "6" : mhz >= 4900 ? "5" : "2.4";
    if (ch !== null) return ch > 14 ? "5" : "2.4";
    const b = ctx.str(o.band, 8).replace(/\s*ghz/i, "");
    return ["2.4", "5", "6"].includes(b) ? b : "";
  }

  const bars = (p) => `<span class="on-sig" aria-hidden="true">${[25, 50, 75, 100].map((t, i) => `<i class="${p >= t - 12 ? "on" : ""}" style="height:${4 + i * 3}px"></i>`).join("")}</span>`;

  function rows(d, ctx) {
    return ctx.arr(d.devices ?? d.networks, 40).filter((n) => n && typeof n === "object").map((n) => {
      const name = ctx.pick(n, ["name", "ssid", "alias"], 64);
      const bt = n.type === "bluetooth" || /bluetooth/i.test(ctx.str(n.kind, 20));
      const sec = ctx.str(n.security, 24);
      const secure = typeof n.secure === "boolean" ? n.secure : sec ? !/^(open|none|aperta|--)$/i.test(sec) : null;
      const battery = ctx.num(n.battery);
      return { name, bt, sig: signal(n.signal ?? n.rssi ?? n.strength, ctx), secure, sec, connected: n.connected === true, paired: n.paired === true, band: bt ? "" : band(n, ctx), battery: battery === null ? null : Math.max(0, Math.min(100, battery)), hidden: !name };
    }).filter((n) => n.name || n.connected);
  }

  NuxivaDesk.register("os_networks", {
    render(el, d, ctx) {
      const list = rows(d && typeof d === "object" ? d : {}, ctx);
      const wifi = list.filter((n) => !n.bt).sort((a, b) => (b.connected - a.connected) || ((b.sig ?? -1) - (a.sig ?? -1)));
      const bt = list.filter((n) => n.bt).sort((a, b) => (b.connected - a.connected) || (b.paired - a.paired) || ((b.sig ?? -1) - (a.sig ?? -1)));
      const current = wifi.find((n) => n.connected);
      const head = ctx.head({ icon: "wifi", label: ctx.t("label"), title: current ? current.name : list.length ? ctx.count("nearby", list.length) : "", chip: current ? ctx.t("connected") : "", live: Boolean(current) });
      if (!list.length) { el.innerHTML = `${head}${ctx.empty(ctx.t("none"))}`; return; }
      const row = (n) => `<li class="on-row${n.connected ? " cur" : ""}">
          <span class="on-ic">${ctx.icon(n.bt ? "bt" : "wifi")}</span>
          <span class="on-txt"><b>${ctx.esc(n.name || ctx.t("hidden"))}</b><small>${ctx.esc([n.bt ? ctx.t(n.connected ? "connected" : n.paired ? "paired" : "available") : n.connected ? ctx.t("connected") : "", n.band ? `${n.band} GHz` : "", n.sec && n.secure !== false ? n.sec : n.secure === false ? ctx.t("open") : "", n.battery !== null ? `${ctx.t("battery")} ${Math.round(n.battery)}%` : ""].filter(Boolean).join(" · "))}</small></span>
          <span class="on-end">${n.secure === false && !n.bt ? `<span class="on-open" title="${ctx.esc(ctx.t("open_hint"))}">${ctx.icon("unlock")}</span>` : n.secure && !n.bt ? `<span class="on-lock">${ctx.icon("lock")}</span>` : ""}${n.sig !== null ? bars(n.sig) : ""}</span></li>`;
      el.innerHTML = `${head}
        ${wifi.length ? `<h5 class="on-h">${ctx.icon("wifi")}${ctx.esc(ctx.t("wifi"))}<b>${wifi.length}</b></h5><ul class="on-list">${wifi.slice(0, 10).map(row).join("")}</ul>` : ""}
        ${bt.length ? `<h5 class="on-h">${ctx.icon("bt")}${ctx.esc(ctx.t("bluetooth"))}<b>${bt.length}</b></h5><ul class="on-list">${bt.slice(0, 8).map(row).join("")}</ul>` : ""}`;
    },
  });
})();
