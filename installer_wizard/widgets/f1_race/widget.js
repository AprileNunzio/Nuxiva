(() => {
  const left = (iso, ctx) => {
    const s = Math.max(0, (new Date(iso).getTime() - Date.now()) / 1000);
    const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60);
    return d ? `${d}${ctx.t("unit_d")} ${h}${ctx.t("unit_h")}` : h ? `${h}${ctx.t("unit_h")} ${m}${ctx.t("unit_m")}` : `${m} ${ctx.t("unit_min")}`;
  };
  const at = (iso, ctx) => new Date(iso).toLocaleString(ctx.locale(), { weekday: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  const rows = (list, ctx) => `<ul class="wk-list f1-rows">${list.map((r) => `<li class="wk-row ic"><span class="f1-pos">${ctx.esc(r.pos)}</span>
    <span>${ctx.esc(r.name || r.team || "")}${r.name && r.team ? `<small> ${ctx.esc(r.team)}</small>` : ""}</span><span class="mono">${ctx.esc(r.time || r.points)}</span></li>`).join("")}</ul>`;
  NuxivaDesk.register("f1_race", {
    render(el, d, ctx) {
      const race = d.race || {}, label = ctx.t("label");
      if (d.mode === "standings") {
        el.innerHTML = `${ctx.head({ icon: "trend", label, title: ctx.t("drivers_title") })}${rows((d.drivers || []).slice(0, 6), ctx)}`;
        return;
      }
      if (d.mode === "results") {
        el.innerHTML = `${ctx.head({ icon: "star", label, title: race.name || "", chip: ctx.t("results") })}${rows((d.results || []).slice(0, 6), ctx)}`;
        return;
      }
      const s = d.session || {}, live = d.mode === "live";
      el.innerHTML = `${ctx.head({ icon: "car", label, title: race.name || "", chip: ctx.t(live ? "live_now" : "next"), live })}
        <div class="wk-hero"><span class="wk-num sm">${live ? ctx.esc(ctx.tc("live").toUpperCase()) : ctx.esc(left(s.start, ctx))}</span>
          <span class="wk-sub"><span>${ctx.esc(s.name || "")}</span><br><span>${ctx.esc(at(s.start, ctx))}</span></span></div>
        <dl class="wk-kv"><dt>${ctx.esc(ctx.t("circuit"))}</dt><dd>${ctx.esc(race.circuit || "")}</dd><dt>${ctx.esc(ctx.t("place"))}</dt><dd>${ctx.esc(race.place || "")}</dd><dt>${ctx.esc(ctx.t("round"))}</dt><dd class="mono">${ctx.esc(race.round || "")}</dd></dl>`;
    },
  });
})();
