(() => {
  const crest = (t, ctx) => `<span class="hm-crest" style="--team:#${/^[0-9a-f]{6}$/i.test(t.color || "") ? t.color : "38bdf8"}">${ctx.esc((t.abbr || t.short || "?").slice(0, 3))}</span>`;
  const when = (iso, ctx) => {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "";
    const days = Math.round((new Date(d.toDateString()) - new Date(new Date().toDateString())) / 86400000);
    const loc = ctx.locale();
    const day = days === 0 ? ctx.t("today_cap") : days === 1 ? ctx.t("tomorrow") : d.toLocaleDateString(loc, { weekday: "short", day: "numeric", month: "short" });
    return `${day} · ${d.toLocaleTimeString(loc, { hour: "2-digit", minute: "2-digit" })}`;
  };
  const CHIP = { live: ["live", true], goal: ["goal", true], overtime: ["ot", true], faceoff: ["faceoff", true], soon: ["soon", false],
    final: ["final", false], result: ["final", false], today: ["today", false], next: ["next", false] };
  NuxivaDesk.register("hockey_match", {
    render(el, d, ctx) {
      const m = d.match || {}, h = m.home || {}, a = m.away || {};
      const [chipKey, live] = CHIP[d.kind] || (m.state === "in" ? CHIP.live : m.state === "post" ? CHIP.final : CHIP.next);
      const chip = chipKey === "live" ? ctx.tc("live") : ctx.t(`chip_${chipKey}`);
      const played = m.state !== "pre";
      const goals = (m.events || []).filter((e) => e.kind === "goal").slice(-5);
      const period = m.period || (m.state === "in" ? ctx.t("period_in_progress") : m.state === "post" ? ctx.t("chip_final") : when(m.start, ctx));
      el.innerHTML = `${ctx.head({ icon: "disc", label: m.league_name || ctx.t("hockey"), chip, live })}
        ${d.highlight ? `<div class="hm-flash">${ctx.esc(d.highlight)}</div>` : ""}
        <div class="hm-board">
          <div class="hm-team">${crest(h, ctx)}<span>${ctx.esc(h.short || h.name || "")}</span></div>
          <div class="hm-score"><div>${played ? `<b>${ctx.esc(h.score ?? 0)}</b><i>–</i><b>${ctx.esc(a.score ?? 0)}</b>` : `<i class="hm-vs">${ctx.esc(ctx.t("versus"))}</i>`}</div>
            <small>${ctx.esc(period)}</small></div>
          <div class="hm-team">${crest(a, ctx)}<span>${ctx.esc(a.short || a.name || "")}</span></div>
        </div>
        ${goals.length ? `<ul class="hm-goals">${goals.map((g) => `<li class="${g.side === "away" ? "r" : ""}"><i class="hm-puck"></i>${ctx.esc(g.player || "")} <span>${ctx.esc(g.minute || "")}${g.powerplay ? ` [PP]` : ""}</span></li>`).join("")}</ul>` : ""}
        ${m.venue && !played ? `<div class="wk-sub">${ctx.esc(m.venue)}</div>` : ""}`;
    },
  });
})();
