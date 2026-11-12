(() => {
  const KIND = { smoke: "fire", gas: "alert", flood: "drop", intrusion: "shield", co: "fog", generic: "alert" };
  const ALIAS = { fire: "smoke", fumo: "smoke", water: "flood", leak: "flood", acqua: "flood", burglar: "intrusion", intrusione: "intrusion", monoxide: "co", carbon_monoxide: "co" };
  const REPEAT_MS = 45000;

  const stop = (el) => { clearInterval(el._rep); clearInterval(el._tick); el._rep = 0; el._tick = 0; };
  const span = (sec) => {
    const s = Math.max(0, Math.floor(sec)), h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), r = s % 60;
    return h ? `${h}:${String(m).padStart(2, "0")}:${String(r).padStart(2, "0")}` : `${m}:${String(r).padStart(2, "0")}`;
  };

  NuxivaDesk.register("alarm", {
    render(el, d, ctx) {
      stop(el);
      const data = d && typeof d === "object" ? d : {};
      const raw = ctx.str(data.kind, 30).toLowerCase();
      const kind = Object.hasOwn(KIND, raw) ? raw : ALIAS[raw] || "generic";
      const test = data.test === true;
      const now = ctx.now();
      const stamp = ctx.stamp(data.at);
      const at = stamp && stamp <= now + 60 ? stamp : now;
      const title = ctx.str(data.title, 80) || ctx.t(`kind_${kind}`);
      const room = ctx.str(data.room, 60);
      const message = ctx.str(data.message, 400);
      const speak = ctx.str(data.speak, 240);
      el.innerHTML = `${ctx.head({ icon: "alert", label: ctx.t("label"), chip: ctx.t(test ? "status_test" : "status_active"), live: !test, state: test ? "warn" : "bad" })}
        <div class="al-core${test ? " al-test" : ""}" role="alert" aria-live="assertive">
          <div class="al-mark"><span class="al-ring"></span><span class="al-ring r2"></span><span class="al-ring r3"></span><span class="al-icon">${ctx.icon(KIND[kind])}</span></div>
          <div class="al-title">${ctx.esc(title)}</div>
          ${room ? `<div class="al-room">${ctx.icon("pin")}<span>${ctx.esc(room)}</span></div>` : ""}
          ${message ? `<div class="al-msg">${ctx.esc(message)}</div>` : ""}
          <div class="al-advice">${ctx.icon("info")}<span>${ctx.esc(ctx.t(`advice_${kind}`))}</span></div>
          <div class="al-time"><span>${ctx.esc(ctx.when(at, { hour: "2-digit", minute: "2-digit", second: "2-digit" }))}</span><span class="al-sep">·</span><span>${ctx.esc(ctx.t("elapsed"))} <b class="al-elapsed">${span(now - at)}</b></span></div>
          ${test ? `<div class="al-banner">${ctx.esc(ctx.t("test_note"))}</div>` : ""}
        </div>`;
      const out = el.querySelector(".al-elapsed");
      el._tick = setInterval(() => {
        if (!el.isConnected) { stop(el); return; }
        out.textContent = span(ctx.now() - at);
      }, 1000);
      if (speak && !test) el._rep = setInterval(() => { if (el.isConnected) ctx.speak(speak); else stop(el); }, REPEAT_MS);
    },
    destroy(el) { stop(el); },
  });
})();
