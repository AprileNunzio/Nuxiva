(() => {
  const PHASES = ["focus", "short", "long"];
  const R = 46, C = 2 * Math.PI * R;
  let shared = null;

  const minutes = (v, def, max) => { const n = Number(v); return Number.isFinite(n) && n > 0 ? Math.min(max, n) : def; };

  function config(d) {
    return { focus: minutes(d.focus_min, 25, 180) * 60, short: minutes(d.break_min ?? d.short_min, 5, 60) * 60, long: minutes(d.long_min, 15, 90) * 60, every: Math.round(minutes(d.rounds ?? d.every, 4, 12)) };
  }

  function fresh(cfg) { return { cfg, phase: "focus", round: 1, left: cfg.focus, ends: 0, running: false, done: 0 }; }

  function chime() {
    try {
      const Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx) return;
      const a = new Ctx();
      [0, 0.22, 0.44].forEach((t, i) => {
        const o = a.createOscillator(), g = a.createGain();
        o.type = "sine";
        o.frequency.value = [880, 1175, 1568][i];
        g.gain.setValueAtTime(0.0001, a.currentTime + t);
        g.gain.exponentialRampToValueAtTime(0.18, a.currentTime + t + 0.02);
        g.gain.exponentialRampToValueAtTime(0.0001, a.currentTime + t + 0.5);
        o.connect(g).connect(a.destination);
        o.start(a.currentTime + t);
        o.stop(a.currentTime + t + 0.55);
      });
      setTimeout(() => a.close().catch(() => {}), 1500);
    } catch {}
  }

  function remaining(s) { return s.running ? Math.max(0, (s.ends - Date.now()) / 1000) : s.left; }

  function advance(s, ctx) {
    if (s.phase === "focus") {
      s.done += 1;
      s.phase = s.round % s.cfg.every === 0 ? "long" : "short";
    } else {
      if (s.phase === "long") s.round = 0;
      s.round += 1;
      s.phase = "focus";
    }
    s.left = s.cfg[s.phase];
    s.ends = Date.now() + s.left * 1000;
    chime();
    ctx.speak(ctx.t(`say_${s.phase}`));
  }

  function stop(el) { clearInterval(el._poT); el._poT = 0; }

  function paint(el, ctx) {
    const s = shared;
    const left = remaining(s), total = s.cfg[s.phase];
    const arc = el.querySelector(".po-arc"), time = el.querySelector(".po-time");
    if (!arc || !time) return;
    arc.style.strokeDashoffset = `${C * (1 - left / total)}`;
    time.textContent = ctx.mmss(Math.ceil(left));
  }

  function draw(el, d, ctx) {
    const s = shared;
    const task = ctx.str(d.task ?? d.title ?? d.content, 120);
    el.innerHTML = `${ctx.head({ icon: "tomato", label: ctx.t("label"), chip: ctx.t("round_of", { n: Math.min(s.round, s.cfg.every), m: s.cfg.every }), live: s.running, state: s.phase === "focus" ? "" : "ok" })}
      <div class="po po-${s.phase}${s.running ? " run" : ""}">
        <div class="po-dial"><svg viewBox="0 0 110 110" aria-hidden="true"><circle class="po-track" cx="55" cy="55" r="${R}"/><circle class="po-arc" cx="55" cy="55" r="${R}" stroke-dasharray="${C.toFixed(2)}"/></svg>
          <div class="po-center"><b class="po-time mono" role="timer" aria-live="off"></b><small>${ctx.esc(ctx.t(s.running ? `ph_${s.phase}` : "paused"))}</small></div></div>
        <div class="po-dots" aria-label="${ctx.esc(ctx.count("done", s.done))}">${Array.from({ length: s.cfg.every }, (_, i) => `<i class="${i < (s.round - 1) || (i === s.round - 1 && s.phase !== "focus") ? "on" : i === s.round - 1 && s.phase === "focus" ? "now" : ""}"></i>`).join("")}</div>
        ${task ? `<div class="po-task">${ctx.icon("pin")}<span>${ctx.esc(task)}</span></div>` : ""}
        <div class="po-ctl">
          <button type="button" class="wk-btn primary" data-a="toggle">${ctx.icon(s.running ? "stop" : "play")}<span>${ctx.esc(ctx.t(s.running ? "pause" : s.left < s.cfg[s.phase] ? "resume" : "start"))}</span></button>
          <button type="button" class="wk-btn icon" data-a="skip" title="${ctx.esc(ctx.t("skip"))}" aria-label="${ctx.esc(ctx.t("skip"))}"><span class="po-skip" aria-hidden="true">»</span></button>
          <button type="button" class="wk-btn icon" data-a="reset" title="${ctx.esc(ctx.t("reset"))}" aria-label="${ctx.esc(ctx.t("reset"))}">${ctx.icon("refresh")}</button>
        </div>
        ${s.done ? `<div class="wk-faint po-done">${ctx.esc(ctx.count("done", s.done))}</div>` : ""}
      </div>`;
    paint(el, ctx);
  }

  const impl = {
    render(el, d, ctx) {
      stop(el);
      const data = d && typeof d === "object" ? d : {};
      const cfg = config(data);
      if (!shared || JSON.stringify(shared.cfg) !== JSON.stringify(cfg)) shared = fresh(cfg);
      const phase = PHASES.includes(data.phase) ? data.phase : null;
      const ends = ctx.stamp(data.ends_at);
      if (phase && ends && ends * 1000 > Date.now()) Object.assign(shared, { phase, running: true, ends: ends * 1000, left: cfg[phase] });
      else if (data.autostart === true && !shared.running && shared.left === cfg.focus) Object.assign(shared, { running: true, ends: Date.now() + cfg.focus * 1000 });
      el._poD = data;
      draw(el, data, ctx);
      el.onclick = (e) => {
        const b = e.target.closest("[data-a]");
        if (!b) return;
        e.stopPropagation();
        const s = shared;
        if (b.dataset.a === "toggle") {
          if (s.running) { s.left = remaining(s); s.running = false; }
          else { s.ends = Date.now() + s.left * 1000; s.running = true; }
        } else if (b.dataset.a === "skip") {
          const was = s.running;
          advance(s, ctx);
          s.running = was;
          if (!was) s.left = s.cfg[s.phase];
        } else if (b.dataset.a === "reset") {
          shared = fresh(s.cfg);
        }
        draw(el, el._poD, ctx);
      };
      el._poT = setInterval(() => {
        if (!el.isConnected) { stop(el); return; }
        const s = shared;
        if (s.running && remaining(s) <= 0) { advance(s, ctx); draw(el, el._poD, ctx); return; }
        paint(el, ctx);
      }, 250);
    },
    update(el, d, ctx) { el._poD = d && typeof d === "object" ? d : {}; if (!el._poT) impl.render(el, d, ctx); },
    destroy: stop,
  };
  NuxivaDesk.register("pomodoro", impl);
})();
