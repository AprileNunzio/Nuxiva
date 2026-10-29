(() => {
  const ICON = { router: "network", ap: "wifi", phone: "phone", computer: "cpu", server: "server", printer: "printer", tv: "video", camera: "camera", nas: "memory", iot: "bolt", esp: "chip", raspberry: "chip", speaker: "music", homeassistant: "home", console: "play", nuxiva: "brain", unknown: "lan" };
  const ORDER = Object.keys(ICON);
  const MAX = 12;
  const clean = (s) => s.replace(/^[^\p{L}\p{N}]+/u, "").trim();

  function rows(d, ctx) {
    const src = Array.isArray(d.devices) ? d.devices : d.items;
    return ctx.arr(src, 60).filter((x) => x && typeof x === "object").map((x) => {
      const type = Object.hasOwn(ICON, x.type) ? x.type : "unknown";
      return { label: clean(ctx.pick(x, ["label", "name", "hostname"], 60)), ip: ctx.pick(x, ["value", "ip"], 45), type,
        online: x.online !== false, trusted: x.trusted === true, room: ctx.str(x.room, 40), since: ctx.stamp(x.since ?? x.first_seen) };
    }).filter((x) => x.label || x.ip);
  }

  NuxivaDesk.register("network_devices", {
    render(el, d, ctx) {
      const data = d && typeof d === "object" ? d : {};
      const list = rows(data, ctx);
      const online = list.filter((x) => x.online);
      const head = ctx.head({ icon: "network", label: ctx.t("label"), chip: list.length ? ctx.count("connected", online.length) : "", live: online.length > 0 });
      if (!list.length) { el.innerHTML = `${head}${ctx.empty(ctx.t("none"))}`; return; }
      const known = list.some((x) => x.trusted);
      const types = new Map();
      for (const x of online) types.set(x.type, (types.get(x.type) || 0) + 1);
      const sorted = [...list].sort((a, b) => (b.online - a.online) || (known ? a.trusted - b.trusted : 0) || ORDER.indexOf(a.type) - ORDER.indexOf(b.type) || a.label.localeCompare(b.label));
      const shown = sorted.slice(0, MAX);
      const now = ctx.now();
      el.innerHTML = `${head}
        ${types.size > 1 ? `<div class="nd-types">${[...types].sort((a, b) => b[1] - a[1]).slice(0, 6).map(([t, n]) => `<span title="${ctx.esc(ctx.t(`t_${t}`))}">${ctx.icon(ICON[t])}<b class="mono">${n}</b></span>`).join("")}</div>` : ""}
        <ul class="nd-list">${shown.map((x, i) => {
          const fresh = x.since && now - x.since < 86400;
          const flag = known && !x.trusted && x.online;
          return `<li class="nd-row${x.online ? "" : " off"}${flag ? " warn" : ""}" style="--i:${i}"><span class="nd-ic">${ctx.icon(ICON[x.type])}<i class="nd-dot" aria-hidden="true"></i></span>
            <span class="nd-txt"><b title="${ctx.esc(x.label)}">${ctx.esc(x.label || x.ip)}</b><small>${ctx.esc([ctx.t(`t_${x.type}`), x.room].filter(Boolean).join(" · "))}</small></span>
            <span class="nd-end">${fresh ? `<em class="nd-new">${ctx.esc(ctx.t("new"))}</em>` : ""}${flag ? `<em class="nd-unk" title="${ctx.esc(ctx.t("untrusted_hint"))}">${ctx.esc(ctx.t("untrusted"))}</em>` : ""}<span class="mono nd-ip">${ctx.esc(x.ip)}</span></span></li>`;
        }).join("")}</ul>
        ${list.length > MAX ? `<div class="wk-faint nd-more">${ctx.esc(ctx.t("more", { n: list.length - MAX }))}</div>` : ""}`;
    },
  });
})();
