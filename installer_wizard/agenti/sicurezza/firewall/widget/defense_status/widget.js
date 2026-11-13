(() => {
  const POSTURES = new Set(["calm", "watch", "alert", "attack"]);
  const TONE = { calm: "green", watch: "amber", alert: "red", attack: "red" };
  const ICON = { calm: "shield", watch: "shield", alert: "alert", attack: "alert" };

  NuxivaDesk.register("defense_status", {
    render(el, raw, ctx) {
      const d = raw && typeof raw === "object" ? raw : {};
      const posture = POSTURES.has(d.posture) ? d.posture : "calm";
      const observing = d.mode === "off" || d.mode === "monitor";
      const active = ctx.arr(d.defenses, 12).length;
      const hint = observing && posture !== "calm" ? "h_observing" : `h_${posture}`;
      el.dataset.posture = posture;
      el.innerHTML = `${ctx.head({ icon: ICON[posture], label: ctx.t("label"), state: posture === "calm" ? "" : posture === "watch" ? "warn" : "bad", live: posture !== "calm" })}
        <div class="df-state ${TONE[posture]}">
          <strong>${ctx.esc(ctx.t(`p_${posture}`))}</strong>
          <p>${ctx.esc(ctx.t(hint))}</p>
        </div>
        ${active ? `<div class="df-active">${ctx.icon("shield")}<span>${ctx.esc(ctx.count("defending", active))}</span></div>` : ""}`;
    },
  });
})();
