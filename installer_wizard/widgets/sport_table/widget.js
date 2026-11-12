(() => {
  const COLOR = /^[0-9a-f]{6}$/i;

  const row = (r, ctx) => {
    const o = r && typeof r === "object" ? r : {};
    const n = (k) => { const v = ctx.num(o[k]); return v === null ? null : Math.trunc(v); };
    return { id: ctx.str(o.id, 40), name: ctx.pick(o, ["short", "name", "abbr"], 40), group: ctx.str(o.group, 40), color: COLOR.test(ctx.str(o.color, 6)) ? `#${ctx.str(o.color, 6)}` : "",
      rank: n("rank"), played: n("played"), points: n("points"), won: n("won"), drawn: n("drawn"), lost: n("lost"), diff: n("diff") };
  };

  const zones = (d, count, ctx) => {
    const z = d.zones && typeof d.zones === "object" ? d.zones : null;
    if (z) return { top: Math.max(0, Math.floor(ctx.num(z.top ?? z.promotion ?? z.champions) || 0)), bottom: Math.max(0, Math.floor(ctx.num(z.bottom ?? z.relegation) || 0)) };
    return /\.1$/.test(ctx.str(d.league, 20)) && count >= 16 ? { top: 4, bottom: 3 } : { top: 0, bottom: 0 };
  };

  const impl = {
    render(el, raw, ctx) {
      const d = raw && typeof raw === "object" ? raw : {};
      const all = ctx.arr(d.rows, 80).map((r) => row(r, ctx)).filter((r) => r.name);
      const mark = new Set(ctx.arr(d.highlight, 20).map((x) => ctx.str(x, 40)).filter(Boolean));
      const head = (chip) => ctx.head({ icon: "list", label: ctx.t("label"), title: ctx.str(d.league_name, 50), chip });
      if (!all.length) { el.innerHTML = `${head("")}${ctx.empty(ctx.tc("waiting"))}`; return; }
      const groups = [...new Set(all.map((r) => r.group))];
      const ui = el._st && el._st.key === groups.join("|") ? el._st : (el._st = { key: groups.join("|"), group: "", open: false });
      const pref = all.find((r) => mark.has(r.id))?.group ?? groups[0];
      const group = groups.includes(ui.group) ? ui.group : pref;
      const rows = all.filter((r) => r.group === group).sort((x, y) => (x.rank ?? 999) - (y.rank ?? 999));
      rows.forEach((r, i) => { if (r.rank === null) r.rank = i + 1; });
      const z = zones(d, rows.length, ctx);
      const focus = rows.findIndex((r) => mark.has(r.id));
      const me = focus >= 0 ? rows[focus] : null;
      const leader = rows[0];
      let view;
      if (ui.open || rows.length <= 10) view = rows.map((r, i) => [r, i]);
      else if (focus <= 6) view = rows.slice(0, 9).map((r, i) => [r, i]);
      else {
        const from = Math.max(3, Math.min(focus - 3, rows.length - 7));
        view = [...rows.slice(0, 2).map((r, i) => [r, i]), null, ...rows.slice(from, from + 7).map((r, i) => [r, from + i])];
      }
      const zone = (i) => i < z.top ? "up" : z.bottom && i >= rows.length - z.bottom ? "down" : "";
      const sign = (v) => v === null ? "—" : `${v > 0 ? "+" : ""}${v}`;
      const v = (x) => x === null ? "—" : ctx.esc(x);
      const gap = me && leader && me !== leader && me.points !== null && leader.points !== null ? leader.points - me.points : null;
      el.innerHTML = `${head(me ? ctx.t("pos", { n: me.rank }) : "")}
        ${groups.length > 1 ? `<div class="st-tabs" role="tablist">${groups.slice(0, 8).map((g) => `<button type="button" role="tab" class="st-tab${g === group ? " on" : ""}" aria-selected="${g === group}" data-g="${ctx.esc(g)}">${ctx.esc(g || "—")}</button>`).join("")}</div>` : ""}
        ${me ? `<div class="st-me"><span class="st-me-rank mono">${me.rank}°</span><span class="st-me-txt"><b>${ctx.esc(me.name)}</b><small>${ctx.esc(gap === null ? ctx.t("leader") : gap === 0 ? ctx.t("level") : ctx.t("gap", { n: gap }))}</small></span>
          ${me.won !== null ? `<span class="st-form"><i class="w" style="flex:${me.won}"></i><i class="d" style="flex:${me.drawn || 0}"></i><i class="l" style="flex:${me.lost || 0}"></i></span><span class="st-wdl mono">${v(me.won)}-${v(me.drawn)}-${v(me.lost)}</span>` : ""}</div>` : ""}
        <table class="st-table"><thead><tr><th>#</th><th></th><th>${ctx.esc(ctx.t("col_played"))}</th><th class="x">${ctx.esc(ctx.t("col_won"))}</th><th class="x">${ctx.esc(ctx.t("col_drawn"))}</th><th class="x">${ctx.esc(ctx.t("col_lost"))}</th><th>${ctx.esc(ctx.t("col_diff"))}</th><th>${ctx.esc(ctx.t("col_points"))}</th></tr></thead><tbody>
        ${view.map((e) => e === null ? `<tr class="gap"><td colspan="8">⋯</td></tr>` : `<tr class="${mark.has(e[0].id) ? "me" : ""} ${zone(e[1])}"><td>${v(e[0].rank)}</td><td><span class="st-name">${e[0].color ? `<i style="--team:${e[0].color}"></i>` : "<i></i>"}<span>${ctx.esc(e[0].name)}</span></span></td>
          <td>${v(e[0].played)}</td><td class="x">${v(e[0].won)}</td><td class="x">${v(e[0].drawn)}</td><td class="x">${v(e[0].lost)}</td><td class="${(e[0].diff || 0) > 0 ? "pos" : (e[0].diff || 0) < 0 ? "neg" : ""}">${ctx.esc(sign(e[0].diff))}</td><td><b>${v(e[0].points)}</b></td></tr>`).join("")}</tbody></table>
        ${rows.length > 10 ? `<button type="button" class="st-more">${ctx.esc(ui.open ? ctx.t("less") : ctx.t("all", { n: rows.length }))}</button>` : ""}
        ${z.top || z.bottom ? `<div class="st-legend">${z.top ? `<span class="up">${ctx.esc(ctx.t("zone_up"))}</span>` : ""}${z.bottom ? `<span class="down">${ctx.esc(ctx.t("zone_down"))}</span>` : ""}</div>` : ""}`;
      el.onclick = (e) => {
        const tab = e.target.closest(".st-tab");
        if (tab) { ui.group = tab.dataset.g; ui.open = false; impl.render(el, raw, ctx); return; }
        if (e.target.closest(".st-more")) { ui.open = !ui.open; impl.render(el, raw, ctx); }
      };
    },
    destroy(el) { el.onclick = null; },
  };
  NuxivaDesk.register("sport_table", impl);
})();
