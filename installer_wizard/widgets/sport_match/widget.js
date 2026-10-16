(() => {
  const crest = (t, ctx) => `<span class="sm-crest" style="--team:#${/^[0-9a-f]{6}$/i.test(t.color || "") ? t.color : "29e0ff"}">${ctx.esc((t.abbr || t.short || "?").slice(0, 3))}</span>`;
  const when = (iso, ctx) => {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "";
    const days = Math.round((new Date(d.toDateString()) - new Date(new Date().toDateString())) / 86400000);
    const loc = ctx.locale();
    const day = days === 0 ? ctx.t("today_cap") : days === 1 ? ctx.t("tomorrow") : d.toLocaleDateString(loc, { weekday: "short", day: "numeric", month: "short" });
    return `${day} · ${d.toLocaleTimeString(loc, { hour: "2-digit", minute: "2-digit" })}`;
  };
  const CHIP = { live: ["live", true], goal: ["goal", true], red: ["red", true], kickoff: ["kickoff", true], soon: ["soon", false],
    final: ["final", false], result: ["final", false], today: ["today", false], next: ["next", false] };
  NuxivaDesk.register("sport_match", {
    render(el, d, ctx) {
      const m = d.match || {}, h = m.home || {}, a = m.away || {};
      const [chipKey, live] = CHIP[d.kind] || (m.state === "in" ? CHIP.live : m.state === "post" ? CHIP.final : CHIP.next);
      const chip = chipKey === "live" ? ctx.tc("live") : ctx.t(`chip_${chipKey}`);
      const played = m.state !== "pre";
      const goals = (m.events || []).filter((e) => e.kind === "goal").slice(-6);
      const status = m.state === "in" ? (m.clock || ctx.t("in_progress")) : m.state === "post" ? ctx.t("chip_final") : when(m.start, ctx);
      el.innerHTML = `${ctx.head({ icon: "star", label: m.league_name || ctx.t("football"), chip, live })}
        ${d.highlight ? `<div class="sm-flash">${ctx.esc(d.highlight)}</div>` : ""}
        <div class="sm-board">
          <div class="sm-team">${crest(h, ctx)}<span>${ctx.esc(h.short || h.name || "")}</span></div>
          <div class="sm-score"><div>${played ? `<b>${ctx.esc(h.score ?? 0)}</b><i>–</i><b>${ctx.esc(a.score ?? 0)}</b>` : `<i class="sm-vs">${ctx.esc(ctx.t("versus"))}</i>`}</div>
            <small>${ctx.esc(status)}</small></div>
          <div class="sm-team">${crest(a, ctx)}<span>${ctx.esc(a.short || a.name || "")}</span></div>
        </div>
        ${goals.length ? `<ul class="sm-goals">${goals.map((g) => `<li class="${g.side === "away" ? "r" : ""}"><i class="sm-ball"></i>${ctx.esc(g.player || "")} <span>${ctx.esc(g.minute || "")}${g.penalty ? ` ${ctx.esc(ctx.t("penalty"))}` : ""}${g.own_goal ? ` ${ctx.esc(ctx.t("own_goal"))}` : ""}</span></li>`).join("")}</ul>` : ""}
        ${m.venue && !played ? `<div class="wk-sub">${ctx.esc(m.venue)}</div>` : ""}`;
    },
  });
})();
