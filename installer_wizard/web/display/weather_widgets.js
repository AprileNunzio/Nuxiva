(() => {
  const has = (v) => v !== null && v !== undefined && Number.isFinite(Number(v));
  const LEVEL_COLOR = { yellow: "#ffd166", orange: "#ff9a4d", red: "#ff5d73" };
  const SEVERITY_COLOR = { minor: "#ffd166", moderate: "#ffd166", severe: "#ff9a4d", extreme: "#ff5d73" };
  const INSIGHT_COLOR = { info: "#6cc1ff", warn: "#ffd166", alert: "#ff5d73" };
  const AQI_COLORS = ["#3ddc97", "#a6e22e", "#ffd166", "#ff9a4d", "#ff5d73", "#b24bf3"];
  const band = (value, limits) => { const i = limits.findIndex((l) => value <= l); return i < 0 ? limits.length : i; };

  const clock = (k, iso) => {
    if (!iso) return "";
    const date = new Date(iso.length <= 16 ? `${iso}:00` : iso);
    return Number.isNaN(date.getTime()) ? "" : date.toLocaleTimeString(k.loc, { hour: "2-digit", minute: "2-digit" });
  };
  const when = (k, iso) => {
    if (!iso) return "";
    const date = new Date(iso);
    return Number.isNaN(date.getTime()) ? "" : date.toLocaleString(k.loc, { weekday: "short", hour: "2-digit", minute: "2-digit" });
  };

  function alerts(data, k) {
    const list = Array.isArray(data.alerts) ? data.alerts : [];
    if (!list.length) return "";
    return `<section class="wx-alerts" data-prio="1" role="alert">${list.slice(0, 3).map((a) => {
      const color = LEVEL_COLOR[a.level] || SEVERITY_COLOR[a.severity] || "#ffd166";
      const until = a.expires ? k.t("wx_until", { time: when(k, a.expires) }) : "";
      return `<article class="wx-alert" style="--c:${color}"><b>${k.esc(a.event || a.headline)}</b>
        <span>${k.esc(a.area)}${until ? ` · ${k.esc(until)}` : ""}</span><small>${k.esc(k.t("wx_alert_source", { source: a.source }))}</small></article>`;
    }).join("")}</section>`;
  }

  function insightText(item, k) {
    const params = { value: has(item.value) ? Math.abs(item.value) : "", time: clock(k, item.time) };
    if (item.kind === "wind" && has(item.value)) params.value = `${k.U.wind(item.value)} ${k.U.windUnit}`;
    if (["heat", "frost", "warmer", "colder"].includes(item.kind) && has(item.value)) {
      params.value = item.kind === "warmer" || item.kind === "colder" ? `${Math.round(Math.abs(item.value) * (k.U.tempUnit === "°F" ? 1.8 : 1) * 10) / 10}°` : `${Math.round(k.U.temp(item.value))}°`;
    }
    if (item.kind === "rain_soon" && has(item.value)) params.value = `${k.U.precip(item.value)} ${k.U.precipUnit}`;
    return k.t(`wx_in_${item.kind}`, params);
  }

  function insights(data, k) {
    const list = (Array.isArray(data.insights) ? data.insights : []).filter((i) => i && typeof i.kind === "string");
    if (!list.length) return "";
    return `<ul class="wx-insights" data-prio="1">${list.slice(0, 6).map((i) =>
      `<li style="--c:${INSIGHT_COLOR[i.level] || INSIGHT_COLOR.info}" class="lv-${k.esc(i.level)}">${k.esc(insightText(i, k))}</li>`).join("")}</ul>`;
  }

  function nowcastTile(data, k) {
    const slots = Array.isArray(data.nowcast) ? data.nowcast.filter((s) => s && s.time) : [];
    if (slots.length < 2) return "";
    const max = Math.max(0.5, ...slots.map((s) => Number(s.rain) || 0));
    const dry = slots.every((s) => !(Number(s.rain) >= 0.1));
    const bars = slots.map((s) => `<i style="--h:${Math.min(1, (Number(s.rain) || 0) / max).toFixed(3)}" title="${k.esc(clock(k, s.time))} ${has(s.rain) ? k.U.precip(s.rain) : "—"} ${k.U.precipUnit}"></i>`).join("");
    return k.tile("wx-now", k.t("wx_nowcast"), `<div class="wx-bars${dry ? " dry" : ""}">${bars}</div>
      <div class="wx-bars-axis"><span>${k.esc(clock(k, slots[0].time))}</span><span>${k.esc(clock(k, slots[slots.length - 1].time))}</span></div>`,
      k.esc(dry ? k.t("wx_nowcast_dry") : k.t("wx_nowcast_wet")));
  }

  function yesterdayTile(data, k) {
    const y = data.yesterday, today = (data.days || [])[0];
    if (!y || !today || !has(y.tmax) || !has(today.tmax)) return "";
    const delta = Math.round((k.U.temp(today.tmax) - k.U.temp(y.tmax)) * 10) / 10;
    const arrow = delta >= 1 ? "↑" : delta <= -1 ? "↓" : "≈";
    const same = has(y.same_hour) && has(data.current.temp_exact) ? Math.round((k.U.temp(data.current.temp_exact) - k.U.temp(y.same_hour)) * 10) / 10 : null;
    return k.tile("wx-yday", k.t("wx_yesterday"), `<div class="wx-row"><b class="wx-big">${arrow} ${Math.abs(delta)}<small>°</small></b></div>
      <div class="wx-pair"><span>${k.esc(k.t("wx_yesterday_short"))} ${k.deg(y.tmax)} / ${k.deg(y.tmin)}</span><span>${k.esc(k.t("wx_today"))} ${k.deg(today.tmax)} / ${k.deg(today.tmin)}</span></div>`,
      same === null ? "" : k.esc(k.t("wx_yesterday_now", { value: `${same > 0 ? "+" : ""}${same}°` })));
  }

  function airDays(data, k) {
    const days = Array.isArray(data.air_days) ? data.air_days.filter((d) => d && has(d.aqi)) : [];
    if (days.length < 2) return "";
    return `<section class="wx-panel wx-airdays" data-prio="3"><h4>${k.esc(k.t("wx_air_days"))}</h4><div class="wx-aird">${days.map((d) => {
      const lv = band(d.aqi, [20, 40, 60, 80, 100]), names = ["good", "fair", "moderate", "poor", "very_poor", "extreme"];
      const top = Object.entries(d.pollen || {}).sort((a, b) => b[1] - a[1])[0];
      return `<div style="--c:${AQI_COLORS[lv]}"><b>${k.esc(new Date(`${d.iso}T12:00:00`).toLocaleDateString(k.loc, { weekday: "short" }))}</b>
        <span class="wx-aqi">${Math.round(d.aqi)}</span><small>${k.esc(k.t(`wx_aqi_${names[lv]}`))}</small>
        ${top && top[1] > 0 ? `<em>${k.esc(k.t(`wx_pl_${top[0]}`))} ${Math.round(top[1])}</em>` : ""}</div>`;
    }).join("")}</div></section>`;
  }

  function radar(data, k) {
    const r = data.radar;
    if (!r || !Array.isArray(r.frames) || !r.frames.length || !has(data.lat) || !has(data.lon)) return "";
    return `<section class="wx-panel wx-radar" data-prio="2"><h4>${k.esc(k.t("wx_radar"))}<span class="wx-rtime" data-radar-time></span></h4>
      <div class="wx-rmap" data-radar></div><p class="wx-foot">${k.esc(k.t("wx_radar_credit"))}</p></section>`;
  }

  const timers = new WeakMap();
  async function mount(root, data, loadLeaflet, locale) {
    const box = root.querySelector("[data-radar]"), r = data && data.radar;
    if (!box || !r || typeof loadLeaflet !== "function") return;
    try {
      const L = await loadLeaflet();
      const map = L.map(box, { zoomControl: false, attributionControl: true, fadeAnimation: false, dragging: false, scrollWheelZoom: false,
        doubleClickZoom: false, boxZoom: false, keyboard: false, touchZoom: false }).setView([data.lat, data.lon], 7);
      L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 7, className: "rm-tiles",
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' }).addTo(map);
      L.circleMarker([data.lat, data.lon], { radius: 5, color: "#fff", weight: 2, fillColor: "#29e0ff", fillOpacity: 1 }).addTo(map);
      const layers = r.frames.map((f) => L.tileLayer(`${r.host}${f.path}/256/{z}/{x}/{y}/2/1_1.png`, { opacity: 0, maxZoom: 7, maxNativeZoom: 7,
        attribution: '<a href="https://www.rainviewer.com/">RainViewer</a>' }).addTo(map));
      const label = root.querySelector("[data-radar-time]");
      let index = layers.length - 1;
      const show = (i) => {
        layers.forEach((layer, n) => layer.setOpacity(n === i ? 0.75 : 0));
        if (label) label.textContent = new Date(r.frames[i].time * 1000).toLocaleTimeString(locale, { hour: "2-digit", minute: "2-digit" });
      };
      show(index);
      if (!matchMedia("(prefers-reduced-motion: reduce)").matches && layers.length > 1) {
        const timer = setInterval(() => {
          if (!box.isConnected) { clearInterval(timer); map.remove(); return; }
          index = (index + 1) % layers.length;
          show(index);
        }, 900);
        timers.set(box, timer);
      }
      setTimeout(() => map.invalidateSize(), 300);
    } catch (err) {
      box.closest(".wx-radar")?.remove();
    }
  }

  window.NuxivaWeatherWidgets = Object.freeze({ alerts, insights, nowcastTile, yesterdayTile, airDays, radar, mount });
})();
