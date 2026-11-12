(() => {
  const timers = new WeakMap();
  const fmts = new Map();
  const zoneOk = (tz) => {
    if (typeof tz !== "string" || !/^[A-Za-z_]+(?:\/[A-Za-z0-9_+-]+){0,2}$|^UTC$/.test(tz) || tz.length > 40) return "";
    try { new Intl.DateTimeFormat("en", { timeZone: tz }); return tz; } catch (_) { return ""; }
  };
  const fmt = (loc, opts) => {
    const k = `${loc}|${JSON.stringify(opts)}`;
    if (!fmts.has(k)) fmts.set(k, new Intl.DateTimeFormat(loc, opts));
    return fmts.get(k);
  };
  const partsIn = (now, tz) => {
    const p = {};
    for (const x of fmt("en-GB", { timeZone: tz || undefined, hourCycle: "h23", year: "numeric", month: "numeric", day: "numeric", hour: "numeric", minute: "numeric", second: "numeric" }).formatToParts(now)) p[x.type] = Number(x.value);
    return p;
  };
  const week = (y, m, d) => {
    const t = new Date(Date.UTC(y, m - 1, d));
    t.setUTCDate(t.getUTCDate() + 4 - (t.getUTCDay() || 7));
    return Math.ceil(((t - Date.UTC(t.getUTCFullYear(), 0, 1)) / 864e5 + 1) / 7);
  };
  const dayOfYear = (y, m, d) => Math.round((Date.UTC(y, m - 1, d) - Date.UTC(y, 0, 0)) / 864e5);
  const ticks = () => Array.from({ length: 60 }, (_, i) => {
    const a = (i * Math.PI) / 30, big = i % 5 === 0, r1 = big ? 40 : 43, r2 = 46;
    return `<line class="${big ? "big" : ""}" x1="${50 + r1 * Math.sin(a)}" y1="${50 - r1 * Math.cos(a)}" x2="${50 + r2 * Math.sin(a)}" y2="${50 - r2 * Math.cos(a)}"/>`;
  }).join("");

  function tick(el, ctx) {
    const st = el._clock;
    if (!st || !el.isConnected) return;
    const now = new Date(), loc = ctx.locale(), p = partsIn(now, st.tz);
    st.hm.textContent = fmt(loc, { timeZone: st.tz || undefined, hour: "2-digit", minute: "2-digit" }).format(now);
    st.s.textContent = String(p.second).padStart(2, "0");
    st.day.textContent = fmt(loc, { timeZone: st.tz || undefined, weekday: "long", day: "numeric", month: "long", year: "numeric" }).format(now);
    st.week.textContent = String(week(p.year, p.month, p.day));
    st.doy.textContent = String(dayOfYear(p.year, p.month, p.day));
    const mins = p.hour * 60 + p.minute + p.second / 60;
    st.bar.style.width = `${(mins / 1440) * 100}%`;
    st.hh.style.transform = `rotate(${((p.hour % 12) + p.minute / 60) * 30}deg)`;
    st.mh.style.transform = `rotate(${(p.minute + p.second / 60) * 6}deg)`;
    if (p.second < st.lastSec) st.turns += 1;
    st.lastSec = p.second;
    st.sh.style.transform = `rotate(${st.turns * 360 + p.second * 6}deg)`;
    st.zones.forEach((z) => {
      z.time.textContent = fmt(loc, { timeZone: z.tz, hour: "2-digit", minute: "2-digit" }).format(now);
      const q = partsIn(now, z.tz), diff = Math.round(((Date.UTC(q.year, q.month - 1, q.day, q.hour, q.minute) - Date.UTC(p.year, p.month - 1, p.day, p.hour, p.minute)) / 36e5) * 2) / 2;
      z.off.textContent = diff === 0 ? "±0h" : `${diff > 0 ? "+" : "−"}${Math.abs(diff)}h`;
    });
  }

  function schedule(el, ctx) {
    clearTimeout(timers.get(el));
    const run = () => {
      if (!el.isConnected) return;
      tick(el, ctx);
      timers.set(el, setTimeout(run, 1000 - (Date.now() % 1000) + 5));
    };
    run();
  }

  NuxivaDesk.register("clock", {
    render(el, d, ctx) {
      const data = d && typeof d === "object" ? d : {};
      const tz = zoneOk(data.timezone ?? data.tz);
      const city = ctx.str(data.city, 40);
      const zones = ctx.arr(data.zones, 4).map((z) => (z && typeof z === "object" ? { tz: zoneOk(z.tz ?? z.timezone), city: ctx.pick(z, ["city", "name", "label"], 30) } : null)).filter((z) => z && z.tz);
      el.innerHTML = `${ctx.head({ icon: "clock", label: ctx.t("label"), title: city || (tz ? tz.split("/").pop().replace(/_/g, " ") : "") })}
        <div class="ck-main">
          <svg class="ck-face" viewBox="0 0 100 100" aria-hidden="true"><circle class="ck-rim" cx="50" cy="50" r="48"/><g class="ck-ticks">${ticks()}</g>
            <line class="ck-h" x1="50" y1="54" x2="50" y2="28"/><line class="ck-m" x1="50" y1="56" x2="50" y2="14"/><line class="ck-sec" x1="50" y1="60" x2="50" y2="8"/><circle class="ck-pin" cx="50" cy="50" r="2.2"/></svg>
          <div class="ck-digital">
            <div class="wk-hero"><span class="wk-num ck-hm" role="timer" aria-live="off"></span><span class="wk-num sm wk-faint ck-s"></span></div>
            <div class="wk-sub ck-day"></div>
            <div class="wk-sub ck-meta"><span>${ctx.esc(ctx.t("week"))} <b class="wk-mono ck-week"></b></span><span>${ctx.esc(ctx.t("day_of_year"))} <b class="wk-mono ck-doy"></b></span></div>
          </div>
        </div>
        <span class="wk-bar ck-bar" title="${ctx.esc(ctx.t("day_progress"))}"><i></i></span>
        ${zones.length ? `<ul class="ck-zones">${zones.map((z) => `<li><span>${ctx.esc(z.city || z.tz.split("/").pop().replace(/_/g, " "))}</span><b class="wk-mono"></b><small class="wk-mono"></small></li>`).join("")}</ul>` : ""}`;
      const q = (s) => el.querySelector(s);
      el._clock = {
        tz, turns: 0, lastSec: 0, hm: q(".ck-hm"), s: q(".ck-s"), day: q(".ck-day"), week: q(".ck-week"), doy: q(".ck-doy"), bar: q(".ck-bar > i"),
        hh: q(".ck-h"), mh: q(".ck-m"), sh: q(".ck-sec"),
        zones: [...el.querySelectorAll(".ck-zones li")].map((li, i) => ({ tz: zones[i].tz, time: li.querySelector("b"), off: li.querySelector("small") })),
      };
      schedule(el, ctx);
    },
    destroy(el) { clearTimeout(timers.get(el)); el._clock = null; },
  });
})();
