(() => {
  const KEEP = 72;
  const val = (v, ctx) => { const n = ctx.num(v); return n === null ? null : Math.round(Math.max(0, Math.min(100, n))); };

  const chart = (series, uid) => {
    const path = (h) => h.map((v, i) => `${((i / (KEEP - 1)) * 300).toFixed(1)},${(78 - (v / 100) * 74).toFixed(1)}`);
    const off = (h) => KEEP - h.length;
    return `<svg class="sm-chart" viewBox="0 0 300 80" preserveAspectRatio="none" aria-hidden="true">
      <defs>${series.map(([, , c], k) => `<linearGradient id="${uid}${k}" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="${c}" stop-opacity=".35"/><stop offset="1" stop-color="${c}" stop-opacity="0"/></linearGradient>`).join("")}</defs>
      ${[25, 50, 75].map((g) => `<line x1="0" x2="300" y1="${78 - g * 0.74}" y2="${78 - g * 0.74}" class="grid"/>`).join("")}
      ${series.map(([h, , c], k) => {
        if (h.length < 2) return "";
        const pts = path(h);
        const shift = (off(h) / (KEEP - 1)) * 300;
        return `<g transform="translate(${shift.toFixed(1)} 0)"><polygon points="0,78 ${pts.join(" ")} ${((h.length - 1) / (KEEP - 1) * 300).toFixed(1)},78" fill="url(#${uid}${k})"/><polyline points="${pts.join(" ")}" stroke="${c}"/></g>`;
      }).join("")}</svg>`;
  };

  let seq = 0;

  NuxivaDesk.register("system_monitor", {
    render(el, raw, ctx) {
      const d = raw && typeof raw === "object" ? raw : {};
      const cpu = val(d.cpu, ctx), ram = val(d.ram ?? d.mem, ctx), swap = val(d.swap, ctx), pressure = val(d.pressure, ctx);
      const temp = ctx.num(d.temp), load = ctx.num(d.load), cores = Math.floor(ctx.num(d.cores) || 0);
      const st = el._sm || (el._sm = { uid: `smg${++seq}`, cpu: [], ram: [], at: 0 });
      const now = Date.now();
      if (now - st.at > 900) {
        st.at = now;
        if (cpu !== null) st.cpu.push(cpu);
        if (ram !== null) st.ram.push(ram);
        st.cpu.splice(0, Math.max(0, st.cpu.length - KEEP));
        st.ram.splice(0, Math.max(0, st.ram.length - KEEP));
      }
      if (cpu === null && ram === null) { el.innerHTML = `${ctx.head({ icon: "cpu", label: ctx.t("label") })}${ctx.empty(ctx.tc("waiting"))}`; return; }
      const hot = d.high === true || (cpu ?? 0) > 85 || (ram ?? 0) > 90 || (temp ?? 0) >= 82;
      const warm = !hot && ((cpu ?? 0) > 70 || (ram ?? 0) > 80 || (swap ?? 0) > 40 || (temp ?? 0) >= 72);
      const avg = (h) => h.length ? Math.round(h.reduce((a, b) => a + b, 0) / h.length) : null;
      const peak = (h) => h.length ? Math.max(...h) : null;
      const stat = (icon, label, value, s = "") => `<div class="sm-stat${s ? ` ${s}` : ""}">${ctx.icon(icon)}<span><small>${ctx.esc(label)}</small><b class="mono">${ctx.esc(value)}</b></span></div>`;
      el.innerHTML = `${ctx.head({ icon: "cpu", label: ctx.t("label"), chip: ctx.t(hot ? "critical" : warm ? "loaded" : "nominal"), state: hot ? "bad" : warm ? "warn" : "ok", live: true })}
        <div class="sm-top">
          <div class="sm-rings${hot ? " hot" : ""}">${ctx.ring(cpu ?? 0, cpu === null ? "—" : `${cpu}%`, ctx.t("cpu"))}${ctx.ring(ram ?? 0, ram === null ? "—" : `${ram}%`, ctx.t("ram"))}</div>
          <div class="sm-graph">${chart([[st.cpu, "cpu", "rgb(var(--tone))"], [st.ram, "ram", "#a78bfa"]], st.uid)}
            <div class="sm-legend"><span class="c">${ctx.esc(ctx.t("cpu"))} ${avg(st.cpu) !== null ? `<small>${ctx.esc(ctx.t("avg_peak", { a: avg(st.cpu), p: peak(st.cpu) }))}</small>` : ""}</span><span class="r">${ctx.esc(ctx.t("ram"))} ${avg(st.ram) !== null ? `<small>${ctx.esc(ctx.t("avg_peak", { a: avg(st.ram), p: peak(st.ram) }))}</small>` : ""}</span></div></div>
        </div>
        <div class="sm-stats">
          ${temp !== null ? stat("therm", ctx.t("temp"), `${Math.round(temp)} °C`, temp >= 82 ? "bad" : temp >= 72 ? "warn" : "") : ""}
          ${load !== null ? stat("gauge", ctx.t("load"), `${ctx.fmt(load, { maximumFractionDigits: 2 })}${cores ? ` · ${cores} ${ctx.t("cores")}` : ""}`, load >= 1 ? "warn" : "") : ""}
          ${swap !== null ? stat("memory", ctx.t("swap"), `${swap}%`, swap > 40 ? "warn" : "") : ""}
          ${pressure !== null ? stat("trend", ctx.t("pressure"), `${pressure}%`, d.high === true ? "bad" : pressure >= 70 ? "warn" : "") : ""}
        </div>`;
    },
  });
})();
