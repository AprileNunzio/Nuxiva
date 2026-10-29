(() => {
  const MODE = [[/piedi|walk|foot|pie|pied/i, "user"], [/bici|bike|cycl|vélo|velo/i, "wind"], [/mezzi|transit|bus|treno|train|metro|tram|transporte|transports/i, "map"], [/moto/i, "car"]];
  const CLOCK = /^([01]?\d|2[0-3])[:.]([0-5]\d)$/;
  const BASIS = { storico: "b_history", history: "b_history", prudenza: "b_caution", caution: "b_caution", fisso: "b_fixed", fixed: "b_fixed" };

  const at = (v, ctx) => {
    const s = ctx.str(v, 30);
    const m = s.match(CLOCK);
    if (!m) return ctx.stamp(v);
    const d = new Date();
    d.setHours(+m[1], +m[2], 0, 0);
    if (d.getTime() < Date.now() - 12 * 3600e3) d.setDate(d.getDate() + 1);
    return d.getTime() / 1000;
  };

  const sketch = (raw, a, b) => {
    const pts = (Array.isArray(raw) ? raw : []).slice(0, 600).map((p) => Array.isArray(p) ? [Number(p[0]), Number(p[1])] : p && typeof p === "object" ? [Number(p.lat), Number(p.lon ?? p.lng)] : null)
      .filter((p) => p && Number.isFinite(p[0]) && Number.isFinite(p[1]) && Math.abs(p[0]) <= 90 && Math.abs(p[1]) <= 180);
    if (pts.length < 2) for (const p of [a, b]) if (Array.isArray(p) && Number.isFinite(+p[0]) && Number.isFinite(+p[1])) pts.push([+p[0], +p[1]]);
    if (pts.length < 2) return "";
    const k = Math.cos((pts[0][0] * Math.PI) / 180);
    const xy = pts.map(([la, lo]) => [lo * k, -la]);
    const xs = xy.map((p) => p[0]), ys = xy.map((p) => p[1]);
    const x0 = Math.min(...xs), y0 = Math.min(...ys), w = Math.max(...xs) - x0 || 1e-6, h = Math.max(...ys) - y0 || 1e-6;
    const s = Math.min(200 / w, 80 / h), ox = (220 - w * s) / 2, oy = (100 - h * s) / 2;
    const P = xy.map(([x, y]) => [ox + (x - x0) * s, oy + (y - y0) * s].map((n) => n.toFixed(1)).join(","));
    const [sx, sy] = P[0].split(","), [ex, ey] = P[P.length - 1].split(",");
    return `<svg class="rt-map" viewBox="0 0 220 100" aria-hidden="true"><polyline class="halo" points="${P.join(" ")}"/><polyline points="${P.join(" ")}"/><circle class="a" cx="${sx}" cy="${sy}" r="4"/><circle class="b" cx="${ex}" cy="${ey}" r="5"/></svg>`;
  };

  const impl = {
    render(el, raw, ctx) {
      clearInterval(el._rtTick);
      const d = raw && typeof raw === "object" ? raw : {};
      const mode = ctx.str(d.mode, 30);
      const icon = (MODE.find(([re]) => re.test(mode)) || [null, "car"])[1];
      const minutes = ctx.num(d.minutes);
      const delay = ctx.num(d.delay ?? d.delay_minutes);
      const late = delay !== null && delay >= 3;
      const steps = ctx.arr(d.steps, 20).map((s) => ctx.str(typeof s === "string" ? s : s?.text, 160)).filter(Boolean);
      const advice = d.advice && typeof d.advice === "object" ? d.advice : null;
      const leave = d.leave_by ? at(d.leave_by, ctx) : null;
      const arrive = ctx.str(d.arrive_at, 20);
      const ui = el._rt || (el._rt = { open: false });
      const map = sketch(d.path, d.a, d.b);
      if (!d.to && !d.duration && minutes === null) { el.innerHTML = `${ctx.head({ icon, label: mode || ctx.t("trip") })}${ctx.empty(ctx.tc("waiting"))}`; el.onclick = null; return; }
      const paint = () => {
        const left = leave === null ? null : leave - Date.now() / 1000;
        const urgency = left === null ? "" : left < 0 ? "bad" : left <= 600 ? "warn" : "";
        const chip = late ? ctx.t("delay", { n: Math.round(delay) }) : d.traffic ? ctx.t("clear") : "";
        el.innerHTML = `${ctx.head({ icon, label: mode || ctx.t("trip"), title: ctx.str(d.title, 80), chip, state: late ? "warn" : d.traffic ? "ok" : "", live: !!d.traffic })}
          <div class="rt-top">
            <div class="rt-hero"><span class="wk-num sm">${ctx.esc(ctx.str(d.duration, 20) || (minutes !== null ? `${Math.round(minutes)} min` : "—"))}</span>
              <span class="rt-path"><span class="rt-from">${ctx.esc(ctx.str(d.from, 60))}</span><span class="rt-arrow">${ctx.icon(icon)}</span><b>${ctx.esc(ctx.str(d.to, 80))}</b></span>
              ${d.to_detail ? `<span class="wk-faint rt-detail">${ctx.esc(ctx.str(d.to_detail, 90))}</span>` : ""}
              <span class="rt-tags">${[d.distance ? `<span class="wk-chip">${ctx.esc(ctx.str(d.distance, 20))}</span>` : "", d.via ? `<span class="wk-chip">${ctx.esc(ctx.t("via", { v: ctx.str(d.via, 50) }))}</span>` : "", d.tolls ? `<span class="wk-chip warn">${ctx.icon("coin")}${ctx.esc(ctx.t("tolls"))}</span>` : ""].join("")}</span></div>
            ${map}</div>
          ${late && minutes ? `<div class="rt-traffic"><span>${ctx.esc(ctx.t("traffic_share", { n: Math.round(delay) }))}</span>${ctx.bar((delay / minutes) * 100, delay / minutes > 0.3 ? "bad" : "warn")}</div>` : ""}
          ${leave !== null ? `<div class="rt-leave ${urgency}"><span class="rt-leave-ic">${ctx.icon(urgency === "bad" ? "alert" : "clock")}</span>
            <span class="rt-leave-txt"><small>${ctx.esc(ctx.t("leave_by"))}</small><b class="mono">${ctx.esc(ctx.when(leave))}</b></span>
            <span class="rt-leave-left">${ctx.esc(left < 0 ? ctx.t("leave_now") : ctx.ago(leave))}</span></div>` : ""}
          <dl class="wk-kv rt-kv"><dt>${ctx.esc(ctx.t(leave !== null ? "appointment" : "arrival"))}</dt><dd class="mono">${ctx.esc(arrive || "—")}</dd>
            ${advice && ctx.num(advice.margin) ? `<dt>${ctx.esc(ctx.t("margin"))}</dt><dd>${ctx.esc(ctx.t("margin_v", { n: Math.round(ctx.num(advice.margin)) }))}${BASIS[ctx.str(advice.basis, 20)] ? ` · <span class="wk-faint">${ctx.esc(ctx.t(BASIS[ctx.str(advice.basis, 20)], { n: Math.max(0, Math.floor(ctx.num(advice.samples) || 0)) }))}</span>` : ""}</dd>` : ""}</dl>
          ${steps.length ? `<button type="button" class="rt-toggle" aria-expanded="${ui.open}">${ctx.icon("list")}<span>${ctx.esc(ctx.t(ui.open ? "hide_steps" : "show_steps", { n: steps.length }))}</span></button>
            ${ui.open ? `<ol class="rt-steps">${steps.map((s) => `<li>${ctx.esc(s)}</li>`).join("")}</ol>` : ""}` : ""}`;
        return left;
      };
      el.onclick = (e) => { if (e.target.closest(".rt-toggle")) { ui.open = !ui.open; paint(); } };
      const left = paint();
      if (left !== null && left > -3600) el._rtTick = setInterval(() => { if (!el.isConnected) clearInterval(el._rtTick); else paint(); }, 20000);
    },
    destroy(el) { clearInterval(el._rtTick); el.onclick = null; },
  };
  NuxivaDesk.register("route", impl);
})();
