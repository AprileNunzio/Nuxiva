(() => {
  const OPEN = /^(open|aperta|aperto|abierto|abierta|ouvert|ouverte)$/i;
  const FILTERED = /filtered|filtrat|filtrad|filtré|filtre/i;
  const LINE = /^(\d{1,5})\/(tcp|udp|sctp)\s+(\S+)\s*(\S*)\s*(.*)$/i;
  const HOST = /Nmap scan report for\s+(.+)$/i;
  const SERVICE = { 21: "ftp", 22: "ssh", 23: "telnet", 25: "smtp", 53: "dns", 80: "http", 110: "pop3", 111: "rpcbind", 135: "msrpc", 139: "netbios", 143: "imap", 161: "snmp", 389: "ldap", 443: "https", 445: "smb", 502: "modbus", 554: "rtsp", 631: "ipp", 993: "imaps", 1433: "mssql", 1883: "mqtt", 2375: "docker", 3306: "mysql", 3389: "rdp", 5432: "postgres", 5900: "vnc", 6379: "redis", 8080: "http-alt", 8443: "https-alt", 9200: "elasticsearch", 11211: "memcached", 11434: "ollama", 27017: "mongodb" };
  const RISK = { 23: "bad", 21: "bad", 445: "bad", 139: "bad", 3389: "bad", 5900: "bad", 2375: "bad", 6379: "bad", 27017: "bad", 11211: "bad", 9200: "bad", 1433: "warn", 3306: "warn", 5432: "warn", 161: "warn", 135: "warn", 111: "warn", 1883: "warn", 502: "bad", 554: "warn", 11434: "warn" };

  function parse(d, ctx) {
    const out = [];
    let host = ctx.str(d.host ?? d.target, 80);
    if (Array.isArray(d.ports)) {
      for (const p of ctx.arr(d.ports, 200)) {
        if (!p || typeof p !== "object") continue;
        const port = Math.floor(ctx.num(p.port) || 0);
        if (port < 1 || port > 65535) continue;
        out.push({ port, proto: ctx.str(p.proto ?? p.protocol, 5).toLowerCase() || "tcp", state: ctx.str(p.state, 20).toLowerCase() || "open", service: ctx.str(p.service, 30), version: ctx.str(p.version ?? p.product, 80) });
      }
      return { host, rows: out, extra: [] };
    }
    const extra = [];
    for (const l of ctx.lines(d.content, 200, 20000)) {
      const h = l.match(HOST);
      if (h) { host = host || h[1].slice(0, 80); continue; }
      const m = l.match(LINE);
      if (m && +m[1] >= 1 && +m[1] <= 65535) out.push({ port: +m[1], proto: m[2].toLowerCase(), state: m[3].toLowerCase(), service: m[4], version: m[5].slice(0, 80) });
      else if (!/^(PORT\s|Starting Nmap|Nmap done|Host is up|Not shown|Read data files)/i.test(l)) extra.push(l.slice(0, 160));
    }
    return { host, rows: out, extra: extra.slice(0, 4) };
  }

  NuxivaDesk.register("port_scanner", {
    render(el, d, ctx) {
      const { host, rows, extra } = parse(d && typeof d === "object" ? d : {}, ctx);
      const open = rows.filter((r) => OPEN.test(r.state));
      const filtered = rows.filter((r) => FILTERED.test(r.state));
      const closed = rows.length - open.length - filtered.length;
      const risky = open.filter((r) => RISK[r.port] === "bad").length;
      const head = ctx.head({ icon: "port", label: ctx.t("label"), title: host, chip: rows.length ? ctx.count("open", open.length) : "", state: risky ? "bad" : open.length ? "warn" : rows.length ? "ok" : "" });
      if (!rows.length && !extra.length) { el.innerHTML = `${head}${ctx.empty(ctx.tc("waiting"))}`; return; }
      const shown = [...open.sort((a, b) => ((RISK[b.port] === "bad") - (RISK[a.port] === "bad")) || a.port - b.port), ...filtered].slice(0, 14);
      el.innerHTML = `${head}
        ${rows.length ? `<div class="pz-sum"><span class="pz-n open"><b>${open.length}</b>${ctx.esc(ctx.t("s_open"))}</span><span class="pz-n filt"><b>${filtered.length}</b>${ctx.esc(ctx.t("s_filtered"))}</span><span class="pz-n shut"><b>${closed}</b>${ctx.esc(ctx.t("s_closed"))}</span></div>` : ""}
        ${risky ? `<div class="wk-alert-hint pz-alert">${ctx.icon("alert")}<span>${ctx.esc(ctx.count("risky", risky))}</span></div>` : ""}
        ${shown.length ? `<ul class="pz-list">${shown.map((r) => {
          const on = OPEN.test(r.state);
          const risk = on ? RISK[r.port] || "" : "";
          const svc = r.service && r.service !== "unknown" ? r.service : SERVICE[r.port] || "";
          return `<li class="pz-row${on ? " on" : " filt"}${risk ? ` ${risk}` : ""}"><span class="pz-port mono">${r.port}<small>/${ctx.esc(r.proto)}</small></span>
            <span class="pz-txt"><b>${ctx.esc(svc || "—")}</b>${r.version ? `<small>${ctx.esc(r.version)}</small>` : risk ? `<small>${ctx.esc(ctx.t(`r_${risk}`))}</small>` : ""}</span>
            <span class="wk-chip${risk === "bad" ? " bad" : on ? " warn" : ""}">${ctx.esc(ctx.t(on ? "s_open_one" : "s_filtered_one"))}</span></li>`;
        }).join("")}</ul>` : rows.length ? `<div class="pz-clean">${ctx.icon("shield")}<span>${ctx.esc(ctx.t("all_closed"))}</span></div>` : ""}
        ${extra.length && !rows.length ? `<pre class="wk-pre pz-raw">${ctx.esc(extra.join("\n"))}</pre>` : ""}`;
    },
  });
})();
