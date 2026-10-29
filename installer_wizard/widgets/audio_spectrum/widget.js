(() => {
  const FPS = 30;
  const safeImg = (u) => {
    const s = typeof u === "string" ? u.trim() : "";
    return /^(https:\/\/|\/(?!\/))[^\s"'<>\\]+$/i.test(s) ? s : "";
  };
  const reduced = () => window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function stop(el) {
    const v = el._viz;
    if (!v) return;
    cancelAnimationFrame(v.raf);
    if (v.ro) v.ro.disconnect();
    el._viz = null;
  }

  function levels(raw, ctx) {
    const list = ctx.arr(raw, 256).map((x) => ctx.num(x)).filter((x) => x !== null);
    if (list.length < 4) return null;
    const max = Math.max(...list);
    const scale = max > 1 ? 100 : 1;
    return list.map((x) => Math.max(0, Math.min(1, x / scale)));
  }

  function start(el, canvas, opts) {
    const v = { raf: 0, ro: null, w: 0, h: 0, dpr: 1, bars: [], drift: [], last: 0, t0: performance.now() };
    el._viz = v;
    const g = canvas.getContext("2d", { alpha: true });
    const tone = (getComputedStyle(canvas).getPropertyValue("--tone") || "41, 224, 255").trim();
    const size = () => {
      const r = canvas.getBoundingClientRect();
      v.dpr = Math.min(2, window.devicePixelRatio || 1);
      v.w = Math.max(1, Math.round(r.width));
      v.h = Math.max(1, Math.round(r.height));
      canvas.width = Math.round(v.w * v.dpr);
      canvas.height = Math.round(v.h * v.dpr);
      const n = Math.max(16, Math.min(96, Math.floor(v.w / 7)));
      if (v.bars.length !== n) { v.bars = new Float32Array(n); v.drift = Float32Array.from({ length: n }, () => Math.random()); }
    };
    const target = (i, n, t) => {
      const x = i / (n - 1);
      if (opts.levels) {
        const src = opts.levels[Math.min(opts.levels.length - 1, Math.floor(x * opts.levels.length))];
        return src * (0.92 + 0.08 * Math.sin(t * 3 + i));
      }
      if (!opts.active) return 0.05 + 0.03 * Math.sin(t * 1.2 + i * 0.35);
      const beat = Math.pow(Math.max(0, Math.cos(Math.PI * 2 * t * (opts.bpm / 60))), 6);
      const env = 0.95 * Math.exp(-x * 1.6) + 0.18 + 0.12 * Math.exp(-((x - 0.45) ** 2) / 0.02);
      v.drift[i] = Math.max(0, Math.min(1, v.drift[i] + (Math.random() - 0.5) * 0.18));
      return Math.min(1, env * (0.35 + 0.55 * v.drift[i]) * (1 + beat * 0.55 * (1 - x)));
    };
    const draw = (now) => {
      const n = v.bars.length, t = (now - v.t0) / 1000;
      g.setTransform(v.dpr, 0, 0, v.dpr, 0, 0);
      g.clearRect(0, 0, v.w, v.h);
      const gap = 2, bw = Math.max(1.5, (v.w - gap * (n - 1)) / n), mid = v.h * 0.62;
      const up = g.createLinearGradient(0, mid, 0, 0);
      up.addColorStop(0, `rgba(${tone}, 0.95)`);
      up.addColorStop(1, `rgba(${tone}, 0.25)`);
      const down = g.createLinearGradient(0, mid, 0, v.h);
      down.addColorStop(0, `rgba(${tone}, 0.35)`);
      down.addColorStop(1, `rgba(${tone}, 0)`);
      for (let i = 0; i < n; i++) {
        const want = target(i, n, t);
        const cur = v.bars[i];
        v.bars[i] = want > cur ? cur + (want - cur) * 0.55 : cur + (want - cur) * 0.12;
        const hUp = Math.max(1, v.bars[i] * mid * 0.96), hDown = hUp * 0.38;
        const x = i * (bw + gap);
        g.fillStyle = up;
        g.fillRect(x, mid - hUp, bw, hUp);
        g.fillStyle = down;
        g.fillRect(x, mid + 1, bw, hDown);
      }
      g.fillStyle = `rgba(${tone}, 0.25)`;
      g.fillRect(0, mid, v.w, 1);
    };
    const loop = (now) => {
      if (!canvas.isConnected) { stop(el); return; }
      v.raf = requestAnimationFrame(loop);
      if (document.hidden || now - v.last < 1000 / FPS) return;
      v.last = now;
      draw(now);
    };
    size();
    if ("ResizeObserver" in window) { v.ro = new ResizeObserver(() => { size(); if (reduced()) draw(performance.now()); }); v.ro.observe(canvas); }
    if (reduced()) { for (let k = 0; k < 20; k++) draw(performance.now()); return; }
    v.raf = requestAnimationFrame(loop);
  }

  NuxivaDesk.register("audio_spectrum", {
    render(el, d, ctx) {
      stop(el);
      const data = d && typeof d === "object" ? d : {};
      const np = (window.NuxivaDisplay && window.NuxivaDisplay.state && window.NuxivaDisplay.state.now_playing) || {};
      const [first = "", ...rest] = ctx.lines(data.content, 4, 2000);
      const title = ctx.pick(data, ["title", "track"], 120) || first || ctx.pick(np, ["title"], 120);
      const artist = ctx.pick(data, ["artist", "source"], 120) || (first ? "" : ctx.pick(np, ["artist"], 120));
      const cover = safeImg(data.cover) || (first || data.title ? "" : safeImg(np.cover));
      const lv = levels(data.levels, ctx);
      const bpmRaw = ctx.num(data.bpm ?? np.bpm);
      const bpm = bpmRaw && bpmRaw >= 40 && bpmRaw <= 220 ? bpmRaw : 112;
      const active = !!(title || lv);
      el.innerHTML = `${ctx.head({ icon: "wave", label: ctx.t("label"), chip: active ? ctx.tc("live") : "", live: active })}
        <div class="as-viz"><canvas aria-hidden="true"></canvas></div>
        ${title ? `<div class="as-meta">${cover ? `<img class="as-cover" alt="" loading="lazy" decoding="async" referrerpolicy="no-referrer" src="${ctx.esc(cover)}">` : ""}
          <div class="as-text"><div class="wk-title">${ctx.esc(title)}</div>${artist ? `<div class="wk-sub">${ctx.esc(artist)}</div>` : ""}
          ${rest.map((l) => `<div class="wk-sub">${ctx.esc(l)}</div>`).join("")}</div>
          ${bpmRaw && bpm === bpmRaw ? `<span class="as-bpm">${ctx.esc(ctx.fmt(Math.round(bpm)))}<small>BPM</small></span>` : ""}</div>`
        : ctx.empty(ctx.t("silent"))}`;
      const img = el.querySelector(".as-cover");
      if (img) img.addEventListener("error", () => img.remove(), { once: true });
      start(el, el.querySelector("canvas"), { levels: lv, bpm, active });
    },
    destroy(el) { stop(el); },
  });
})();
