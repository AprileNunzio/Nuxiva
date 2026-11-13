(() => {
  const num = (v) => (typeof v === "number" && Number.isFinite(v) ? v : null);
  const f1 = (v) => v.toFixed(1);

  function curve(points) {
    if (points.length < 2) return "";
    let d = `M${f1(points[0][0])} ${f1(points[0][1])}`;
    for (let i = 0; i < points.length - 1; i++) {
      const p0 = points[i - 1] || points[i], p1 = points[i], p2 = points[i + 1], p3 = points[i + 2] || p2;
      d += `C${f1(p1[0] + (p2[0] - p0[0]) / 6)} ${f1(p1[1] + (p2[1] - p0[1]) / 6)} ${f1(p2[0] - (p3[0] - p1[0]) / 6)} ${f1(p2[1] - (p3[1] - p1[1]) / 6)} ${f1(p2[0])} ${f1(p2[1])}`;
    }
    return d;
  }

  function render(rows, k, icon) {
    const items = rows.filter((r) => num(r.temp) !== null);
    if (items.length < 3) return "";
    const temps = items.map((r) => k.U.temp(r.temp)), lo = Math.min(...temps), hi = Math.max(...temps), span = Math.max(1, hi - lo);
    const level = (t) => (t - lo) / span;
    const pts = items.map((r, i) => [(i + 0.5) * 10, 24 + (1 - level(temps[i])) * 70]);
    const line = curve(pts), W = items.length * 10;
    const area = `${line}L${f1(pts[pts.length - 1][0])} 100L${f1(pts[0][0])} 100Z`;
    const every = items.length > 18 ? 2 : 1;
    const cols = items.map((r, i) => {
      const prob = Math.max(0, Math.min(100, num(r.rain_prob) ?? 0)), show = i % every === 0;
      return `<div class="wx-hcol${i === 0 ? " now" : ""}${show ? "" : " thin"}" style="--y:${level(temps[i]).toFixed(3)};--p:${prob / 100}">
        <span class="wx-ht">${i === 0 ? k.esc(k.t("wx_now")) : k.esc(k.hourLabel(r.time))}</span>
        <span class="wx-hi">${icon(r.icon, 26)}</span>
        <span class="wx-hv"><b>${Math.round(temps[i])}°</b></span>
        <span class="wx-hr"><i></i><small>${prob >= 10 ? `${Math.round(prob)}%` : ""}</small></span>
        <span class="wx-hw">${num(r.wind) !== null ? `${k.U.wind(r.wind)}` : ""}</span></div>`;
    }).join("");
    return `<div class="wx-hgrid" style="--n:${items.length}" role="img" aria-label="${k.esc(k.t("wx_hourly"))}">
      <svg class="wx-hcurve" viewBox="0 0 ${W} 100" preserveAspectRatio="none" aria-hidden="true">
        <defs><linearGradient id="wxh-fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="rgb(var(--wx-a))" stop-opacity=".28"/><stop offset="1" stop-color="rgb(var(--wx-a))" stop-opacity="0"/></linearGradient></defs>
        <path d="${area}" fill="url(#wxh-fill)"/><path d="${line}" class="wx-hline" vector-effect="non-scaling-stroke"/></svg>${cols}</div>
      <p class="wx-hfoot">${k.esc(k.t("wx_hourly_legend", { unit: k.U.windUnit }))}</p>`;
  }

  window.NuxivaWeatherHourly = Object.freeze({ render });
})();
