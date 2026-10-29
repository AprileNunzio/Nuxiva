(() => {
  const ICON = { router: "network", ap: "wifi", phone: "phone", computer: "cpu", server: "server", printer: "printer", tv: "video", camera: "camera", nas: "memory", iot: "bolt", esp: "chip", raspberry: "chip", speaker: "music", homeassistant: "home", console: "play", nuxiva: "brain", unknown: "lan" };
  const IPV4 = /\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b/;
  const W = 420, H = 270, CX = W / 2, CY = H / 2, MAX = 24;

  function nodes(d, ctx) {
    const src = d.devices ?? d.nodes ?? d.items;
    if (Array.isArray(src)) {
      return ctx.arr(src, 80).filter((x) => x && typeof x === "object").map((x) => ({
        label: ctx.pick(x, ["label", "name", "hostname"], 40).replace(/^[^\p{L}\p{N}]+/u, ""), ip: ctx.pick(x, ["ip", "value"], 45),
        type: Object.hasOwn(ICON, x.type) ? x.type : "unknown", online: x.online !== false, trusted: x.trusted === true,
      })).filter((x) => x.label || x.ip);
    }
    return ctx.lines(d.content, 40, 6000).map((line) => {
      const ip = (line.match(IPV4) || [""])[0];
      const label = line.replace(IPV4, "").replace(/[()[\]\-–—:|,]+/g, " ").replace(/\s+/g, " ").trim().slice(0, 40);
      const low = line.toLowerCase();
      const type = /router|gateway|fritz/.test(low) ? "router" : /nuxiva/.test(low) ? "nuxiva" : /phone|iphone|android|telefono/.test(low) ? "phone" : /printer|stampante/.test(low) ? "printer" : /tv|chromecast/.test(low) ? "tv" : /cam/.test(low) ? "camera" : /nas/.test(low) ? "nas" : /server|raspberry/.test(low) ? "server" : /pc|laptop|computer|macbook/.test(low) ? "computer" : "unknown";
      return { label, ip, type, online: !/offline|spento|down/.test(low), trusted: false };
    }).filter((x) => x.ip);
  }

  const short = (s, n = 12) => (Array.from(s).length > n ? `${Array.from(s).slice(0, n - 1).join("")}…` : s);
  const glyph = (ctx, name, x, y, size) => ctx.icon(name).replace("<svg ", `<svg x="${(x - size / 2).toFixed(1)}" y="${(y - size / 2).toFixed(1)}" width="${size}" height="${size}" `);

  NuxivaDesk.register("net_topology", {
    render(el, d, ctx) {
      const data = d && typeof d === "object" ? d : {};
      const all = nodes(data, ctx);
      const gwIp = ctx.str(data.gateway, 45);
      let hub = all.find((x) => x.type === "router") || all.find((x) => gwIp && x.ip === gwIp);
      const subnet = ctx.str(data.subnet, 45);
      const head = ctx.head({ icon: "network", label: ctx.t("label"), title: subnet || ctx.t("title"), chip: all.length ? ctx.count("online", all.filter((x) => x.online).length) : "", live: all.length > 0 });
      if (!all.length) { el.innerHTML = `${head}${ctx.empty(ctx.t(data.scanning ? "loading" : "none"))}`; return; }
      if (!hub) hub = { label: ctx.t("gateway"), ip: gwIp, type: "router", online: true, virtual: true };
      const ring = all.filter((x) => x !== hub).sort((a, b) => (b.online - a.online) || a.type.localeCompare(b.type)).slice(0, MAX);
      const outer = ring.length > 12;
      const pos = ring.map((x, i) => {
        const inner = !outer || i % 2 === 0;
        const n = outer ? Math.ceil(ring.length / 2) : ring.length;
        const k = outer ? Math.floor(i / 2) : i;
        const a = -Math.PI / 2 + (k / n) * Math.PI * 2 + (outer && !inner ? Math.PI / n : 0);
        const rx = inner ? (outer ? 120 : 160) : 180, ry = inner ? (outer ? 70 : 96) : 112;
        return { x: CX + Math.cos(a) * rx, y: CY + Math.sin(a) * ry };
      });
      const links = ring.map((x, i) => `<line class="nt-link${x.online ? "" : " off"}" x1="${CX}" y1="${CY}" x2="${pos[i].x.toFixed(1)}" y2="${pos[i].y.toFixed(1)}" style="--d:${(1.4 + (i % 5) * 0.25).toFixed(2)}s"/>`).join("");
      const dots = ring.map((x, i) => `<g class="nt-node${x.online ? "" : " off"}${x.type === "nuxiva" ? " me" : ""}${!x.trusted && data.trusted_known ? " warn" : ""}" data-i="${i}" tabindex="0" role="button" aria-label="${ctx.esc(`${x.label || x.ip} ${x.ip}`)}">
          <circle cx="${pos[i].x.toFixed(1)}" cy="${pos[i].y.toFixed(1)}" r="13"/>${glyph(ctx, ICON[x.type], pos[i].x, pos[i].y, 13)}
          <text x="${pos[i].x.toFixed(1)}" y="${(pos[i].y + 25).toFixed(1)}">${ctx.esc(short(x.label || x.ip))}</text><title>${ctx.esc(`${x.label}\n${x.ip}\n${ctx.t(`t_${x.type}`)}`)}</title></g>`).join("");
      el.innerHTML = `${head}
        <div class="nt-wrap"><svg class="nt-map" viewBox="0 0 ${W} ${H}" role="img" aria-label="${ctx.esc(ctx.t("title"))}">
          <defs><radialGradient id="nt-glow-${el.dataset.ntId || (el.dataset.ntId = Math.random().toString(36).slice(2, 8))}"><stop offset="0" stop-color="currentColor" stop-opacity=".35"/><stop offset="1" stop-color="currentColor" stop-opacity="0"/></radialGradient></defs>
          <circle class="nt-halo" cx="${CX}" cy="${CY}" r="46" fill="url(#nt-glow-${el.dataset.ntId})"/>
          ${links}${dots}
          <g class="nt-hub"><circle cx="${CX}" cy="${CY}" r="20"/>${glyph(ctx, "network", CX, CY, 18)}<text x="${CX}" y="${CY + 34}">${ctx.esc(short(hub.label || ctx.t("gateway"), 16))}</text></g>
        </svg></div>
        <div class="nt-info" aria-live="polite">${ctx.esc(hub.ip ? `${ctx.t("gateway")} · ${hub.ip}` : "")}${all.length - 1 > MAX ? ` · ${ctx.esc(ctx.t("more", { n: all.length - 1 - MAX }))}` : ""}</div>`;
      const info = el.querySelector(".nt-info");
      const show = (g) => {
        el.querySelectorAll(".nt-node.sel").forEach((n) => n.classList.remove("sel"));
        const x = ring[Number(g.dataset.i)];
        if (!x) return;
        g.classList.add("sel");
        info.textContent = [x.label, x.ip, ctx.t(`t_${x.type}`), ctx.t(x.online ? "online_word" : "offline_word")].filter(Boolean).join(" · ");
      };
      el.querySelectorAll(".nt-node").forEach((g) => {
        g.addEventListener("click", (e) => { e.stopPropagation(); show(g); });
        g.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); show(g); } });
      });
    },
  });
})();
