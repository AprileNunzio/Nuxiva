(() => {
  const STATES = new Set(["idle", "listening", "transcribing", "off"]);
  const BARS = 12;
  const wake = () => (window.NUXIVA_ASSISTANT && typeof window.NUXIVA_ASSISTANT.name === "string" ? window.NUXIVA_ASSISTANT.name.slice(0, 40) : "");

  function stop(el) {
    if (el._lsOff) el._lsOff();
    el._lsOff = null;
  }

  NuxivaDesk.register("listening", {
    render(el, d, ctx) {
      stop(el);
      const label = (s) => ctx.t(`state_${s}`, { name: wake() });
      el.innerHTML = `<button type="button" class="ls-box idle"><span class="ls-ic">${ctx.icon("mic")}</span><span class="ls-bars" aria-hidden="true">${"<i></i>".repeat(BARS)}</span><span class="ls-t" aria-live="polite">${ctx.esc(label("idle"))}</span></button>`;
      const box = el.firstChild, bars = [...box.querySelectorAll(".ls-bars i")], text = box.querySelector(".ls-t");
      const hist = new Float32Array(BARS);
      let state = "idle", raf = 0, last = 0;
      const draw = () => {
        raf = 0;
        for (let i = 0; i < BARS; i++) bars[i].style.transform = `scaleY(${(0.15 + Math.min(1, hist[i]) * 0.85).toFixed(3)})`;
      };
      const schedule = () => { if (!raf) raf = requestAnimationFrame(draw); };
      const decay = setInterval(() => {
        if (performance.now() - last < 120) return;
        let any = false;
        for (let i = 0; i < BARS; i++) { hist[i] *= 0.7; any ||= hist[i] > 0.01; }
        if (any) schedule();
      }, 90);
      const onState = (e) => {
        const s = String((e.detail && e.detail.state) || "idle");
        state = STATES.has(s) ? s : "idle";
        box.className = `ls-box ${state}`;
        text.textContent = label(state);
        box.setAttribute("aria-label", label(state));
      };
      const onLevel = (e) => {
        const v = Number(e.detail);
        if (!Number.isFinite(v) || state !== "listening") return;
        hist.copyWithin(0, 1);
        hist[BARS - 1] = Math.max(0, Math.min(1, v * 2.4));
        last = performance.now();
        schedule();
      };
      const onTap = (e) => {
        e.stopPropagation();
        const ear = window.nuxivaEar;
        if (!ear) return;
        if (state === "off" && typeof ear.restartMic === "function") ear.restartMic();
        else if (state === "idle" && typeof ear.listen === "function") ear.listen();
      };
      box.addEventListener("click", onTap);
      window.addEventListener("nuxiva-ear", onState);
      window.addEventListener("nuxiva-ear-level", onLevel);
      el._lsOff = () => {
        window.removeEventListener("nuxiva-ear", onState);
        window.removeEventListener("nuxiva-ear-level", onLevel);
        clearInterval(decay);
        if (raf) cancelAnimationFrame(raf);
      };
      onState({ detail: { state: window.nuxivaEar ? window.nuxivaEar.state : "idle" } });
    },
    update() {},
    destroy: stop,
  });
})();
