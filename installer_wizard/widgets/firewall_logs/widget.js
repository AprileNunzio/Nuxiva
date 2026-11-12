(() => {
  const IPV4 = /^(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)$/;
  const IPV6 = /^[0-9a-f:]{2,39}$/i;
  const IP_IN = /\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b/g;
  const FIELD = /\b(SRC|DST|PROTO|SPT|DPT|IN)=([^\s]+)/g;
  const SEV = { low: 0, medium: 1, high: 2, critical: 3 };
  const KINDS = new Set(["port_scan", "host_sweep", "syn_flood", "brute_force", "arp_spoof", "dns_tunnel", "icmp_flood", "exfiltration"]);
  const PORTS = { 21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS", 80: "HTTP", 110: "POP3", 123: "NTP", 137: "NetBIOS", 139: "SMB", 143: "IMAP", 161: "SNMP", 443: "HTTPS", 445: "SMB", 993: "IMAPS", 1433: "MSSQL", 1883: "MQTT", 3306: "MySQL", 3389: "RDP", 5060: "SIP", 5432: "Postgres", 5900: "VNC", 6379: "Redis", 8080: "HTTP-alt", 8443: "HTTPS-alt", 11434: "Ollama", 27017: "MongoDB" };

  const ip = (v) => { const s = typeof v === "string" ? v.trim() : ""; return IPV4.test(s) || (s.includes(":") && IPV6.test(s)) ? s : ""; };
  const isLocal = (a) => /^(10\.|127\.|192\.168\.|169\.254\.|172\.(1[6-9]|2\d|3[01])\.)/.test(a) || /^(fe80:|fc|fd|::1$)/i.test(a);
  const port = (v) => { const n = Number(v); return Number.isInteger(n) && n > 0 && n < 65536 ? n : 0; };

  function fromText(line) {
    const f = {};
    for (const [, k, v] of line.matchAll(FIELD)) f[k] = v;
    const src = ip(f.SRC || "") || (line.match(IP_IN) || [])[0] || "";
    return { src, dst: ip(f.DST || ""), proto: (f.PROTO || "").slice(0, 6).toUpperCase(), dport: port(f.DPT), iface: (f.IN || "").slice(0, 12), raw: line, kind: "", sev: -1, count: 1, at: null };
  }

  function fromObj(o, ctx) {
    const kind = ctx.str(o.kind, 24);
    const sev = SEV[ctx.str(o.severity, 10).toLowerCase()];
    const count = Math.max(1, Math.floor(ctx.num(o.count) || 1));
    return { src: ip(o.src) || ip(o.source), dst: ip(o.dst), proto: ctx.str(o.proto, 6).toUpperCase(), dport: port(o.port ?? o.dport ?? o.dpt),
      iface: ctx.str(o.iface, 12), raw: ctx.pick(o, ["detail", "text", "line"], 200), kind: KINDS.has(kind) ? kind : "", sev: sev ?? -1, count, at: ctx.stamp(o.at ?? o.time) };
  }

  const svc = (p) => (p ? `${p}${PORTS[p] ? ` ${PORTS[p]}` : ""}` : "");
  const level = (s) => (s >= 3 ? "bad" : s >= 2 ? "bad" : s >= 1 ? "warn" : "");

  function top(list, key, n) {
    const m = new Map();
    for (const e of list) if (e[key]) m.set(e[key], (m.get(e[key]) || 0) + e.count);
    return [...m.entries()].sort((a, b) => b[1] - a[1]).slice(0, n);
  }

  NuxivaDesk.register("firewall_logs", {
    render(el, d, ctx) {
      const data = d && typeof d === "object" ? d : {};
      const objs = ctx.arr(data.entries ?? data.alerts ?? data.blocks, 60).filter((o) => o && typeof o === "object").map((o) => fromObj(o, ctx)).filter((e) => e.src || e.raw || e.kind);
      const text = objs.length ? [] : ctx.lines(data.content ?? (typeof d === "string" ? d : ""), 40, 12000).map(fromText);
      const rows = objs.length ? objs : text;
      const total = rows.reduce((s, e) => s + e.count, 0);
      const worst = rows.reduce((m, e) => Math.max(m, e.sev), -1);
      const sources = top(rows, "src", 4);
      const ports = top(rows.map((e) => ({ ...e, p: svc(e.dport) })), "p", 4);
      const peak = Math.max(1, ...sources.map((s) => s[1]));
      const head = ctx.head({ icon: "shield", label: ctx.t("label"), chip: total ? ctx.count("blocked", total) : "", live: total > 0, state: total ? level(worst) || "bad" : "" });
      if (!rows.length) { el.innerHTML = `${head}${ctx.empty(ctx.t("none"))}`; return; }
      const parsed = rows.some((e) => e.src);
      const external = sources.filter(([a]) => !isLocal(a)).length;
      el.innerHTML = `${head}
        ${parsed ? `<div class="fw-grid">
          <div class="fw-box"><h5>${ctx.esc(ctx.t("top_sources"))}</h5><ul class="fw-top">${sources.map(([a, n]) => `<li><span class="fw-ip ${isLocal(a) ? "lan" : "wan"}" title="${ctx.esc(ctx.t(isLocal(a) ? "lan" : "wan"))}">${ctx.esc(a)}</span>${ctx.bar((n / peak) * 100, isLocal(a) ? "warn" : "bad")}<b class="mono">${ctx.esc(ctx.fmt(n))}</b></li>`).join("")}</ul></div>
          ${ports.length ? `<div class="fw-box"><h5>${ctx.esc(ctx.t("top_ports"))}</h5><ul class="fw-ports">${ports.map(([p, n]) => `<li><span class="mono">${ctx.esc(p)}</span><b class="mono">${ctx.esc(ctx.fmt(n))}</b></li>`).join("")}</ul></div>` : ""}
        </div>
        ${external ? `<div class="fw-note">${ctx.icon("alert")}<span>${ctx.esc(ctx.count("external", external))}</span></div>` : ""}` : ""}
        <ol class="fw-log">${rows.slice(0, 14).map((e) => {
          const kind = e.kind ? ctx.t(`k_${e.kind}`) : "";
          const main = e.src
            ? `<span class="fw-ip ${isLocal(e.src) ? "lan" : "wan"}">${ctx.esc(e.src)}</span><i aria-hidden="true">→</i><span class="fw-dst">${ctx.esc(e.dst || "")}${e.dport ? `<b>:${ctx.esc(svc(e.dport))}</b>` : ""}</span>`
            : `<span class="fw-raw">${ctx.esc(e.raw)}</span>`;
          const meta = [kind, e.proto, e.iface, e.count > 1 ? `×${ctx.fmt(e.count)}` : "", e.at ? ctx.when(e.at, { hour: "2-digit", minute: "2-digit", second: "2-digit" }) : ""].filter(Boolean).map(ctx.esc).join(" · ");
          return `<li class="${level(e.sev)}">${main}${meta ? `<small>${meta}</small>` : ""}</li>`;
        }).join("")}</ol>
        ${rows.length > 14 ? `<div class="wk-faint fw-more">${ctx.esc(ctx.t("more", { n: rows.length - 14 }))}</div>` : ""}`;
    },
  });
})();
