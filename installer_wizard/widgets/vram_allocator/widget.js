(() => {
  const UNIT = { b: 1 / 1048576, kb: 1 / 1024, kib: 1 / 1024, mb: 1, mib: 1, gb: 1024, gib: 1024, tb: 1048576, tib: 1048576 };
  const SIZE = /(\d+(?:[.,]\d+)?)\s*(t|g|m|k)?i?b\b/i;
  const PS = /^(\S+)\s+([0-9a-f]{6,})\s+(\d+(?:[.,]\d+)?\s*[KMGT]i?B)\s+(.+?)\s{2,}(.*)$/i;
  const SMI = /(\d+)\s*MiB\s*\/\s*(\d+)\s*MiB/i;
  const COLORS = ["rgb(var(--tone))", "#38bdf8", "#f472b6", "#facc15", "#34d399", "#fb923c", "#a3e635", "#e879f9"];

  const mb = (v, ctx) => {
    if (typeof v === "number") return Number.isFinite(v) && v >= 0 ? v : null;
    const s = ctx.str(v, 30);
    const m = s.match(SIZE);
    if (m) return Number(m[1].replace(",", ".")) * UNIT[`${(m[2] || "").toLowerCase()}b`];
    const n = ctx.num(s);
    return n === null || n < 0 ? null : n;
  };

  const parse = (d, ctx) => {
    let total = mb(d.total ?? d.total_mb ?? d.vram_total, ctx), used = mb(d.used ?? d.used_mb ?? d.vram_used, ctx);
    const models = [];
    for (const m of ctx.arr(d.models, 16)) {
      if (!m || typeof m !== "object") continue;
      const size = mb(m.size_vram ?? m.vram ?? m.size ?? m.size_mb, ctx);
      const name = ctx.pick(m, ["name", "model"], 60);
      if (name && size !== null) models.push({ name, size, proc: ctx.pick(m, ["processor", "device"], 30), until: ctx.pick(m, ["until", "expires"], 40) });
    }
    if (!models.length) {
      for (const l of ctx.lines(d.content, 40, 8000)) {
        const smi = l.match(SMI);
        if (smi) { used = used ?? Number(smi[1]); total = total ?? Number(smi[2]); continue; }
        const ps = l.match(PS);
        if (ps) { models.push({ name: ps[1].slice(0, 60), size: mb(ps[3], ctx), proc: ps[4].trim().slice(0, 30), until: ps[5].trim().slice(0, 40) }); continue; }
        const p = ctx.pair(l, 60);
        if (!p) continue;
        const key = p[1].toLowerCase();
        const val = mb(p[2], ctx);
        if (val === null) continue;
        if (/^(total|totale|vram|capacit)/.test(key)) total = total ?? val;
        else if (/^(used|usata|occupat|in uso)/.test(key)) used = used ?? val;
        else if (!/^(free|libera)/.test(key)) models.push({ name: p[1].slice(0, 60), size: val, proc: "", until: "" });
      }
    }
    const sum = models.reduce((a, m) => a + m.size, 0);
    used = used ?? (models.length ? sum : null);
    return { total, used, models: models.sort((a, b) => b.size - a.size) };
  };

  const gb = (v, ctx) => v >= 1024 ? `${ctx.fmt(v / 1024, { maximumFractionDigits: 1 })} GB` : `${ctx.fmt(v, { maximumFractionDigits: 0 })} MB`;

  NuxivaDesk.register("vram_allocator", {
    render(el, raw, ctx) {
      const d = raw && typeof raw === "object" ? raw : {};
      const { total, used, models } = parse(d, ctx);
      if (used === null && !models.length) { el.innerHTML = `${ctx.head({ icon: "memory", label: ctx.t("label") })}${ctx.metrics(d.content)}`; return; }
      const cap = Math.max(total || 0, used || 0, models.reduce((a, m) => a + m.size, 0), 1);
      const pct = total ? ctx.pct(((used || 0) / total) * 100) : null;
      const state = pct === null ? "" : pct >= 95 ? "bad" : pct >= 80 ? "warn" : "ok";
      const split = models.filter((m) => /cpu/i.test(m.proc) && /gpu/i.test(m.proc)).length;
      const onCpu = models.filter((m) => /cpu/i.test(m.proc) && !/gpu/i.test(m.proc)).length;
      el.innerHTML = `${ctx.head({ icon: "memory", label: ctx.t("label"), chip: pct !== null ? `${Math.round(pct)}%` : ctx.count("models", models.length), state })}
        <div class="va-hero"><span class="wk-num sm">${ctx.esc(gb(used || 0, ctx))}</span>${total ? `<span class="wk-sub">${ctx.esc(ctx.t("of", { total: gb(total, ctx) }))}</span>` : ""}
          ${total ? `<span class="va-free">${ctx.esc(ctx.t("free", { v: gb(Math.max(0, total - (used || 0)), ctx) }))}</span>` : ""}</div>
        <div class="va-stack" role="img" aria-label="${ctx.esc(ctx.t("label"))}">${models.map((m, i) => `<i style="width:${Math.max(0.6, (m.size / cap) * 100).toFixed(2)}%;background:${COLORS[i % COLORS.length]}" title="${ctx.esc(m.name)}"></i>`).join("")}${!models.length && used ? `<i style="width:${((used / cap) * 100).toFixed(2)}%;background:${COLORS[0]}"></i>` : ""}</div>
        ${split || onCpu ? `<div class="wk-alert-hint va-alert">${ctx.icon("alert")}<span>${ctx.esc(ctx.t(split ? "split" : "cpu_only"))}</span></div>` : ""}
        ${models.length ? `<ul class="va-list">${models.slice(0, 8).map((m, i) => `<li><i style="background:${COLORS[i % COLORS.length]}"></i><span class="va-name">${ctx.esc(m.name)}${m.until ? `<small>${ctx.esc(m.until)}</small>` : ""}</span>
          ${m.proc ? `<em class="${/cpu/i.test(m.proc) ? "cpu" : ""}">${ctx.esc(m.proc)}</em>` : "<em></em>"}<b class="mono">${ctx.esc(gb(m.size, ctx))}</b></li>`).join("")}</ul>` : ""}`;
    },
  });
})();
