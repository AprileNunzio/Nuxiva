(() => {
  const KINDS = new Set(["port_scan", "host_sweep", "syn_flood", "brute_force", "arp_spoof", "dns_tunnel", "icmp_flood", "exfiltration"]);
  const DEFENSES = new Set(["block", "tarpit", "rate_limit", "honeypot", "quarantine", "sinkhole", "country_block"]);
  const LEVELS = new Set(["low", "medium", "high", "critical"]);
  const CODE = /^[A-Z]{2}$/;

  const flag = (code) => (CODE.test(code) ? String.fromCodePoint(...[...code].map((c) => 0x1f1a5 + c.charCodeAt(0))) : "");

  function country(code) {
    if (!CODE.test(code)) return "";
    try {
      const lang = document.documentElement.lang || "it";
      return new Intl.DisplayNames([lang], { type: "region" }).of(code) || code;
    } catch (e) {
      return code;
    }
  }

  const left = (expires, ctx) => {
    const minutes = Math.max(1, Math.ceil((expires - ctx.now()) / 60));
    return minutes >= 120 ? ctx.t("hours", { n: Math.round(minutes / 60) }) : ctx.t("minutes", { n: minutes });
  };

  NuxivaDesk.register("defense_incidents", {
    headline(d, ctx) {
      const data = d && typeof d === "object" ? d : {};
      const n = ctx.arr(data.incidents, 100).length;
      return n ? { text: ctx.count("say_n", n), tone: "warn" } : { text: ctx.t("say_none"), tone: "ok" };
    },
    render(el, raw, ctx) {
      const d = raw && typeof raw === "object" ? raw : {};
      const incidents = ctx.arr(d.incidents, 5).filter((i) => i && typeof i === "object");
      const defenses = ctx.arr(d.defenses, 6).filter((i) => i && typeof i === "object" && DEFENSES.has(i.kind));
      const head = ctx.head({ icon: "alert", label: ctx.t("label"), chip: incidents.length ? ctx.count("incidents", incidents.length) : "", live: incidents.length > 0, state: incidents.length ? "bad" : "" });
      if (!incidents.length && !defenses.length) { el.innerHTML = `${head}${ctx.empty(ctx.t("none"))}`; return; }
      el.innerHTML = `${head}
        <ul class="di-list">${incidents.map((i) => {
          const kind = KINDS.has(i.kind) ? i.kind : "port_scan";
          const code = ctx.str(i.country, 2);
          const place = i.origin === "lan" ? ctx.t("from_home") : code && CODE.test(code) ? `${flag(code)} ${country(code)}` : ctx.t("from_internet");
          const level = LEVELS.has(i.level) ? i.level : "low";
          return `<li class="${level}"><b>${ctx.esc(ctx.t(`k_${kind}`))}</b><span>${ctx.esc(place)}</span></li>`;
        }).join("")}</ul>
        ${defenses.length ? `<h5 class="di-title">${ctx.esc(ctx.t("done"))}</h5><ul class="di-defs">${defenses.map((x) => `<li><span>${ctx.esc(ctx.t(`d_${x.kind}`))}</span><small>${ctx.esc(ctx.t("for", { t: left(ctx.num(x.expires) || 0, ctx) }))}</small></li>`).join("")}</ul>` : ""}`;
    },
  });
})();
