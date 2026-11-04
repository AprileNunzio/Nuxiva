(() => {
  const IPV4 = /\b((?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3})\b/;
  const IPV6 = /\b([0-9a-f]{0,4}(?::[0-9a-f]{0,4}){2,7})\b/i;
  const LOCAL = (a) => /^(10\.|127\.|192\.168\.|169\.254\.|172\.(1[6-9]|2\d|3[01])\.|100\.(6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.)/.test(a) || /^(fe80:|fc|fd|::1$)/i.test(a);
  const WHO = /^(\S+)\s+((?:pts|tty)\/?\S*)\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}|\w{3}\s+\d{1,2}\s+\d{2}:\d{2})\s*(?:\(([^)]+)\))?/;
  const W = /^(\S+)\s+((?:pts|tty)\/?\S*)\s+(\S+)\s+(\S+)\s+(\S+)\s+\S+\s+\S+\s+(.*)$/;
  const SS = /(\S+):22\s+(\S+):(\d+)/;

  const isIp = (s) => IPV4.test(s) && /^[\d.]+$/.test(s) || /^[0-9a-f:]+$/i.test(s) && (s.includes("::") || s.split(":").length > 3);
  const ipOf = (s) => { const m = String(s || "").match(IPV4) || String(s || "").match(IPV6); return m ? m[1] : ""; };

  const parse = (d, ctx) => {
    const out = [];
    if (Array.isArray(d.sessions)) {
      for (const s of ctx.arr(d.sessions, 40)) {
        if (!s || typeof s !== "object") continue;
        const from = ctx.pick(s, ["from", "ip", "host", "source", "remote"], 80);
        out.push({ user: ctx.pick(s, ["user", "name", "login"], 32), from, ip: ipOf(from) || from, tty: ctx.pick(s, ["tty", "pts", "terminal"], 16),
          since: ctx.stamp(s.since ?? s.login ?? s.started ?? s.at), idle: ctx.pick(s, ["idle"], 12), what: ctx.pick(s, ["what", "cmd", "command"], 80) });
      }
      return out;
    }
    for (const l of ctx.lines(d.content, 40, 8000)) {
      if (/^\s*(USER\s+TTY|\d{1,2}:\d{2}:\d{2}\s+up\b|Recv-Q|State\s)/i.test(l)) continue;
      let m = l.match(WHO);
      if (m) { out.push({ user: m[1].slice(0, 32), tty: m[2].slice(0, 16), since: ctx.stamp(m[3].replace(" ", "T")), from: (m[4] || "").slice(0, 80), ip: ipOf(m[4]) || (m[4] || "").slice(0, 80), idle: "", what: "" }); continue; }
      m = l.match(W);
      if (m) { out.push({ user: m[1].slice(0, 32), tty: m[2].slice(0, 16), from: m[3] === "-" ? "" : m[3].slice(0, 80), ip: ipOf(m[3]) || (m[3] === "-" ? "" : m[3]), since: null, idle: m[5].slice(0, 12), what: m[6].slice(0, 80) }); continue; }
      m = l.match(SS);
      if (m) { const proc = l.match(/pid=(\d+)/); out.push({ user: "", tty: proc ? `pid ${proc[1]}` : "", from: `${m[2]}:${m[3]}`, ip: ipOf(m[2]), since: null, idle: "", what: "" }); continue; }
      const p = ctx.pair(l, 64);
      const who = p ? p[1] : l;
      const at = who.match(/^([^@\s]+)@(\S+)/);
      out.push({ user: (at ? at[1] : who).slice(0, 32), from: at ? at[2].slice(0, 80) : ipOf(l), ip: ipOf(at ? at[2] : l) || (at ? at[2].slice(0, 80) : ""), tty: "", since: null, idle: "", what: p ? p[2].slice(0, 80) : "" });
    }
    return out;
  };

  NuxivaDesk.register("ssh_sessions", {
    render(el, raw, ctx) {
      const d = raw && typeof raw === "object" ? raw : {};
      const rows = parse(d, ctx).filter((r) => r.user || r.from);
      const root = rows.filter((r) => /^root$/i.test(r.user)).length;
      const wan = rows.filter((r) => isIp(r.ip) && !LOCAL(r.ip)).length;
      const state = root || wan ? "bad" : rows.length ? "warn" : "ok";
      const head = ctx.head({ icon: "terminal", label: ctx.t("label"), chip: rows.length ? ctx.count("active", rows.length) : ctx.t("none_chip"), live: rows.length > 0, state });
      if (!rows.length) { el.innerHTML = `${head}<div class="sh-clean">${ctx.icon("shield")}<span>${ctx.esc(ctx.t("none"))}</span></div>`; return; }
      const users = new Set(rows.map((r) => r.user).filter(Boolean)).size;
      el.innerHTML = `${head}
        ${wan ? `<div class="wk-alert-hint sh-alert">${ctx.icon("alert")}<span>${ctx.esc(ctx.count("wan", wan))}</span></div>` : root ? `<div class="wk-alert-hint sh-alert warn">${ctx.icon("key")}<span>${ctx.esc(ctx.t("root_on"))}</span></div>` : ""}
        <ul class="sh-list">${rows.slice(0, 10).map((r) => {
          const isRoot = /^root$/i.test(r.user);
          const ext = isIp(r.ip) && !LOCAL(r.ip);
          const meta = [r.tty, r.since !== null ? ctx.ago(r.since) : "", r.idle && r.idle !== "0.00s" ? ctx.t("idle", { t: r.idle }) : ""].filter(Boolean);
          return `<li class="sh-row${isRoot ? " root" : ""}${ext ? " ext" : ""}"><span class="sh-av">${isRoot ? ctx.icon("key") : ctx.esc((r.user || "?").slice(0, 1).toUpperCase())}</span>
            <span class="sh-txt"><b>${ctx.esc(r.user || ctx.t("unknown"))}</b><small>${ctx.esc(meta.join(" · "))}</small>${r.what ? `<code>${ctx.esc(r.what)}</code>` : ""}</span>
            <span class="sh-from"><span class="mono">${ctx.esc(r.from || "—")}</span>${isIp(r.ip) ? `<em class="${ext ? "bad" : ""}">${ctx.esc(ctx.t(ext ? "wan_tag" : "lan_tag"))}</em>` : ""}</span></li>`;
        }).join("")}</ul>
        ${rows.length > 10 ? `<div class="wk-faint sh-more">${ctx.esc(ctx.t("more", { n: rows.length - 10 }))}</div>` : ""}
        ${users > 1 ? `<div class="wk-faint sh-more">${ctx.esc(ctx.t("users", { n: users }))}</div>` : ""}`;
    },
  });
})();
