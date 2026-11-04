(() => {
  const I = window.NuxivaWeatherIcons, C = window.NuxivaWeatherCharts;
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const has = (v) => v !== null && v !== undefined && Number.isFinite(Number(v));
  const AQI_COLORS = ["#3ddc97", "#a6e22e", "#ffd166", "#ff9a4d", "#ff5d73", "#b24bf3"];
  const UV_COLORS = ["#3ddc97", "#ffd166", "#ff9a4d", "#ff5d73", "#b24bf3"];

  function units(u = {}) {
    const imperial = u.temp === "f";
    const wind = u.wind || "kmh";
    const speed = { kmh: [1, "km/h"], ms: [1 / 3.6, "m/s"], mph: [0.621371, "mph"], kn: [0.539957, "kn"] }[wind] || [1, "km/h"];
    return {
      temp: (c) => (imperial ? c * 1.8 + 32 : c), tempUnit: imperial ? "°F" : "°C",
      wind: (k) => (has(k) ? Math.round(k * speed[0] * (speed[0] < 1 && wind === "ms" ? 10 : 1)) / (wind === "ms" ? 10 : 1) : null), windUnit: speed[1],
      precip: (mm) => (has(mm) ? (u.precip === "in" ? Math.round(mm * 0.03937 * 100) / 100 : mm) : null), precipUnit: u.precip === "in" ? "in" : "mm",
      pressure: (h) => (has(h) ? (u.pressure === "inhg" ? (h * 0.02953).toFixed(2) : Math.round(h)) : null), pressureUnit: u.pressure === "inhg" ? "inHg" : "hPa",
      dist: (km) => (has(km) ? (u.distance === "mi" ? (km * 0.621371).toFixed(1) : km) : null), distUnit: u.distance === "mi" ? "mi" : "km",
    };
  }

  function make(data, opts) {
    const t = (k, p) => opts.t(k, p) || k, U = units(data.units), loc = opts.locale || "it-IT";
    const deg = (c) => `${Math.round(U.temp(c))}°`;
    const cond = (code, fallback) => { const v = opts.t(`wx_c${code}`); return v && v !== `wx_c${code}` ? v : fallback || ""; };
    const dirName = (name) => String(name || "").split("").map((ch) => ({ N: t("wx_c_n"), E: t("wx_c_e"), S: t("wx_c_s"), W: t("wx_c_w") }[ch] || ch)).join("");
    const hourLabel = (iso) => new Date(iso).toLocaleTimeString(loc, { hour: "2-digit", minute: "2-digit" }).replace(/:00$/, "");
    const dayName = (d, long) => new Date(`${d.iso}T12:00:00`).toLocaleDateString(loc, { weekday: long ? "long" : "short" });
    const rel = (d, i) => (i === 0 ? t("wx_today") : i === 1 ? t("wx_tomorrow") : dayName(d, true));
    const tile = (cls, title, body, foot) => `<section class="wx-tile ${cls}"><h4>${esc(title)}</h4>${body}${foot ? `<p class="wx-foot">${foot}</p>` : ""}</section>`;
    return { t, U, deg, cond, dirName, hourLabel, dayName, rel, tile, loc, esc };
  }

  function band(value, limits) { const i = limits.findIndex((l) => value <= l); return i < 0 ? limits.length : i; }

  function tiles(data, k) {
    const { t, U, tile, esc: e } = k, c = data.current, day = (data.days || [])[k.focus] || {}, out = [];
    const toKmh = (v) => v;
    out.push(tile("wx-wind", t("wx_wind"), C.compass(c.dir, U.wind(toKmh(c.wind)), has(c.gust) ? U.wind(c.gust) : "", U.windUnit, ["N", "E", "S", "W"].map((x) => k.dirName(x))),
      `${esc(k.dirName(c.dir_name))} · ${t("wx_gust")} ${U.wind(c.gust) ?? "—"} ${U.windUnit}`));
    if (has(c.humidity)) out.push(tile("wx-hum", t("wx_humidity"), `<div class="wx-row">${C.water(c.humidity)}<b class="wx-big">${Math.round(c.humidity)}<small>%</small></b></div>`,
      has(c.dew) ? `${t("wx_dew")} ${k.deg(c.dew)}` : ""));
    const air = data.air;
    if (air && has(air.aqi)) {
      const level = band(air.aqi, [20, 40, 60, 80, 100]);
      out.push(tile("wx-air", t("wx_air"), C.arc(air.aqi, 120, AQI_COLORS, Math.round(air.aqi), t(`wx_aqi_${air.level || "good"}`)),
        `PM2.5 ${air.pm25 ?? "—"} · PM10 ${air.pm10 ?? "—"} · O₃ ${air.o3 ?? "—"}<br>NO₂ ${air.no2 ?? "—"} · SO₂ ${air.so2 ?? "—"} <span class="wx-tag" style="--c:${AQI_COLORS[level]}">US ${air.us_aqi ?? "—"}</span>`));
    }
    const uv = has(day.uv) && k.focus > 0 ? day.uv : has(c.uv) ? c.uv : day.uv;
    if (has(uv)) {
      const lv = band(uv, [2.9, 5.9, 7.9, 10.9]), names = ["low", "moderate", "high", "very_high", "extreme"];
      out.push(tile("wx-uv", t("wx_uv"), C.arc(uv, 12, UV_COLORS, uv, t(`wx_uv_${names[lv]}`)), t(`wx_uv_tip_${names[lv]}`)));
    }
    if (has(c.pressure)) {
      const arrow = { rising: "↗", falling: "↘", steady: "→" }[c.pressure_trend] || "";
      out.push(tile("wx-press", t("wx_pressure"), C.arc(Math.max(0, c.pressure - 960), 90, ["#6cc1ff", "#29e0ff", "#ffd166"], U.pressure(c.pressure), U.pressureUnit),
        `${arrow} ${c.pressure_trend ? t(`wx_trend_${c.pressure_trend}`) : ""}`));
    }
    if (has(c.visibility)) out.push(tile("wx-vis", t("wx_visibility"), `<b class="wx-big">${U.dist(c.visibility)}<small>${U.distUnit}</small></b>`, `${t("wx_cloud")} ${c.cloud ?? "—"}%`));
    const rain = has(day.rain_sum) ? day.rain_sum : c.rain_now;
    out.push(tile("wx-rain", t("wx_rain"), `<b class="wx-big">${day.rain ?? 0}<small>%</small></b><div class="wx-bar"><i style="width:${Math.min(100, day.rain ?? 0)}%"></i></div>`,
      `${U.precip(rain) ?? 0} ${U.precipUnit}${has(day.rain_hours) && day.rain_hours ? ` · ${day.rain_hours} ${t("wx_hours")}` : ""}${has(day.snow_sum) && day.snow_sum ? ` · ❄ ${day.snow_sum} cm` : ""}`));
    if (day.sunrise) {
      const now = new Date(), minutes = k.focus === 0 ? now.getHours() * 60 + now.getMinutes() : 720;
      const span = has(day.daylight_min) ? `${Math.floor(day.daylight_min / 60)}h ${day.daylight_min % 60}m` : "";
      out.push(tile("wx-sun", t("wx_sun"), C.sunArc(day.sunrise, day.sunset, minutes, span), has(day.sun_min) ? `${t("wx_sunshine")} ${Math.floor(day.sun_min / 60)}h ${day.sun_min % 60}m` : ""));
    }
    if (data.astro) out.push(tile("wx-moon", t("wx_moon"), `<div class="wx-row">${C.moon(data.astro.fraction)}<b class="wx-big">${data.astro.illumination}<small>%</small></b></div>`,
      `${t(`wx_moon_${data.astro.phase}`)}<br>${t("wx_full")} ${new Date(data.astro.next_full).toLocaleDateString(k.loc, { day: "numeric", month: "short" })}`));
    const pollen = air && air.pollen ? Object.entries(air.pollen).filter(([, v]) => v.level) : [];
    if (pollen.length) out.push(tile("wx-pollen", t("wx_pollen"), `<div class="wx-chips">${pollen.map(([n, v]) =>
      `<span class="wx-chip lv-${e(v.level)}" title="${e(v.value)}">${t(`wx_pl_${n}`)}<i>${t(`wx_plv_${v.level}`)}</i></span>`).join("")}</div>`));
    return out.join("");
  }

  function hero(data, k) {
    const c = data.current, day = (data.days || [])[k.focus] || {}, today = k.focus === 0;
    const icon = today ? c.icon : day.icon, code = today ? c.code : day.code, desc = k.cond(code, today ? c.desc : day.desc);
    const big = today ? c.temp : day.tmax;
    const stamp = new Date(today ? Date.now() : `${day.iso}T12:00:00`).toLocaleDateString(k.loc, { weekday: "long", day: "numeric", month: "long" });
    return `<header class="wx-hero"><div class="wx-sky" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i><i></i></div>
      <div class="wx-place"><b>${k.esc(data.location)}</b><span>${k.esc(stamp)}${data.detail ? ` · ${k.esc(data.detail)}` : ""}</span></div>
      <div class="wx-main"><div class="wx-ico">${I.icon(icon, 96)}</div>
        <div class="wx-temp"><span>${has(big) ? Math.round(k.U.temp(big)) : "—"}</span><sup>${k.U.tempUnit}</sup></div>
        <div class="wx-desc"><b>${k.esc(desc)}</b>
          <span>${today ? `${k.t("wx_feels")} ${k.deg(c.feels)}` : `${k.t("wx_feels")} ${has(day.feels_max) ? k.deg(day.feels_max) : "—"}`}</span>
          <span>▲ ${has(day.tmax) ? k.deg(day.tmax) : "—"} &nbsp; ▼ ${has(day.tmin) ? k.deg(day.tmin) : "—"}</span></div></div></header>`;
  }

  function hourlyBlock(data, k) {
    const date = (data.days || [])[k.focus] && data.days[k.focus].iso, rows = (data.hourly || []).filter((h) => k.focus === 0 || (date && h.time.startsWith(date)));
    const shown = rows.slice(0, data.view === "week" ? 24 : 36);
    if (shown.length < 3) return "";
    return `<section class="wx-panel"><h4>${k.esc(k.t("wx_hourly"))}</h4><div class="wx-scroll">${C.hourly(shown, {
      temp: k.U.temp, hour: k.hourLabel, every: shown.length > 24 ? 4 : shown.length > 12 ? 3 : 2, icon: I.icon, label: k.t("wx_hourly") })}</div></section>`;
  }

  function strip(data, k) {
    const days = data.days || [];
    return `<section class="wx-panel"><h4>${k.esc(k.t("wx_next_days"))}</h4><div class="wx-strip">${days.slice(0, 7).map((d, i) => `<div class="wx-mini ${i === k.focus ? "on" : ""}">
      <b>${k.esc(k.rel(d, i))}</b>${I.icon(d.icon, 34)}<span>${k.deg(d.tmax)} <small>${k.deg(d.tmin)}</small></span><em>☂ ${d.rain ?? 0}%</em></div>`).join("")}</div></section>`;
  }

  function weekRows(data, k) {
    const days = data.days || [], lo = Math.min(...days.map((d) => k.U.temp(d.tmin))), hi = Math.max(...days.map((d) => k.U.temp(d.tmax)));
    const rows = days.map((d, i) => `<div class="wx-row-day" style="animation-delay:${i * 45}ms">
      <div class="wx-dn"><b>${k.esc(k.rel(d, i))}</b><small>${k.esc(d.date)}</small></div>${I.icon(d.icon, 38)}
      <div class="wx-dd">${k.esc(k.cond(d.code, d.desc))}</div>
      <div class="wx-rg"><span>${k.deg(d.tmin)}</span>${C.range(k.U.temp(d.tmin), k.U.temp(d.tmax), lo, hi)}<span>${k.deg(d.tmax)}</span></div>
      <div class="wx-st" title="${k.esc(k.t("wx_rain"))}">☂ ${d.rain ?? 0}%<small>${k.U.precip(d.rain_sum) ?? 0} ${k.U.precipUnit}</small></div>
      <div class="wx-st" title="${k.esc(k.t("wx_wind"))}"><i class="wx-arrow" style="transform:rotate(${(d.dir ?? 0) + 180}deg)">↑</i> ${k.U.wind(d.wind) ?? "—"}<small>${k.U.windUnit}${has(d.gust) ? ` · ↯${k.U.wind(d.gust)}` : ""}</small></div>
      <div class="wx-st" title="${k.esc(k.t("wx_uv"))}">UV <b class="uv-${has(d.uv) ? band(d.uv, [2.9, 5.9, 7.9, 10.9]) : 0}">${d.uv ?? "—"}</b><small>☀ ${k.esc(d.sunrise)}–${k.esc(d.sunset)}</small></div></div>`).join("");
    return `<section class="wx-panel"><h4>${k.esc(k.t("wx_week"))}</h4><div class="wx-scroll">${C.weekChart(days, { temp: k.U.temp, day: (d) => k.dayName(d, false), label: k.t("wx_week") })}</div>
      <div class="wx-days">${rows}</div></section>`;
  }

  function render(data, opts) {
    if (!data || !data.current || !Array.isArray(data.days) || !data.days.length) return "";
    const k = make(data, opts);
    k.focus = Math.max(0, Math.min(data.days.length - 1, Number(data.focus) || 0));
    const theme = I.theme(k.focus === 0 ? data.current.icon : data.days[k.focus].icon);
    const view = data.view === "week" ? "week" : "day";
    const body = view === "week"
      ? `${hero(data, k)}${weekRows(data, k)}<div class="wx-tiles">${tiles(data, k)}</div>`
      : `${hero(data, k)}${hourlyBlock(data, k)}<div class="wx-tiles">${tiles(data, k)}</div>${strip(data, k)}`;
    return `<div class="wx wx-${view} wx-theme-${theme} ${opts.compact ? "wx-compact" : ""}">${body}<p class="wx-credit">${k.esc(data.source || "")}${data.stale ? ` · ${k.esc(k.t("wx_stale"))}` : ""}</p></div>`;
  }

  function compact(data, opts) {
    if (!data || !data.current) return "";
    const k = make(data, opts), c = data.current, today = (data.days || [])[0] || {}, rows = (data.hourly || []).slice(0, 12);
    const next = (data.days || []).slice(1, 5);
    return `<div class="wx wx-mini-card wx-theme-${I.theme(c.icon)}"><div class="wx-sky" aria-hidden="true"><i></i><i></i><i></i><i></i></div>
      <div class="wx-mc-top"><div class="wx-ico">${I.icon(c.icon, 64)}</div><div class="wx-temp"><span>${has(c.temp) ? Math.round(k.U.temp(c.temp)) : "—"}</span><sup>${k.U.tempUnit}</sup></div>
        <div class="wx-desc"><b>${k.esc(k.cond(c.code, c.desc))}</b><span>${k.t("wx_feels")} ${k.deg(c.feels)}</span><span>▲ ${has(today.tmax) ? k.deg(today.tmax) : "—"} ▼ ${has(today.tmin) ? k.deg(today.tmin) : "—"}</span></div></div>
      <div class="wx-scroll">${rows.length > 3 ? C.hourly(rows, { temp: k.U.temp, hour: k.hourLabel, every: 3, icon: I.icon, label: k.t("wx_hourly") }) : ""}</div>
      <div class="wx-mc-facts"><span>💨 ${k.U.wind(c.wind) ?? "—"} ${k.U.windUnit} ${k.esc(k.dirName(c.dir_name))}</span><span>💧 ${c.humidity ?? "—"}%</span>
        <span>☂ ${today.rain ?? 0}%</span>${has(c.uv) ? `<span>UV ${c.uv}</span>` : ""}${data.air && has(data.air.aqi) ? `<span>AQI ${Math.round(data.air.aqi)}</span>` : ""}</div>
      <div class="wx-strip">${next.map((d, i) => `<div class="wx-mini"><b>${k.esc(k.rel(d, i + 1))}</b>${I.icon(d.icon, 28)}<span>${k.deg(d.tmax)} <small>${k.deg(d.tmin)}</small></span></div>`).join("")}</div></div>`;
  }

  window.NuxivaWeather = Object.freeze({ render, compact, units });
})();
