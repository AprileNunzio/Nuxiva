(() => {
  const PHASES = new Set(["greet", "device", "camera", "done", "failed"]);
  const ICON = { greet: "user", device: "bt", camera: "eye", done: "check", failed: "alert" };
  const STEPS = { device: ["d_search", "d_connect", "d_read"], camera: ["c_still", "c_look", "c_breathe"] };
  const R = 52, C = 2 * Math.PI * R;

  const value = (v, lo, hi, ctx) => {
    const n = ctx.num(v);
    return n !== null && n >= lo && n <= hi ? Math.round(n) : null;
  };

  const activeStep = (d) => {
    if (d.phase === "device") return d.elapsed < 4 ? 0 : d.elapsed < 12 ? 1 : 2;
    if (d.phase === "camera") return d.heart ? 2 : d.hold > 0 ? 0 : 1;
    return 3;
  };

  const parse = (raw, ctx) => {
    const d = raw && typeof raw === "object" ? raw : {};
    const vals = d.values && typeof d.values === "object" ? d.values : {};
    return {
      session: ctx.str(d.session, 80), phase: PHASES.has(d.phase) ? d.phase : "greet", who: d.person && typeof d.person === "object" ? ctx.str(d.person.name, 40) : "",
      first: d.person && typeof d.person === "object" ? ctx.str(d.person.name, 40).split(" ")[0] : "",
      heart: value(vals.heart_rate, 30, 230, ctx), breath: value(vals.resp_rate, 4, 60, ctx), source: d.source === "device" ? "device" : "camera",
      hold: Math.max(0, Math.min(99, ctx.num(d.hold_left) || 0)), progress: ctx.pct((ctx.num(d.progress) || 0) * 100), moved: d.moved === true,
      elapsed: Math.max(0, ctx.num(d.elapsed) || 0),
      devices: ctx.arr(d.devices, 3).filter((x) => x && typeof x === "object").map((x) => ctx.str(x.label, 40)).filter(Boolean),
    };
  };

  const steps = (d, ctx) => {
    const list = STEPS[d.phase];
    if (!list) return "";
    const at = activeStep(d);
    return `<ol class="vc-steps">${list.map((k, i) => `<li class="${i < at ? "done" : i === at ? "now" : ""}"><i aria-hidden="true">${i < at ? ctx.icon("check") : i + 1}</i><span>${ctx.esc(ctx.t(k))}</span></li>`).join("")}</ol>`;
  };

  const results = (d, ctx) => {
    if (d.heart === null && d.breath === null) return "";
    const cell = (k, v, unit) => (v === null ? "" : `<li class="vc-v-${k}"><span>${ctx.esc(ctx.t(`m_${k}`))}</span><div><b>${ctx.esc(ctx.fmt(v))}</b><small>${ctx.esc(unit)}</small></div></li>`);
    return `<ul class="vc-vals">${cell("heart", d.heart, "bpm")}${cell("breath", d.breath, ctx.t("per_min"))}</ul>`;
  };

  const message = (d, ctx) => {
    if (d.moved) return ctx.t("moved");
    if (d.phase === "greet") return ctx.t("greet", { name: d.first || d.who });
    if (d.phase === "device") return d.devices.length ? ctx.t("device_named", { name: d.devices.join(", ") }) : ctx.t("device");
    if (d.phase === "camera") return d.heart ? ctx.t("camera_breath") : d.hold > 0 ? ctx.t("camera_hold", { n: d.hold }) : ctx.t("camera_wait");
    if (d.phase === "done") return ctx.t(d.source === "device" ? "done_device" : "done_camera");
    return ctx.t("failed");
  };

  const core = (d, ctx) => {
    if (d.phase === "camera" && d.heart === null) return `<b class="vc-count">${d.hold || ""}</b><small>${ctx.esc(ctx.t(d.hold ? "seconds" : "measuring"))}</small>`;
    if (d.heart !== null) return `<svg class="vc-heart" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 21s-7.5-4.6-9.6-9.2C.9 8.4 3 4.5 6.7 4.5c2.1 0 3.6 1.2 4.3 2.4.7-1.2 2.2-2.4 4.3-2.4 3.7 0 5.8 3.9 4.3 7.3C19.5 16.4 12 21 12 21z"/></svg><b class="vc-count">${d.heart}</b><small>bpm</small>`;
    return `<span class="vc-glyph" aria-hidden="true">${ctx.icon(ICON[d.phase])}</span>`;
  };

  NuxivaDesk.register("vital_check", {
    render(el, raw, ctx) {
      const d = parse(raw, ctx);
      const sync = `-${(Date.now() % 1200) / 1000}s`;
      const beat = d.heart ? `${(60 / d.heart).toFixed(3)}s` : "1.2s";
      const offset = (C * (1 - d.progress / 100)).toFixed(1);
      el.innerHTML = `${ctx.head({ icon: ICON[d.phase], label: ctx.t(`title_${d.phase}`), title: d.who, live: d.phase === "camera" || d.phase === "device",
        chip: d.phase === "camera" || d.phase === "device" ? `${Math.round(d.progress)}%` : "", state: d.phase === "failed" ? "bad" : d.phase === "done" ? "ok" : "" })}
        <div class="vc-wrap vc-${d.phase}${d.moved ? " vc-moved" : ""}${d.heart !== null ? " vc-live" : ""}" style="--sync:${sync};--beat:${beat}">
          <div class="vc-dial">
            <svg viewBox="0 0 128 128" aria-hidden="true"><circle class="vc-trk" cx="64" cy="64" r="${R}"/><circle class="vc-arc" cx="64" cy="64" r="${R}" stroke-dasharray="${C.toFixed(1)}" stroke-dashoffset="${offset}"/></svg>
            <i class="vc-halo" aria-hidden="true"></i>
            <div class="vc-core">${core(d, ctx)}</div>
          </div>
          <div class="vc-side">
            <p class="vc-msg" role="status" aria-live="polite">${ctx.esc(message(d, ctx))}</p>
            ${steps(d, ctx)}
            ${d.phase === "done" ? results(d, ctx) : ""}
            ${d.phase === "done" ? `<p class="vc-note">${ctx.esc(ctx.t(d.source === "device" ? "src_device" : "src_camera"))} · ${ctx.esc(ctx.t("not_medical"))}</p>` : ""}
          </div>
        </div>`;
    },
  });
})();
