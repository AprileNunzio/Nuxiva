(() => {
  const CLOCK = /(?:^|[^\d])([01]?\d|2[0-3])[:.]([0-5]\d)(?!\d)/;
  const TOMORROW = /\b(domani|tomorrow|mañana|demain)\b/i;
  const REPEAT = { daily: "rep_daily", day: "rep_daily", giornaliero: "rep_daily", weekly: "rep_weekly", week: "rep_weekly", settimanale: "rep_weekly", monthly: "rep_monthly", month: "rep_monthly", mensile: "rep_monthly", yearly: "rep_yearly", year: "rep_yearly", annuale: "rep_yearly" };

  const due = (o, text, ctx) => {
    const s = ctx.stamp(o.at ?? o.when ?? o.due ?? o.time ?? o.date ?? o.ts);
    if (s !== null) return s;
    const raw = ctx.str(o.at ?? o.when ?? o.time, 40) || text;
    const m = raw.match(CLOCK);
    if (!m) return null;
    const d = new Date();
    d.setHours(+m[1], +m[2], 0, 0);
    if (TOMORROW.test(raw) || TOMORROW.test(text)) d.setDate(d.getDate() + 1);
    else if (d.getTime() < Date.now() - 6 * 3600e3) d.setDate(d.getDate() + 1);
    return d.getTime() / 1000;
  };

  const item = (o, ctx) => {
    const src = typeof o === "string" ? { text: o } : o && typeof o === "object" ? o : {};
    const text = ctx.pick(src, ["text", "content", "title", "message", "what"], 240);
    return { text, at: due(src, text, ctx), repeat: REPEAT[ctx.str(src.repeat ?? src.recurrence, 20).toLowerCase()] || "", where: ctx.pick(src, ["where", "place", "location"], 80) };
  };

  const impl = {
    render(el, raw, ctx) {
      clearInterval(el._rmTick);
      const d = raw && typeof raw === "object" ? raw : {};
      const main = item(d, ctx);
      const more = ctx.arr(d.items ?? d.reminders, 12).map((o) => item(o, ctx)).filter((r) => r.text);
      if (!main.text && more.length) Object.assign(main, more.shift());
      const paint = () => {
        const now = Date.now() / 1000;
        const left = main.at === null ? null : main.at - now;
        const late = left !== null && left < 0;
        const soon = left !== null && !late && left <= 900;
        const state = late ? "bad" : soon ? "warn" : "";
        const chip = left === null ? ctx.t("pending") : late ? ctx.t("overdue") : soon ? ctx.t("soon") : ctx.t("pending");
        const ring = left !== null && !late && left <= 3600;
        el.closest(".widget")?.classList.toggle("rm-due", late || soon);
        el.innerHTML = `${ctx.head({ icon: "bell", label: ctx.t("label"), chip, live: !late, state })}
          <div class="rm-hero${late ? " late" : soon ? " soon" : ""}">
            ${ring ? ctx.ring(100 - (left / 3600) * 100, ctx.mmss(left), ctx.t("min")) : `<span class="rm-ic">${ctx.icon(late ? "alert" : "clock")}</span>`}
            <div class="rm-main"><span class="wk-title rm-text">${ctx.esc(main.text || ctx.t("new"))}</span>
              ${main.at !== null ? `<span class="rm-when">${ctx.icon("calendar")}<b class="mono">${ctx.esc(ctx.when(main.at, Math.abs(main.at - now) > 72000 ? { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" } : { hour: "2-digit", minute: "2-digit" }))}</b><span>${ctx.esc(ctx.ago(main.at))}</span></span>` : ""}
              ${main.repeat || main.where ? `<span class="rm-tags">${main.repeat ? `<span class="wk-chip">${ctx.icon("refresh")}${ctx.esc(ctx.t(main.repeat))}</span>` : ""}${main.where ? `<span class="wk-chip">${ctx.icon("pin")}${ctx.esc(main.where)}</span>` : ""}</span>` : ""}</div></div>
          ${more.length ? `<ul class="rm-next">${more.slice(0, 5).map((r) => `<li><span class="mono">${r.at !== null ? ctx.esc(ctx.when(r.at)) : "·"}</span><span>${ctx.esc(r.text)}</span></li>`).join("")}</ul>` : ""}`;
        return left;
      };
      const fast = (l) => l > -60 && l <= 3600;
      const loop = () => {
        const left = paint();
        clearInterval(el._rmTick);
        if (left === null) return;
        el._rmTick = setInterval(() => { if (!el.isConnected) { clearInterval(el._rmTick); return; } if (fast(paint()) !== fast(left)) loop(); }, fast(left) ? 1000 : 30000);
      };
      loop();
    },
    destroy(el) { clearInterval(el._rmTick); el.closest(".widget")?.classList.remove("rm-due"); },
  };
  NuxivaDesk.register("reminder", impl);
})();
