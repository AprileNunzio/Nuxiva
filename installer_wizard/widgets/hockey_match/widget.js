(() => {
  const CHIP = { live: ["live", true], goal: ["goal", true], overtime: ["ot", true], faceoff: ["faceoff", true], soon: ["soon", false],
    final: ["final", false], result: ["final", false], today: ["today", false], next: ["next", false] };
  const COLOR = /^[0-9a-f]{6}$/i;

  const team = (t, ctx) => {
    const o = t && typeof t === "object" ? t : {};
    const score = ctx.num(o.score);
    return { name: ctx.pick(o, ["short", "name", "abbr"], 40), abbr: (ctx.pick(o, ["abbr", "short", "name"], 12) || "?").slice(0, 3).toUpperCase(),
      color: COLOR.test(ctx.str(o.color, 6)) ? ctx.str(o.color, 6) : "38bdf8", score: score === null ? 0 : Math.max(0, Math.floor(score)),
      shots: ctx.num(o.shots ?? o.sog), record: ctx.str(o.record, 16) };
  };

  const crest = (t, ctx) => `<span class="hm-crest" style="--team:#${t.color}">${ctx.esc(t.abbr)}</span>`;

  function day(start, ctx) {
    const s = ctx.stamp(start);
    if (s === null) return "";
    const d = new Date(s * 1000);
    const days = Math.round((new Date(d.toDateString()) - new Date(new Date().toDateString())) / 86400000);
    const label = days === 0 ? ctx.t("today_cap") : days === 1 ? ctx.t("tomorrow") : ctx.when(s, { weekday: "short", day: "numeric", month: "short" });
    return `${label} · ${ctx.when(s)}`;
  }

  function periodOf(m, ctx) {
    const p = ctx.num(m.period);
    if (p !== null) return Math.max(0, Math.floor(p));
    const txt = ctx.pick(m, ["detail", "clock"], 40).toLowerCase();
    if (/\b(ot|overtime|so|shootout)\b/.test(txt)) return 4;
    const n = txt.match(/\b([1-3])(?:st|nd|rd|°|º|e|er)?\b/);
    return n ? Number(n[1]) : 0;
  }

  const tags = (g, ctx) => {
    const s = ctx.str(g.strength, 6).toUpperCase();
    return [g.powerplay === true || s === "PP" ? "PP" : "", g.shorthanded === true || s === "SH" ? "SH" : "", g.empty_net === true || s === "EN" ? "EN" : ""].filter(Boolean);
  };

  NuxivaDesk.register("hockey_match", {
    render(el, d, ctx) {
      const data = d && typeof d === "object" ? d : {};
      const m = data.match && typeof data.match === "object" ? data.match : {};
      const h = team(m.home, ctx), a = team(m.away, ctx);
      const state = ["pre", "in", "post"].includes(m.state) ? m.state : "pre";
      const [chipKey, live] = CHIP[data.kind] || (state === "in" ? CHIP.live : state === "post" ? CHIP.final : CHIP.next);
      const chip = chipKey === "live" ? ctx.tc("live") : ctx.t(`chip_${chipKey}`);
      if (!h.name && !a.name) { el.innerHTML = `${ctx.head({ icon: "timer", label: ctx.str(m.league_name, 30) || ctx.t("hockey") })}${ctx.empty(ctx.tc("waiting"))}`; return; }
      const played = state !== "pre";
      const per = periodOf(m, ctx);
      const status = state === "in" ? ctx.pick(m, ["detail", "clock"], 40) || ctx.t("period_in_progress") : state === "post" ? ctx.pick(m, ["detail"], 40) || ctx.t("chip_final") : day(m.start, ctx);
      const goals = ctx.arr(m.events, 40).filter((e) => e && typeof e === "object" && e.kind === "goal").slice(-6);
      const win = state === "post" && h.score !== a.score ? (h.score > a.score ? "home" : "away") : "";
      const shots = h.shots !== null && a.shots !== null && h.shots + a.shots > 0 ? [h.shots, a.shots] : null;
      const highlight = ctx.str(data.highlight, 200);
      const until = state === "pre" ? ctx.stamp(m.start) : null;
      const segs = played ? [1, 2, 3, ...(per >= 4 ? [4] : [])].map((p) => `<i class="${state === "post" || p < per ? "done" : p === per ? "now" : ""}" title="${ctx.esc(p === 4 ? ctx.t("chip_ot") : ctx.t("period_n", { n: p }))}">${p === 4 ? "OT" : p}</i>`).join("") : "";
      el.innerHTML = `${ctx.head({ icon: "timer", label: ctx.str(m.league_name, 30) || ctx.t("hockey"), chip, live })}
        ${highlight ? `<div class="hm-flash">${ctx.esc(highlight)}</div>` : ""}
        <div class="hm-board">
          <div class="hm-team${win === "away" ? " lost" : ""}">${crest(h, ctx)}<span>${ctx.esc(h.name)}</span>${h.record ? `<small>${ctx.esc(h.record)}</small>` : ""}</div>
          <div class="hm-score"><div>${played ? `<b class="${win === "home" ? "win" : ""}">${h.score}</b><i>–</i><b class="${win === "away" ? "win" : ""}">${a.score}</b>` : `<i class="hm-vs">${ctx.esc(ctx.t("versus"))}</i>`}</div>
            <small>${ctx.esc(status)}</small>${until && until > ctx.now() ? `<small class="hm-until">${ctx.esc(ctx.ago(until))}</small>` : ""}</div>
          <div class="hm-team${win === "home" ? " lost" : ""}">${crest(a, ctx)}<span>${ctx.esc(a.name)}</span>${a.record ? `<small>${ctx.esc(a.record)}</small>` : ""}</div>
        </div>
        ${segs ? `<div class="hm-periods" aria-label="${ctx.esc(ctx.t("periods"))}">${segs}</div>` : ""}
        ${shots ? `<div class="hm-sog"><b class="mono">${ctx.esc(ctx.fmt(shots[0]))}</b><span class="hm-sogbar"><i style="width:${(shots[0] / (shots[0] + shots[1])) * 100}%"></i></span><b class="mono">${ctx.esc(ctx.fmt(shots[1]))}</b><small>${ctx.esc(ctx.t("shots"))}</small></div>` : ""}
        ${goals.length ? `<ul class="hm-goals">${goals.map((g) => {
          const side = g.side === "away" ? "away" : "home";
          const tg = tags(g, ctx);
          return `<li class="${side === "away" ? "r" : ""}"><i class="hm-puck"></i><b>${ctx.esc(ctx.str(g.player, 40) || (side === "away" ? a.abbr : h.abbr))}</b> <span>${ctx.esc(ctx.str(g.minute, 10))}</span>${tg.map((x) => `<em title="${ctx.esc(ctx.t(`tag_${x.toLowerCase()}`))}">${x}</em>`).join("")}</li>`;
        }).join("")}</ul>` : ""}
        ${!played && ctx.str(m.venue, 80) ? `<div class="wk-sub hm-venue">${ctx.icon("pin")} ${ctx.esc(ctx.str(m.venue, 80))}</div>` : ""}`;
    },
  });
})();
