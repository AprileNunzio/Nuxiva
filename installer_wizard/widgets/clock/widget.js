(() => {
  const timers = new WeakMap();
  const week = (d) => {
    const t = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
    t.setUTCDate(t.getUTCDate() + 4 - (t.getUTCDay() || 7));
    return Math.ceil(((t - Date.UTC(t.getUTCFullYear(), 0, 1)) / 864e5 + 1) / 7);
  };
  function tick(el, ctx) {
    const now = new Date(), loc = ctx.locale();
    const hm = el.querySelector(".ck-hm");
    if (!hm) return;
    hm.textContent = now.toLocaleTimeString(loc, { hour: "2-digit", minute: "2-digit" });
    el.querySelector(".ck-s").textContent = String(now.getSeconds()).padStart(2, "0");
    el.querySelector(".ck-day").textContent = now.toLocaleDateString(loc, { weekday: "long", day: "numeric", month: "long", year: "numeric" });
    el.querySelector(".ck-week").textContent = String(week(now));
    el.querySelector(".ck-bar > i").style.width = `${((now.getHours() * 60 + now.getMinutes()) / 1440) * 100}%`;
  }
  NuxivaDesk.register("clock", {
    render(el, d, ctx) {
      el.innerHTML = `${ctx.head({ icon: "clock", label: ctx.t("label") })}
        <div class="wk-hero"><span class="wk-num ck-hm"></span><span class="wk-num sm wk-faint ck-s"></span></div>
        <div class="wk-sub ck-day"></div>
        <div class="wk-sub"><span>${ctx.esc(ctx.t("week"))}</span> <span class="wk-mono ck-week"></span></div>
        <span class="wk-bar ck-bar"><i></i></span>`;
      tick(el, ctx);
      clearInterval(timers.get(el));
      timers.set(el, setInterval(() => tick(el, ctx), 1000));
    },
    update(el, d, ctx) { tick(el, ctx); },
    destroy(el) { clearInterval(timers.get(el)); },
  });
})();
