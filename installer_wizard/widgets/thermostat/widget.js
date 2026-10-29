(() => {
  const MODE = [[/heat|riscald|calent|chauff|caldo/i, "heat", "fire"], [/cool|raffresc|enfri|refroid|freddo|condiz/i, "cool", "snow"], [/off|spent|apag|éteint|eteint/i, "off", "stop"], [/dry|deumid|seco|déshum/i, "dry", "drop"], [/fan|ventil/i, "fan", "wind"], [/auto/i, "auto", "sparkle"], [/idle|standby|attesa|reposo|veille/i, "idle", "clock"]];
  const temp = (v, ctx) => { const n = ctx.num(typeof v === "string" ? v.replace(/°\s*[cC]?/, "") : v); return n === null || n < -50 || n > 80 ? null : n; };

  const dial = (cur, target, lo, hi, uid) => {
    const r = 42;
    const at = (v) => Math.max(0, Math.min(1, (v - lo) / (hi - lo)));
    const pt = (v) => { const a = Math.PI * 0.75 + at(v) * Math.PI * 1.5; return [48 + r * Math.cos(a), 48 + r * Math.sin(a)]; };
    const fill = cur === null ? 0 : at(cur);
    const [sx, sy] = pt(lo), [ex, ey] = pt(hi);
    const [tx, ty] = target === null ? [0, 0] : pt(target);
    const d = `M${sx.toFixed(2)} ${sy.toFixed(2)} A${r} ${r} 0 1 1 ${ex.toFixed(2)} ${ey.toFixed(2)}`;
    return `<svg class="th-dial" viewBox="0 0 96 96" aria-hidden="true"><defs><linearGradient id="${uid}" gradientUnits="userSpaceOnUse" x1="6" y1="48" x2="90" y2="48"><stop offset="0" stop-color="#38bdf8"/><stop offset=".55" stop-color="#facc15"/><stop offset="1" stop-color="#f97316"/></linearGradient></defs>
      <path class="trk" d="${d}"/>
      <path class="val" d="${d}" stroke="url(#${uid})" pathLength="100" stroke-dasharray="${(fill * 100).toFixed(1)} 100"/>
      ${target !== null ? `<circle class="tgt" cx="${tx.toFixed(1)}" cy="${ty.toFixed(1)}" r="4"/>` : ""}</svg>`;
  };

  let seq = 0;

  NuxivaDesk.register("thermostat", {
    render(el, raw, ctx) {
      const d = raw && typeof raw === "object" ? raw : {};
      const cur = temp(d.current ?? d.temperature, ctx), target = temp(d.target ?? d.setpoint, ctx), out = temp(d.outside ?? d.outdoor, ctx);
      const lo = temp(d.min, ctx) ?? Math.min(10, cur ?? 10, target ?? 10), hi = temp(d.max, ctx) ?? Math.max(30, cur ?? 30, target ?? 30);
      const hum = ctx.num(d.humidity);
      const status = ctx.pick(d, ["status", "mode", "action", "hvac"], 30);
      const mode = MODE.find(([re]) => re.test(status)) || null;
      const diff = cur !== null && target !== null ? Math.round((target - cur) * 10) / 10 : null;
      const rooms = ctx.arr(d.rooms, 8).filter((r) => r && typeof r === "object").map((r) => ({ name: ctx.pick(r, ["name", "room", "label"], 30), cur: temp(r.current ?? r.temperature, ctx), target: temp(r.target, ctx) })).filter((r) => r.name);
      const uid = el._thId || (el._thId = `thg${++seq}`);
      const f = (v) => `${ctx.fmt(v, { maximumFractionDigits: 1 })}°`;
      const humNote = hum === null ? "" : hum < 30 ? "dry" : hum > 65 ? "humid" : "";
      if (cur === null && target === null && !rooms.length) { el.innerHTML = `${ctx.head({ icon: "therm", label: ctx.t("label"), title: ctx.str(d.room, 40) })}${ctx.empty(ctx.tc("waiting"))}`; return; }
      el.innerHTML = `${ctx.head({ icon: "therm", label: ctx.t("label"), title: ctx.str(d.room, 40), chip: mode ? ctx.t(`m_${mode[1]}`) : status || ctx.t("standby"), live: !!mode && ["heat", "cool", "dry", "fan"].includes(mode[1]) })}
        <div class="th-main${mode ? ` ${mode[1]}` : ""}">
          <div class="th-gauge">${mode ? `<span class="th-badge">${ctx.icon(mode[2])}</span>` : ""}${dial(cur, target, lo, hi, uid)}<div class="th-read"><b>${cur === null ? "—" : f(cur)}</b><small>${ctx.esc(ctx.t("now"))}</small></div></div>
          <div class="th-side">
            <div class="th-target"><small>${ctx.esc(ctx.t("target"))}</small><b class="mono">${target === null ? "—" : f(target)}</b></div>
            ${diff !== null && Math.abs(diff) >= 0.3 ? `<div class="th-diff ${diff > 0 ? "up" : "down"}">${ctx.icon(diff > 0 ? "fire" : "snow")}<span>${ctx.esc(ctx.t(diff > 0 ? "to_heat" : "to_cool", { n: ctx.fmt(Math.abs(diff), { maximumFractionDigits: 1 }) }))}</span></div>` : diff !== null ? `<div class="th-diff ok">${ctx.icon("check")}<span>${ctx.esc(ctx.t("reached"))}</span></div>` : ""}
          </div></div>
        <div class="th-facts">
          ${hum !== null ? `<span class="${humNote}">${ctx.icon("drop")}<b class="mono">${Math.round(Math.max(0, Math.min(100, hum)))}%</b>${humNote ? `<small>${ctx.esc(ctx.t(`h_${humNote}`))}</small>` : ""}</span>` : ""}
          ${out !== null ? `<span>${ctx.icon("partly")}<small>${ctx.esc(ctx.t("outside"))}</small><b class="mono">${f(out)}</b></span>` : ""}
        </div>
        ${rooms.length ? `<ul class="th-rooms">${rooms.map((r) => `<li><span>${ctx.esc(r.name)}</span><b class="mono">${r.cur === null ? "—" : f(r.cur)}</b>${r.target !== null ? `<small class="mono">→ ${f(r.target)}</small>` : "<small></small>"}</li>`).join("")}</ul>` : ""}`;
    },
  });
})();
