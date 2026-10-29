(() => {
  const CHIP = { live: ["live", true], goal: ["goal", true], red: ["red", true], kickoff: ["kickoff", true], soon: ["soon", false],
    final: ["final", false], result: ["final", false], today: ["today", false], next: ["next", false] };
  const COLOR = /^[0-9a-f]{6}$/i;

  const team = (t, ctx) => {
    const o = t && typeof t === "object" ? t : {};
    const score = ctx.num(o.score);
    return { id: ctx.str(o.id, 40), name: ctx.pick(o, ["short", "name", "abbr"], 40), abbr: (ctx.pick(o, ["abbr", "short", "name"], 12) || "?").slice(0, 3).toUpperCase(),
      color: COLOR.test(ctx.str(o.color, 6)) ? ctx.str(o.color, 6) : "22c55e", score: score === null ? 0 : Math.max(0, Math.floor(score)) };
  };

  const light = (c) => 0.2126 * parseInt(c.slice(0, 2), 16) + 0.7152 * parseInt(c.slice(2, 4), 16) + 0.0722 * parseInt(c.slice(4, 6), 16) > 170;
  const crest = (t, ctx) => `<span class="sm-crest${light(t.color) ? " light" : ""}" style="--team:#${t.color}">${ctx.esc(t.abbr)}</span>`;

  const day = (start, ctx) => {
    const s = ctx.stamp(start);
    if (s === null) return "";
    const d = new Date(s * 1000);
    const days = Math.round((new Date(d.toDateString()) - new Date(new Date().toDateString())) / 86400000);
    const label = days === 0 ? ctx.t("today_cap") : days === 1 ? ctx.t("tomorrow") : ctx.when(s, { weekday: "short", day: "numeric", month: "short" });
    return `${label} · ${ctx.when(s)}`;
  };

  const minuteOf = (m, ctx) => {
    const txt = ctx.pick(m, ["clock", "detail"], 40);
    if (/\b(ht|half ?time|intervallo|descanso|mi-temps)\b/i.test(txt)) return { pct: 50, ht: true };
    const n = txt.match(/(\d{1,3})(?:\s*\+\s*(\d{1,2}))?\s*'/) || txt.match(/^(\d{1,3})(?::\d{2})?$/);
    return n ? { pct: Math.min(100, (Number(n[1]) / 90) * 100), ht: false } : null;
  };

  const impl = {
    render(el, raw, ctx) {
      const d = raw && typeof raw === "object" ? raw : {};
      const m = d.match && typeof d.match === "object" ? d.match : {};
      const h = team(m.home, ctx), a = team(m.away, ctx);
      const state = ["pre", "in", "post"].includes(m.state) ? m.state : "pre";
      const [chipKey, live] = CHIP[d.kind] || (state === "in" ? CHIP.live : state === "post" ? CHIP.final : CHIP.next);
      const chip = chipKey === "live" ? ctx.tc("live") : ctx.t(`chip_${chipKey}`);
      const league = ctx.str(m.league_name, 30) || ctx.t("football");
      if (!h.name && !a.name) { el.innerHTML = `${ctx.head({ icon: "star", label: league })}${ctx.empty(ctx.tc("waiting"))}`; return; }
      const mine = ctx.str(d.team && typeof d.team === "object" ? d.team.id : d.team, 40);
      const side = mine && mine === h.id ? "home" : mine && mine === a.id ? "away" : "";
      const played = state !== "pre";
      const status = state === "in" ? ctx.pick(m, ["clock", "detail"], 40) || ctx.t("in_progress") : state === "post" ? ctx.pick(m, ["detail"], 40) || ctx.t("chip_final") : day(m.start, ctx);
      const events = ctx.arr(m.events, 40).filter((e) => e && typeof e === "object" && (e.kind === "goal" || e.kind === "red")).slice(-8);
      const win = state === "post" && h.score !== a.score ? (h.score > a.score ? "home" : "away") : "";
      const outcome = state === "post" && side ? (win === side ? "won" : win ? "lost" : "drew") : "";
      const highlight = ctx.str(d.highlight, 200);
      const until = state === "pre" ? ctx.stamp(m.start) : null;
      const clock = state === "in" ? minuteOf(m, ctx) : null;
      const last = d.last && typeof d.last === "object" && state === "pre" ? d.last : null;
      const lh = last ? team(last.home, ctx) : null, la = last ? team(last.away, ctx) : null;
      const box = el.closest(".widget");
      if (box) { box.classList.toggle("sm-goal", d.kind === "goal"); box.classList.toggle("sm-red", d.kind === "red"); }
      const teamCell = (t, s) => `<div class="sm-team${win && win !== s ? " lost" : ""}${side === s ? " mine" : ""}">${crest(t, ctx)}<span>${ctx.esc(t.name)}</span></div>`;
      el.innerHTML = `${ctx.head({ icon: "star", label: league, chip, live, state: d.kind === "red" ? "bad" : outcome === "won" ? "ok" : "" })}
        ${highlight ? `<div class="sm-flash${d.kind === "red" ? " red" : ""}">${ctx.icon(d.kind === "red" ? "alert" : "sparkle")}<span>${ctx.esc(highlight)}</span></div>` : ""}
        <div class="sm-board">
          ${teamCell(h, "home")}
          <div class="sm-score"><div>${played ? `<b class="${win === "home" ? "win" : ""}">${h.score}</b><i>–</i><b class="${win === "away" ? "win" : ""}">${a.score}</b>` : `<i class="sm-vs">${ctx.esc(ctx.t("versus"))}</i>`}</div>
            <small>${ctx.esc(status)}</small>${until && until > ctx.now() ? `<small class="sm-until">${ctx.esc(ctx.ago(until))}</small>` : ""}
            ${outcome ? `<em class="sm-out ${outcome}">${ctx.esc(ctx.t(`out_${outcome}`))}</em>` : ""}</div>
          ${teamCell(a, "away")}
        </div>
        ${clock ? `<div class="sm-clock${clock.ht ? " ht" : ""}"><i style="width:${clock.pct}%"></i><b></b></div>` : ""}
        ${events.length ? `<ul class="sm-goals">${events.map((g) => {
          const s = g.side === "away" ? "away" : "home";
          const tag = [g.penalty ? ctx.t("penalty") : "", g.own_goal ? ctx.t("own_goal") : ""].filter(Boolean).join(" ");
          return `<li class="${s === "away" ? "r" : ""}${g.kind === "red" ? " card" : ""}"><i class="${g.kind === "red" ? "sm-card" : "sm-ball"}"></i><b>${ctx.esc(ctx.str(g.player, 40) || (s === "away" ? a.abbr : h.abbr))}</b> <span>${ctx.esc(ctx.str(g.minute, 10))}${tag ? ` ${ctx.esc(tag)}` : ""}</span></li>`;
        }).join("")}</ul>` : ""}
        ${!played && ctx.str(m.venue, 80) ? `<div class="wk-sub sm-venue">${ctx.icon("pin")} ${ctx.esc(ctx.str(m.venue, 80))}</div>` : ""}
        ${lh && la && (lh.name || la.name) ? `<div class="sm-last"><small>${ctx.esc(ctx.t("last"))}</small><span>${ctx.esc(lh.abbr)} <b class="mono">${lh.score}–${la.score}</b> ${ctx.esc(la.abbr)}</span></div>` : ""}`;
    },
    destroy(el) { el.closest(".widget")?.classList.remove("sm-goal", "sm-red"); },
  };
  NuxivaDesk.register("sport_match", impl);
})();
