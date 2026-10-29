(() => {
  const SESSION = { "Prove libere 1": "fp1", "Prove libere 2": "fp2", "Prove libere 3": "fp3", "Qualifiche sprint": "sq", "Sprint": "sprint", "Qualifiche": "quali", "Gara": "race" };
  const iso = (s) => { const t = typeof s === "string" ? Date.parse(s) : NaN; return Number.isFinite(t) ? t : null; };
  const sessionName = (name, ctx) => (SESSION[name] ? ctx.t(`s_${SESSION[name]}`) : ctx.str(name, 40));

  function left(ms, ctx) {
    const s = Math.max(0, Math.floor(ms / 1000));
    const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
    if (d) return `${d}${ctx.t("unit_d")} ${h}${ctx.t("unit_h")}`;
    if (h) return `${h}${ctx.t("unit_h")} ${String(m).padStart(2, "0")}${ctx.t("unit_m")}`;
    return `${m}:${String(sec).padStart(2, "0")}`;
  }

  function stop(el) { clearInterval(el._f1T); el._f1T = 0; }

  const rowsOf = (list, ctx, kind) => {
    const top = Math.max(...list.map((r) => ctx.num(r.points) || 0), 1);
    return `<ol class="f1-rows">${list.map((r) => {
      const pos = Math.floor(ctx.num(r.pos) || 0);
      const name = kind === "teams" ? ctx.str(r.team, 40) : ctx.str(r.name, 60) || ctx.str(r.code, 3);
      const team = kind === "teams" ? "" : ctx.str(r.team, 40);
      const pts = ctx.num(r.points);
      const right = kind === "results" ? ctx.str(r.time, 20) || (pts !== null ? `${ctx.fmt(pts)} pt` : "") : pts !== null ? ctx.fmt(pts) : "";
      return `<li class="f1-row p${pos <= 3 ? pos : "x"}"><span class="f1-pos">${pos || "–"}</span>
        <span class="f1-who"><b>${ctx.esc(name)}</b>${team ? `<small>${ctx.esc(team)}</small>` : ""}${kind !== "results" && pts !== null ? ctx.bar((pts / top) * 100) : ""}</span>
        <span class="f1-val mono">${ctx.esc(right)}</span></li>`;
    }).join("")}</ol>`;
  };

  const impl = {
    render(el, d, ctx) {
      stop(el);
      const data = d && typeof d === "object" ? d : {};
      const race = data.race && typeof data.race === "object" ? data.race : {};
      const label = ctx.t("label");
      const raceName = ctx.str(race.name, 60);
      if (data.mode === "standings") {
        const drivers = ctx.arr(data.drivers, 10).filter((r) => r && typeof r === "object");
        const teams = ctx.arr(data.teams, 10).filter((r) => r && typeof r === "object");
        if (!drivers.length && !teams.length) { el.innerHTML = `${ctx.head({ icon: "trend", label, title: ctx.t("drivers_title") })}${ctx.empty(ctx.tc("waiting"))}`; return; }
        const view = el._f1View === "teams" && teams.length ? "teams" : "drivers";
        el.innerHTML = `${ctx.head({ icon: "trend", label, title: ctx.t(view === "teams" ? "teams_title" : "drivers_title") })}
          ${teams.length ? `<div class="f1-tabs" role="tablist"><button type="button" class="wk-btn${view === "drivers" ? " primary" : ""}" data-v="drivers" role="tab" aria-selected="${view === "drivers"}">${ctx.esc(ctx.t("drivers_title"))}</button><button type="button" class="wk-btn${view === "teams" ? " primary" : ""}" data-v="teams" role="tab" aria-selected="${view === "teams"}">${ctx.esc(ctx.t("teams_title"))}</button></div>` : ""}
          ${rowsOf((view === "teams" ? teams : drivers).slice(0, 8), ctx, view)}`;
        el.querySelectorAll(".f1-tabs [data-v]").forEach((b) => b.addEventListener("click", (e) => { e.stopPropagation(); el._f1View = b.dataset.v; impl.render(el, d, ctx); }));
        return;
      }
      if (data.mode === "results") {
        const results = ctx.arr(data.results, 10).filter((r) => r && typeof r === "object");
        if (!results.length) { el.innerHTML = `${ctx.head({ icon: "star", label, title: raceName, chip: ctx.t("results") })}${ctx.empty(ctx.tc("waiting"))}`; return; }
        const podium = results.slice(0, 3);
        el.innerHTML = `${ctx.head({ icon: "star", label, title: raceName, chip: ctx.t("results") })}
          ${podium.length === 3 ? `<div class="f1-podium">${[1, 0, 2].map((i) => `<div class="f1-step s${i + 1}"><b>${ctx.esc(ctx.str(podium[i].code, 3) || ctx.str(podium[i].name, 20))}</b><small>${ctx.esc(ctx.str(podium[i].team, 30))}</small><span>${i + 1}</span></div>`).join("")}</div>` : ""}
          ${rowsOf(podium.length === 3 ? results.slice(3, 8) : results.slice(0, 8), ctx, "results")}`;
        return;
      }
      const live = data.mode === "live";
      const s = data.session && typeof data.session === "object" ? data.session : null;
      const start = s ? iso(s.start) : null;
      const sessions = ctx.arr(race.sessions, 8).filter((x) => x && typeof x === "object" && iso(x.start) !== null);
      const now = Date.now();
      const timeline = sessions.map((x) => {
        const t = iso(x.start);
        const cls = s && x.start === s.start ? (live ? "live" : "next") : t < now ? "past" : "";
        return `<li class="${cls}"><b>${ctx.esc(sessionName(x.name, ctx))}</b><span>${ctx.esc(ctx.when(t / 1000, { weekday: "short", hour: "2-digit", minute: "2-digit" }))}</span></li>`;
      }).join("");
      if (!raceName && !start && !sessions.length) { el.innerHTML = `${ctx.head({ icon: "car", label, chip: ctx.t(live ? "live_now" : "next"), live })}${ctx.empty(ctx.tc("waiting"))}`; return; }
      el.innerHTML = `${ctx.head({ icon: "car", label, title: raceName, chip: ctx.t(live ? "live_now" : "next"), live })}
        <div class="wk-hero f1-hero"><span class="wk-num sm f1-count">${live ? ctx.esc(ctx.tc("live").toUpperCase()) : start ? ctx.esc(left(start - now, ctx)) : "—"}</span>
          <span class="wk-sub"><span>${ctx.esc(s ? sessionName(s.name, ctx) : "")}</span><br><span>${start ? ctx.esc(ctx.when(start / 1000, { weekday: "long", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })) : ""}</span></span></div>
        <dl class="wk-kv f1-kv">${race.circuit ? `<dt>${ctx.esc(ctx.t("circuit"))}</dt><dd>${ctx.esc(ctx.str(race.circuit, 80))}</dd>` : ""}${race.place ? `<dt>${ctx.esc(ctx.t("place"))}</dt><dd>${ctx.esc(ctx.str(race.place, 80))}</dd>` : ""}${race.round ? `<dt>${ctx.esc(ctx.t("round"))}</dt><dd class="mono">${ctx.esc(String(Math.floor(ctx.num(race.round) || 0)))}</dd>` : ""}</dl>
        ${timeline ? `<ol class="f1-weekend">${timeline}</ol>` : ""}`;
      if (!live && start && start > now) {
        const out = el.querySelector(".f1-count");
        el._f1T = setInterval(() => {
          if (!out.isConnected) { stop(el); return; }
          out.textContent = left(start - Date.now(), ctx);
        }, start - Date.now() < 86400000 ? 1000 : 30000);
      }
    },
    destroy(el) { stop(el); },
  };

  NuxivaDesk.register("f1_race", impl);
})();
