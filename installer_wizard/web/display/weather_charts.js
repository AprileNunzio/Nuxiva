(() => {
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  const num = (v) => (typeof v === "number" && Number.isFinite(v) ? v : null);
  const f1 = (v) => v.toFixed(1);

  function smooth(points) {
    if (points.length < 2) return "";
    let d = `M${f1(points[0][0])} ${f1(points[0][1])}`;
    for (let i = 0; i < points.length - 1; i++) {
      const p0 = points[i - 1] || points[i], p1 = points[i], p2 = points[i + 1], p3 = points[i + 2] || p2;
      const c1 = [p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6];
      const c2 = [p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6];
      d += `C${f1(c1[0])} ${f1(c1[1])} ${f1(c2[0])} ${f1(c2[1])} ${f1(p2[0])} ${f1(p2[1])}`;
    }
    return d;
  }

  function hourly(rows, o) {
    const items = rows.filter((r) => num(r.temp) !== null);
    if (items.length < 2) return "";
    const W = Math.max(520, items.length * 46), H = 150, top = 26, bottom = 44, left = 20, step = (W - left * 2) / (items.length - 1);
    const temps = items.map((r) => o.temp(r.temp)), lo = Math.min(...temps), hi = Math.max(...temps), span = Math.max(1, hi - lo);
    const y = (t) => top + (1 - (t - lo) / span) * (H - top - bottom);
    const pts = items.map((r, i) => [left + i * step, y(o.temp(r.temp))]);
    const line = smooth(pts), area = `${line}L${f1(pts[pts.length - 1][0])} ${H - bottom + 14}L${f1(pts[0][0])} ${H - bottom + 14}Z`;
    const bars = items.map((r, i) => {
      const p = clamp(num(r.rain_prob) ?? 0, 0, 100), h = (p / 100) * 30;
      return p >= 5 ? `<rect class="wxc-rain" x="${f1(pts[i][0] - 7)}" y="${f1(H - bottom + 14 - h)}" width="14" height="${f1(h)}" rx="3"><title>${p}%</title></rect>` : "";
    }).join("");
    const dots = items.map((r, i) => `<g class="wxc-pt" style="animation-delay:${i * 18}ms"><circle cx="${f1(pts[i][0])}" cy="${f1(pts[i][1])}" r="${i === 0 ? 5 : 2.6}" class="${i === 0 ? "wxc-now" : "wxc-dot"}"/>
      ${i % 2 === 0 || items.length < 14 ? `<text x="${f1(pts[i][0])}" y="${f1(pts[i][1] - 10)}" class="wxc-val">${Math.round(temps[i])}°</text>` : ""}</g>`).join("");
    const labels = items.map((r, i) => (i % o.every === 0 ? `<text x="${f1(pts[i][0])}" y="${H - 2}" class="wxc-hour">${o.hour(r.time)}</text>` : "")).join("");
    const icons = items.map((r, i) => (i % o.every === 0 ? `<foreignObject x="${f1(pts[i][0] - 12)}" y="${H - bottom + 17}" width="24" height="24">${o.icon(r.icon, 24)}</foreignObject>` : "")).join("");
    return `<svg class="wxc-hourly" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet" role="img" aria-label="${o.label}" style="min-width:${Math.min(W, 880)}px">
      <defs><linearGradient id="wxc-fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#29e0ff" stop-opacity=".45"/><stop offset="1" stop-color="#29e0ff" stop-opacity="0"/></linearGradient>
      <linearGradient id="wxc-line" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#ffd166"/><stop offset=".5" stop-color="#29e0ff"/><stop offset="1" stop-color="#9d7bff"/></linearGradient></defs>
      <path d="${area}" fill="url(#wxc-fill)"/>${bars}<path d="${line}" class="wxc-line" pathLength="1"/>${dots}${labels}${icons}</svg>`;
  }

  function compass(deg, speed, gust, unit, names) {
    const a = num(deg) ?? 0;
    const ticks = Array.from({ length: 36 }, (_, i) => `<line x1="60" y1="${i % 9 === 0 ? 8 : 11}" x2="60" y2="${i % 3 === 0 ? 16 : 14}" transform="rotate(${i * 10} 60 60)" class="wxc-tick"/>`).join("");
    return `<svg class="wxc-compass" viewBox="0 0 120 120" aria-hidden="true"><circle cx="60" cy="60" r="52" class="wxc-ring"/>${ticks}
      <text x="60" y="30" class="wxc-card">${names[0]}</text><text x="95" y="64" class="wxc-card">${names[1]}</text><text x="60" y="98" class="wxc-card">${names[2]}</text><text x="25" y="64" class="wxc-card">${names[3]}</text>
      <g class="wxc-needle" style="transform:rotate(${a + 180}deg);transform-origin:60px 60px"><path d="M60 22l7 26H53z" class="wxc-arrow"/><path d="M60 98V48" class="wxc-shaft"/></g>
      <text x="60" y="66" class="wxc-speed">${speed ?? "—"}</text><text x="60" y="78" class="wxc-unit">${unit}${gust ? ` · ↯${gust}` : ""}</text></svg>`;
  }

  function arc(value, max, colors, text, sub) {
    const p = clamp((num(value) ?? 0) / max, 0, 1), r = 44, c = Math.PI * r, off = c * (1 - p);
    const stops = colors.map((col, i) => `<stop offset="${(i / (colors.length - 1)).toFixed(2)}" stop-color="${col}"/>`).join("");
    const id = `wxa${Math.random().toString(36).slice(2, 8)}`;
    return `<svg class="wxc-arc" viewBox="0 0 120 76" aria-hidden="true"><defs><linearGradient id="${id}" x1="0" y1="0" x2="1" y2="0">${stops}</linearGradient></defs>
      <path d="M16 62A44 44 0 0 1 104 62" class="wxc-track"/><path d="M16 62A44 44 0 0 1 104 62" class="wxc-fillarc" stroke="url(#${id})" style="stroke-dasharray:${f1(c)};stroke-dashoffset:${f1(off)}"/>
      <text x="60" y="52" class="wxc-big">${text}</text><text x="60" y="68" class="wxc-sub">${sub || ""}</text></svg>`;
  }

  function water(percent) {
    const p = clamp(num(percent) ?? 0, 0, 100), y = 56 - p * 0.5;
    return `<svg class="wxc-water" viewBox="0 0 60 64" aria-hidden="true"><defs><clipPath id="wxw"><path d="M30 4C20 20 10 28 10 40a20 20 0 0 0 40 0C50 28 40 20 30 4z"/></clipPath></defs>
      <path d="M30 4C20 20 10 28 10 40a20 20 0 0 0 40 0C50 28 40 20 30 4z" class="wxc-drop"/><g clip-path="url(#wxw)"><path class="wxc-wave" d="M0 ${y}q15-6 30 0t30 0V64H0z"/></g></svg>`;
  }

  function sunArc(rise, set, nowMin, labels) {
    const toMin = (s) => { const m = /^(\d{1,2}):(\d{2})$/.exec(s || ""); return m ? Number(m[1]) * 60 + Number(m[2]) : null; };
    const a = toMin(rise), b = toMin(set);
    if (a === null || b === null || b <= a) return "";
    const p = clamp((nowMin - a) / (b - a), 0, 1), ang = Math.PI * (1 - p), x = 60 + 46 * Math.cos(ang), y = 62 - 46 * Math.sin(ang);
    const up = nowMin >= a && nowMin <= b;
    return `<svg class="wxc-sunarc" viewBox="0 0 120 78" aria-hidden="true"><path d="M14 62A46 46 0 0 1 106 62" class="wxc-track"/>
      <path d="M14 62A46 46 0 0 1 106 62" class="wxc-sunpath" style="stroke-dasharray:${f1(Math.PI * 46)};stroke-dashoffset:${f1(Math.PI * 46 * (1 - p))}"/>
      <line x1="8" y1="62" x2="112" y2="62" class="wxc-horizon"/>${up ? `<circle cx="${f1(x)}" cy="${f1(y)}" r="6" class="wxc-sunpoint"/>` : ""}
      <text x="14" y="74" class="wxc-sub" text-anchor="middle">${rise}</text><text x="106" y="74" class="wxc-sub" text-anchor="middle">${set}</text>
      <text x="60" y="48" class="wxc-sub" text-anchor="middle">${labels}</text></svg>`;
  }

  function moon(fraction) {
    const f = clamp(num(fraction) ?? 0, 0, 1), waxing = f < 0.5, k = Math.cos(2 * Math.PI * f), rx = Math.abs(k) * 22;
    const shade = k > 0 ? "dark" : "light";
    const lit = waxing ? `M30 8A22 22 0 0 1 30 52` : `M30 8A22 22 0 0 0 30 52`;
    const term = `M30 8A${f1(rx)} 22 0 0 ${(waxing ? k < 0 : k > 0) ? 1 : 0} 30 52`;
    return `<svg class="wxc-moon" viewBox="0 0 60 60" aria-hidden="true"><circle cx="30" cy="30" r="22" class="wxc-moonbase"/>
      <path d="${lit}${term}Z" class="wxc-moonlit ${shade}"/><circle cx="30" cy="30" r="22" class="wxc-moonedge"/></svg>`;
  }

  function range(min, max, lo, hi) {
    const span = Math.max(1, hi - lo), l = clamp(((min - lo) / span) * 100, 0, 100), w = clamp(((max - min) / span) * 100, 3, 100 - l);
    return `<span class="wxc-range"><i style="left:${f1(l)}%;width:${f1(w)}%"></i></span>`;
  }

  function weekChart(days, o) {
    const items = days.filter((d) => num(d.tmax) !== null);
    if (items.length < 2) return "";
    const W = Math.max(560, items.length * 70), H = 160, left = 30, step = (W - left * 2) / (items.length - 1);
    const hi = items.map((d) => o.temp(d.tmax)), lo = items.map((d) => o.temp(d.tmin)), top = Math.max(...hi), bottom = Math.min(...lo), span = Math.max(1, top - bottom);
    const y = (t) => 26 + (1 - (t - bottom) / span) * 80;
    const hp = items.map((d, i) => [left + i * step, y(hi[i])]), lp = items.map((d, i) => [left + i * step, y(lo[i])]);
    const bars = items.map((d, i) => { const h = clamp(num(d.rain) ?? 0, 0, 100) * 0.32; return h > 2 ? `<rect class="wxc-rain" x="${f1(hp[i][0] - 9)}" y="${f1(150 - h)}" width="18" height="${f1(h)}" rx="3"><title>${d.rain}%</title></rect>` : ""; }).join("");
    const labels = items.map((d, i) => `<text x="${f1(hp[i][0])}" y="${f1(hp[i][1] - 9)}" class="wxc-val">${Math.round(hi[i])}°</text><text x="${f1(lp[i][0])}" y="${f1(lp[i][1] + 17)}" class="wxc-val low">${Math.round(lo[i])}°</text>
      <text x="${f1(hp[i][0])}" y="12" class="wxc-hour">${o.day(d)}</text>`).join("");
    return `<svg class="wxc-week" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet" role="img" aria-label="${o.label}" style="min-width:${Math.min(W, 760)}px">
      ${bars}<path d="${smooth(hp)}" class="wxc-line hot" pathLength="1"/><path d="${smooth(lp)}" class="wxc-line cold" pathLength="1"/>${labels}</svg>`;
  }

  window.NuxivaWeatherCharts = Object.freeze({ hourly, compass, arc, water, sunArc, moon, range, weekChart });
})();
