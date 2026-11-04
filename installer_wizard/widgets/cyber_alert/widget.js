(() => {
  const IPV4 = /^(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)$/;
  const IPV6 = /^[0-9a-f:]{2,39}$/i;
  const LEVELS = { critical: 4, critica: 4, critico: 4, high: 3, alta: 3, alto: 3, élevée: 3, medium: 2, media: 2, medio: 2, moyenne: 2, low: 1, bassa: 1, basso: 1, baja: 1, faible: 1 };
  const isPrivate = (ip) => /^(10\.|127\.|192\.168\.|169\.254\.|172\.(1[6-9]|2\d|3[01])\.)/.test(ip) || /^(fc|fd|fe80|::1$)/i.test(ip);

  NuxivaDesk.register("cyber_alert", {
    render(el, d, ctx) {
      const data = d && typeof d === "object" ? d : {};
      const ipRaw = ctx.str(data.source_ip ?? data.ip, 45);
      const ip = IPV4.test(ipRaw) || (IPV6.test(ipRaw) && ipRaw.includes(":")) ? ipRaw : "";
      const levelRaw = ctx.str(data.threat_level ?? data.severity, 20).toLowerCase();
      const level = LEVELS[levelRaw] || 3;
      const attempts = Math.floor(ctx.num(data.attempts ?? data.count) || 0);
      const first = ctx.stamp(data.first_seen), last = ctx.stamp(data.last_seen ?? data.at);
      const blocked = data.blocked === true || /block|bloccat|banned|drop|blocc/i.test(ctx.str(data.action_taken, 120));
      const port = ctx.num(data.port);
      const target = [`${ctx.str(data.service, 30)}${port !== null && port > 0 && port < 65536 ? `:${Math.floor(port)}` : ""}`, ctx.str(data.target ?? data.host, 60)].filter(Boolean).join(" · ");
      const where = [ctx.str(data.country, 40), ctx.str(data.asn ?? data.isp, 60)].filter(Boolean).join(" · ");
      const events = ctx.arr(data.events, 5).map((e) => (e && typeof e === "object" ? { at: ctx.stamp(e.at), text: ctx.pick(e, ["text", "message", "event"], 120) } : { at: null, text: ctx.str(e, 120) })).filter((e) => e.text);
      const kv = (k, v, cls = "") => (v ? `<dt>${ctx.esc(k)}</dt><dd class="${cls}">${ctx.esc(v)}</dd>` : "");
      el.innerHTML = `${ctx.head({ icon: "shield", label: ctx.t("label"), title: ctx.str(data.title, 80) || ctx.t("fallback_title"), chip: levelRaw || ctx.t("threat_default"), live: !blocked, state: level >= 3 ? "bad" : "warn" })}
        <div class="ca-core" role="alert">
          <div class="ca-level" aria-label="${ctx.esc(ctx.t("severity"))}">${[1, 2, 3, 4].map((n) => `<i class="${n <= level ? "on" : ""}"></i>`).join("")}</div>
          <div class="ca-ip"><span class="wk-mono">${ctx.esc(ip || ipRaw || "—")}</span>${ip ? `<small>${ctx.esc(ctx.t(isPrivate(ip) ? "ip_local" : "ip_public"))}${where ? ` · ${ctx.esc(where)}` : ""}</small>` : ""}</div>
          <span class="ca-status ${blocked ? "ok" : "bad"}">${ctx.icon(blocked ? "lock" : "unlock")}${ctx.esc(ctx.t(blocked ? "blocked" : "not_blocked"))}</span>
        </div>
        <dl class="wk-kv ca-kv">
          ${kv(ctx.t("attack"), ctx.str(data.attack_type, 80))}
          ${kv(ctx.t("target"), target, "mono")}
          ${attempts ? kv(ctx.t("attempts"), ctx.fmt(attempts), "mono wk-accent") : ""}
          ${kv(ctx.t("window"), first && last && last > first ? `${ctx.when(first)} → ${ctx.when(last)}` : last ? ctx.ago(last) : "", "mono")}
          ${kv(ctx.t("action"), ctx.str(data.action_taken, 120), "wk-accent")}
        </dl>
        ${events.length ? `<ol class="ca-events">${events.map((e) => `<li>${e.at ? `<time>${ctx.esc(ctx.when(e.at, { hour: "2-digit", minute: "2-digit", second: "2-digit" }))}</time>` : ""}<span>${ctx.esc(e.text)}</span></li>`).join("")}</ol>` : ""}`;
    },
  });
})();
