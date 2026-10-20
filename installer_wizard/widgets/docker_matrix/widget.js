(() => {
  const state = (v) => {
    if (/unhealthy|exited|dead|error|errore|stopped|fermo|detenido|arrêté|arrete|erreur/i.test(v)) return "bad";
    if (/restarting|paused|riavvio|in pausa|starting|reinici|pausado|redémarr|redemarr|en pause/i.test(v)) return "warn";
    if (/running|healthy|\bup\b|attivo|in esecuzione|activo|en ejecuci|actif|en cours/i.test(v)) return "ok";
    return "";
  };
  NuxivaDesk.register("docker_matrix", {
    render(el, d, ctx) {
      const lines = ctx.lines(d.content, 12);
      const pairs = lines.map((l) => ctx.pair(l));
      const states = pairs.map((p) => (p ? state(p[2]) : ""));
      const total = pairs.filter(Boolean).length;
      const rows = lines.map((l, i) => {
        const p = pairs[i], s = states[i];
        return p
          ? `<li class="wk-row ic${s && s !== "ok" ? ` ${s}` : ""}">${ctx.icon("container")}<span><b>${ctx.esc(p[1])}</b></span><span class="wk-chip${s ? ` ${s}` : ""}">${ctx.esc(p[2])}</span></li>`
          : `<li class="wk-row"><span><b>${ctx.esc(l)}</b></span></li>`;
      }).join("");
      el.innerHTML = `${ctx.head({ icon: "container", label: ctx.t("label"), chip: total ? `${states.filter((s) => s === "ok").length}/${total}` : "", state: states.includes("bad") ? "bad" : "ok" })}
        ${rows ? `<ul class="wk-list">${rows}</ul>` : ctx.empty(ctx.tc("waiting"))}`;
    },
  });
})();
