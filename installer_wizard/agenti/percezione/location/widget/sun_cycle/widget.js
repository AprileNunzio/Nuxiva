(() => {
  const CLOCK = /^([01]?\d|2[0-3])[:.]([0-5]\d)$/;
  const today = (v, ctx) => {
    const m = ctx.str(v, 8).match(CLOCK);
    if (!m) return null;
    const d = new Date();
    d.setHours(+m[1], +m[2], 0, 0);
    return d.getTime() / 1000;
  };
  const dur = (s, ctx) => {
    const m = Math.max(0, Math.round(s / 60));
    return m >= 60 ? ctx.t("hours_minutes", { h: Math.floor(m / 60), m: m % 60 }) : ctx.t("minutes", { m });
  };
  const at = (p) => {
    const q = 1 - p;
    return [q * q * 10 + 2 * q * p * 100 + p * p * 190, q * q * 58 + 2 * q * p * -34 + p * p * 58];
  };

  let seq = 0;

  const impl = {
    render(el, raw, ctx) {
      clearInterval(el._scTick);
      const d = raw && typeof raw === "object" ? raw : {};
      const rise = ctx.stamp(d.rise_ts) ?? today(d.sunrise, ctx);
      const set = ctx.stamp(d.set_ts) ?? today(d.sunset, ctx);
      if (rise === null || set === null || set <= rise) {
        el.innerHTML = `${ctx.head({ icon: "sun", label: ctx.t("label"), title: ctx.str(d.place, 40) })}${ctx.empty(ctx.tc("waiting"))}`;
        return;
      }
      const daylight = set - rise;
      const delta = ctx.num(d.delta_min);
      const uid = el._scId || (el._scId = `sc${++seq}`);
      const paint = () => {
        const now = ctx.now();
        const up = now >= rise && now < set;
        const p = up ? (now - rise) / daylight : now < rise ? 0 : 1;
        const [x, y] = at(p);
        const next = up ? ["sunset", set] : now < rise ? ["sunrise", rise] : ["sunrise", rise + 86400];
        const lit = at(Math.max(0, Math.min(1, p)));
        el.innerHTML = `${ctx.head({ icon: up ? "sun" : "moon", label: ctx.t("label"), title: ctx.str(d.place, 40) })}
          <svg class="sc-arc${up ? " day" : " night"}" viewBox="0 0 200 66" role="img" aria-label="${ctx.esc(ctx.t(up ? "day_pct" : "night", { n: Math.round(p * 100) }))}">
            <defs><linearGradient id="${uid}g" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="rgb(var(--tone))" stop-opacity=".28"/><stop offset="1" stop-color="rgb(var(--tone))" stop-opacity="0"/></linearGradient>
              <clipPath id="${uid}c"><rect x="0" y="0" width="${lit[0].toFixed(1)}" height="59"/></clipPath></defs>
            <path d="M10 58 Q100 -34 190 58 Z" fill="url(#${uid}g)" clip-path="url(#${uid}c)"/>
            <path d="M10 58 Q100 -34 190 58" fill="none" stroke="rgba(255,255,255,.14)" stroke-width="1.2" stroke-dasharray="2 4"/>
            <path d="M10 58 Q100 -34 190 58" fill="none" stroke="rgb(var(--tone))" stroke-width="1.6" stroke-linecap="round" clip-path="url(#${uid}c)" opacity=".85"/>
            <line x1="0" y1="58.5" x2="200" y2="58.5" stroke="rgba(255,255,255,.12)"/>
            <line x1="100" y1="10" x2="100" y2="58" stroke="rgba(255,255,255,.06)" stroke-dasharray="1 3"/>
            ${up ? `<circle class="sc-sun" cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="5"/>` : `<circle class="sc-moon" cx="${(now < rise ? 10 : 190)}" cy="62" r="3.5"/>`}
          </svg>
          <div class="sc-ends"><span><b class="mono">${ctx.esc(ctx.when(rise))}</b><small>${ctx.esc(ctx.t("sunrise"))}</small></span><span class="sc-noon"><b class="mono">${ctx.esc(ctx.when(rise + daylight / 2))}</b><small>${ctx.esc(ctx.t("noon"))}</small></span><span><b class="mono">${ctx.esc(ctx.when(set))}</b><small>${ctx.esc(ctx.t("sunset"))}</small></span></div>
          <div class="sc-next">${ctx.icon(next[0] === "sunset" ? "moon" : "sun")}<span>${ctx.esc(ctx.t(`${next[0]}_in`, { t: dur(next[1] - now, ctx) }))}</span></div>
          <div class="sc-day"><span>${ctx.esc(ctx.t("daylight"))}</span><b>${ctx.esc(dur(daylight, ctx))}</b>${delta !== null && Math.abs(delta) >= 0.5 ? `<em class="${delta > 0 ? "up" : "down"}">${delta > 0 ? "+" : "−"}${ctx.esc(ctx.fmt(Math.abs(delta), { maximumFractionDigits: 0 }))} min</em>` : ""}</div>`;
      };
      paint();
      el._scTick = setInterval(() => { if (!el.isConnected) clearInterval(el._scTick); else paint(); }, 60000);
    },
    destroy(el) { clearInterval(el._scTick); },
  };
  NuxivaDesk.register("sun_cycle", impl);
})();
