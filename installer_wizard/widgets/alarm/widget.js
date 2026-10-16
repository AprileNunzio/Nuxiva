(() => {
  const KIND = { smoke: "fire", gas: "alert", flood: "drop", intrusion: "shield", co: "fog", generic: "alert" };
  NuxivaDesk.register("alarm", {
    render(el, d, ctx) {
      const kind = Object.hasOwn(KIND, d.kind) ? d.kind : "generic";
      const at = Number(d.at) > 0 ? Number(d.at) : ctx.now();
      const time = new Date(at * 1000).toLocaleTimeString(ctx.locale(), { hour: "2-digit", minute: "2-digit", second: "2-digit" });
      el.innerHTML = `${ctx.head({ icon: "alert", label: ctx.t("label"), chip: ctx.t(d.test ? "status_test" : "status_active"), live: !d.test, state: "bad" })}
        <div class="al-core">
          <div class="al-mark"><span class="al-ring"></span><span class="al-ring r2"></span><span class="al-icon">${ctx.icon(KIND[kind])}</span></div>
          <div class="al-title">${ctx.esc(String(d.title || ctx.t(`kind_${kind}`)).slice(0, 80))}</div>
          ${d.room ? `<div class="al-room">${ctx.esc(String(d.room).slice(0, 60))}</div>` : ""}
          ${d.message ? `<div class="al-msg">${ctx.esc(String(d.message).slice(0, 400))}</div>` : ""}
          <div class="al-time">${ctx.esc(time)}</div>
        </div>`;
      clearInterval(el._rep);
      el._rep = setInterval(() => d.speak && ctx.speak(d.speak), 45000);
    },
    destroy(el) { clearInterval(el._rep); },
  });
})();
