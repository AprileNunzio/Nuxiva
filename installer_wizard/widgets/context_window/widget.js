(() => {
  const PARTS = ["system", "history", "tools", "files", "memory"];
  const toNum = (s) => {
    const m = String(s).trim().match(/^(\d+(?:[.,]\d+)*)\s*([kKmM])?$/);
    if (!m) return null;
    let raw = m[1];
    if (m[2]) raw = raw.replace(",", ".");
    else raw = raw.replace(/[.,](?=\d{3}\b)/g, "").replace(",", ".");
    const n = Number(raw);
    if (!Number.isFinite(n)) return null;
    return m[2] ? n * (/[kK]/.test(m[2]) ? 1e3 : 1e6) : n;
  };

  function parse(d, ctx) {
    let used = ctx.num(d.used ?? d.tokens), max = ctx.num(d.max ?? d.limit ?? d.window);
    if ((used === null || max === null) && typeof d.content === "string") {
      const m = d.content.match(/(\d[\d.,]*\s*[kKmM]?)\s*(?:\/|di|of|de|sur)\s*(\d[\d.,]*\s*[kKmM]?)/);
      if (m) { used = used ?? toNum(m[1]); max = max ?? toNum(m[2]); }
    }
    const src = d.parts && typeof d.parts === "object" ? d.parts : {};
    const parts = PARTS.map((k) => ({ k, v: ctx.num(src[k]) })).filter((p) => p.v !== null && p.v > 0);
    return { used, max, parts, model: ctx.str(d.model, 48), messages: ctx.num(d.messages) };
  }

  NuxivaDesk.register("context_window", {
    render(el, d, ctx) {
      const data = d && typeof d === "object" ? d : {};
      const c = parse(data, ctx);
      if (c.used === null || !c.max || c.max <= 0) {
        el.innerHTML = `${ctx.head({ icon: "brain", label: ctx.t("label") })}${ctx.metrics(data.content)}`;
        return;
      }
      const pct = Math.max(0, Math.min(100, (c.used / c.max) * 100));
      const state = pct >= 90 ? "bad" : pct >= 75 ? "warn" : "";
      const compact = (n) => ctx.fmt(n, { notation: "compact", maximumFractionDigits: 1 });
      const sum = c.parts.reduce((a, p) => a + p.v, 0);
      const scale = sum > c.used ? sum : c.used;
      const segs = c.parts.map((p) => `<i class="cw-${p.k}" style="width:${((p.v / c.max) * 100 * (c.used / scale)).toFixed(2)}%" title="${ctx.esc(ctx.t(`part_${p.k}`))}"></i>`).join("");
      el.innerHTML = `${ctx.head({ icon: "brain", label: ctx.t("label"), title: c.model, chip: state ? ctx.t(state === "bad" ? "nearly_full" : "filling") : "", state })}
        <div class="cw-top">
          ${ctx.ring(pct, `${Math.round(pct)}%`, ctx.t("used"))}
          <div class="cw-nums">
            <span class="wk-num sm">${ctx.esc(compact(c.used))}<small> / ${ctx.esc(compact(c.max))}</small></span>
            <span class="wk-sub">${ctx.esc(ctx.t("free", { n: compact(Math.max(0, c.max - c.used)) }))}${c.messages !== null ? ` · ${ctx.esc(ctx.t("messages", { n: ctx.fmt(c.messages) }))}` : ""}</span>
          </div>
        </div>
        ${segs ? `<div class="cw-stack${state ? ` ${state}` : ""}">${segs}</div>
          <ul class="cw-legend">${c.parts.map((p) => `<li><i class="cw-${p.k}"></i>${ctx.esc(ctx.t(`part_${p.k}`))}<b>${ctx.esc(compact(p.v))}</b></li>`).join("")}</ul>` : ctx.bar(pct, state)}`;
    },
  });
})();
