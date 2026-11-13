(() => {
  const ORBIT = ["spo2", "hrv", "resp_rate", "body_temp", "bp_sys", "glucose", "resting_hr", "weight"];
  const RINGS = [["steps", "hh-move"], ["active_kcal", "hh-burn"], ["sleep_min", "hh-rest"]];
  const SPAN = { spo2: [85, 100], hrv: [10, 120], resp_rate: [8, 24], body_temp: [35, 39], bp_sys: [90, 170], glucose: [60, 200], resting_hr: [40, 90], weight: [40, 120] };
  const METRIC = /^[a-z0-9_]{2,24}$/;
  const BANDS = new Set(["high", "mid", "low"]);

  function values(d, ctx) {
    const out = {};
    const raw = d && typeof d.values === "object" && d.values ? d.values : {};
    for (const [k, v] of Object.entries(raw)) {
      const n = v && typeof v === "object" ? ctx.num(v.value) : null;
      if (METRIC.test(k) && n !== null) out[k] = { value: n, unit: ctx.str(v.unit, 12), kind: ctx.str(v.kind, 8), age: ctx.num(v.age) || 0 };
    }
    return out;
  }


  function gauge(key, v, ctx) {
    const [lo, hi] = SPAN[key] || [0, 100];
    const pct = ctx.pct(((v.value - lo) / (hi - lo)) * 100);
    const shown = key === "bp_sys" && v.dia !== undefined ? `${ctx.fmt(v.value)}/${ctx.fmt(v.dia)}` : ctx.fmt(v.value, { maximumFractionDigits: 1 });
    return `<li class="hh-orb k-${key}" style="--p:${pct}"><i aria-hidden="true"></i><b>${ctx.esc(shown)}${v.dia === undefined ? `<small>${ctx.esc(v.unit)}</small>` : ""}</b><span>${ctx.esc(ctx.t(`m_${key}`))}</span></li>`;
  }

  function rings(d, ctx) {
    const goals = d && typeof d.goals === "object" && d.goals ? d.goals : {};
    const rows = RINGS.map(([k, cls], i) => {
      const g = goals[k];
      const pct = g && typeof g === "object" ? ctx.num(g.pct) : null;
      if (pct === null) return "";
      const r = 26 - i * 7, c = 2 * Math.PI * r, fill = (c * Math.min(100, pct)) / 100;
      return `<circle class="trk ${cls}" cx="32" cy="32" r="${r}"/><circle class="val ${cls}" cx="32" cy="32" r="${r}" stroke-dasharray="${fill.toFixed(1)} ${c.toFixed(1)}"/>`;
    }).join("");
    if (!rows) return "";
    const legend = RINGS.map(([k, cls]) => {
      const g = goals[k];
      const n = g && typeof g === "object" ? ctx.num(g.value) : null;
      if (n === null) return "";
      const text = k === "sleep_min" ? ctx.t("hours", { h: Math.floor(n / 60), m: Math.round(n % 60) }) : ctx.fmt(n);
      return `<li class="${cls}"><i aria-hidden="true"></i>${ctx.esc(ctx.t(`m_${k}`))}<b>${ctx.esc(text)}</b></li>`;
    }).join("");
    return `<div class="hh-act"><svg viewBox="0 0 64 64" aria-hidden="true">${rows}</svg><ul>${legend}</ul></div>`;
  }

  function signals(d, ctx) {
    return ctx.arr(d && d.signals, 4).filter((s) => s && METRIC.test(String(s.metric)) && METRIC.test(String(s.code)))
      .map((s) => `<li class="${s.level === "alert" ? "alert" : "warn"}">${ctx.esc(ctx.t(`s_${s.metric}_${s.code}`))}</li>`).join("");
  }

  NuxivaDesk.register("health_hub", {
    headline(d, ctx) {
      const data = d && typeof d === "object" ? d : {};
      return { text: ctx.t("say_plain") };
    },
    render(el, d, ctx) {
      const data = d && typeof d === "object" ? d : {};
      const v = values(data, ctx);
      const who = data.person && typeof data.person === "object" ? ctx.str(data.person.name, 40) : "";
      const rec = data.recovery && typeof data.recovery === "object" && BANDS.has(data.recovery.band) ? data.recovery : null;
      const head = ctx.head({ icon: "sparkle", label: ctx.t("label"), title: who, chip: rec ? ctx.t("recovery", { n: ctx.fmt(rec.score) }) : "", state: rec ? `band-${rec.band}` : "" });
      if (!Object.keys(v).length) { el.innerHTML = `${head}${ctx.empty(ctx.tc("waiting"))}`; return; }
      if (v.bp_sys && v.bp_dia) v.bp_sys.dia = v.bp_dia.value;
      const orbit = ORBIT.filter((k) => v[k]).slice(0, 6).map((k) => gauge(k, v[k], ctx)).join("");
      const alerts = signals(data, ctx);
      el.innerHTML = `${head}
        ${orbit ? `<ul class="hh-orbit">${orbit}</ul>` : ""}
        ${rings(data, ctx)}
        ${alerts ? `<ul class="hh-sig" role="status">${alerts}</ul>` : ""}`;
    },
  });
})();
