(() => {
  const STATES = new Set(["idle", "listening", "transcribing", "off"]);
  const wake = () => (window.NUXIVA_ASSISTANT && window.NUXIVA_ASSISTANT.name) || "";
  NuxivaDesk.register("listening", {
    render(el, d, ctx) {
      const label = (s) => ctx.t(`state_${STATES.has(s) ? s : "idle"}`, { name: wake() });
      el.innerHTML = `<div class="ls-box idle"><span class="ls-ic">${ctx.icon("mic")}</span><span class="ls-bars">${"<i></i>".repeat(10)}</span><span class="ls-t">${ctx.esc(label("idle"))}</span></div>`;
      const box = el.firstChild, bars = [...box.querySelectorAll(".ls-bars i")], text = box.querySelector(".ls-t");
      const onState = (e) => {
        const s = String(e.detail.state || "idle");
        box.className = `ls-box ${STATES.has(s) ? s : "idle"}`;
        text.textContent = label(s);
      };
      const onLevel = (e) => {
        const v = Number(e.detail) || 0;
        bars.forEach((b, i) => { b.style.height = `${3 + Math.max(0, v * 30 - Math.abs(i - 4.5) * 2 + Math.random() * 3)}px`; });
      };
      window.addEventListener("nuxiva-ear", onState);
      window.addEventListener("nuxiva-ear-level", onLevel);
      el._off = () => { window.removeEventListener("nuxiva-ear", onState); window.removeEventListener("nuxiva-ear-level", onLevel); };
      if (window.nuxivaEar) onState({ detail: { state: window.nuxivaEar.state } });
    },
    update() {},
    destroy(el) { if (el._off) el._off(); },
  });
})();
