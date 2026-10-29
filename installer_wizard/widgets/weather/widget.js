(() => {
  const HEAD = { clear: "sun", night: "moon", partly: "partly", night_partly: "moon", cloudy: "cloud", fog: "fog", drizzle: "rain", rain: "rain", snow: "snow", storm: "storm" };
  const KEYS = Object.keys(HEAD);
  const icon = (k) => (window.NuxivaIcons && typeof window.NuxivaIcons.weather === "function" ? window.NuxivaIcons.weather(k) : "");
  const finite = (v) => v !== null && v !== undefined && v !== "" && Number.isFinite(Number(v));
  const round = (v) => (finite(v) ? Math.round(Number(v)) : null);
  const key = (v) => { const s = String(v ?? "").toLowerCase(); return KEYS.includes(s) ? s : "cloudy"; };
  const ISO = /^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}(:\d{2})?)?/;

  function normalize(d, ctx) {
    const src = d && typeof d === "object" ? d : {};
    const cur = src.current && typeof src.current === "object" ? src.current : null;
    const hourly = ctx.arr(src.hourly).filter((h) => h && typeof h === "object" && ISO.test(String(h.time || ""))).slice(0, 48);
    const days = ctx.arr(src.days).filter((x) => x && typeof x === "object").slice(0, 10);
    const units = src.units && typeof src.units === "object" ? src.units : {};
    return { ...src, current: cur, hourly, days, units, location: ctx.str(src.location, 80), source: ctx.str(src.source, 60), stale: src.stale === true, fetched: ctx.num(src.fetched) };
  }

  function rainSoon(w, ctx) {
    const now = ctx.now() * 1000;
    const next = w.hourly.find((h) => {
      const at = Date.parse(h.time);
      return Number.isFinite(at) && at >= now - 3600e3 && at <= now + 6 * 3600e3 && (Number(h.rain_prob) >= 50 || Number(h.rain) >= 0.5);
    });
    if (!next) return "";
    const at = Date.parse(next.time);
    return at <= now ? ctx.t("rain_now") : ctx.t("rain_at", { time: ctx.when(at) });
  }

  function chip(w, ctx) {
    if (w.stale) return ctx.t("stale");
    if (w.fetched) return ctx.ago(w.fetched);
    return "";
  }

  function legacy(w, ctx) {
    const c = w.current;
    const days = w.days.slice(1, 5);
    const feels = round(c.feels), wind = round(c.wind), temp = round(c.temp);
    return `<div class="wk-hero"><span class="wk-big">${icon(key(c.icon))}</span><span class="wk-num">${temp ?? "—"}<sup>°</sup></span>
        <span class="wk-sub"><span>${ctx.esc(ctx.str(c.desc, 60))}</span><br><span>${ctx.esc(ctx.t("feels", { feels: feels ?? "—", wind: wind ?? "—" }))}</span></span></div>
      ${days.length ? `<div class="wk-days">${days.map((x) => {
        const rain = round(x.rain);
        return `<div><b>${ctx.esc(ctx.str(x.label || x.date, 12).slice(0, 3))}</b>${icon(key(x.icon))}
          <span>${round(x.tmax) ?? "—"}° <small>${round(x.tmin) ?? "—"}°</small></span>${rain !== null && rain >= 40 ? `<small class="wk-accent">${rain}%</small>` : ""}</div>`;
      }).join("")}</div>` : ""}`;
  }

  function body(w, ctx) {
    if (window.NuxivaWeather && typeof window.NuxivaWeather.compact === "function" && w.hourly.length && window.PageText) {
      try {
        const html = window.NuxivaWeather.compact(w, { t: (k, p) => window.PageText.t("web/display", k, p), locale: ctx.locale() });
        if (html) return html;
      } catch (e) {
        console.warn("weather", e);
      }
    }
    return legacy(w, ctx);
  }

  const impl = {
    render(el, d, ctx) {
      const w = normalize(d, ctx);
      const head = (ic, state) => ctx.head({ icon: ic, label: ctx.t("label"), title: w.location, chip: chip(w, ctx), state });
      if (!w.current) {
        el.innerHTML = `${head("partly")}${ctx.empty(ctx.t("empty"))}`;
        return;
      }
      const rain = rainSoon(w, ctx);
      el.innerHTML = `${head(HEAD[key(w.current.icon)], w.stale ? "warn" : "")}${rain ? `<p class="wk-alert-hint wt-rain">${ctx.icon("rain")}<span>${ctx.esc(rain)}</span></p>` : ""}${body(w, ctx)}${w.stale ? `<p class="wk-alert-hint wt-stale">${ctx.icon("alert")}<span>${ctx.esc(ctx.t("stale_hint"))}</span></p>` : ""}`;
    },
  };
  NuxivaDesk.register("weather", impl);
})();
