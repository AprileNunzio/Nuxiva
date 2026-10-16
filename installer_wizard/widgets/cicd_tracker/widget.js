(() => {
  const state = (v) => {
    if (/fail|error|errore|fallit|cancel|annullat|fallid|échec|echec|erreur|annul/i.test(v)) return "bad";
    if (/running|in corso|pending|in attesa|queued|coda|ejecuci|en cours|attente|cola/i.test(v)) return "live";
    if (/success|passed|riuscit|superat|completat|\bok\b|done|éxito|exito|réussi|reussi|terminad|termin/i.test(v)) return "ok";
    return "";
  };
  NuxivaDesk.register("cicd_tracker", {
    render(el, d, ctx) {
      const lines = ctx.lines(d.content, 10);
      const pairs = lines.map((l) => ctx.pair(l));
      const states = pairs.map((p) => (p ? state(p[2]) : ""));
      const failed = states.filter((s) => s === "bad").length;
      const running = states.filter((s) => s === "live").length;
      const rows = lines.map((l, i) => {
        const p = pairs[i], s = states[i];
        return p
          ? `<li class="wk-row ic${s === "bad" ? " bad" : s === "live" ? " on" : ""}">${ctx.icon(s === "bad" ? "error" : s === "ok" ? "check" : "pipeline")}<span><b>${ctx.esc(p[1])}</b></span><span class="wk-chip${s === "live" ? " live" : s ? ` ${s}` : ""}">${ctx.esc(p[2])}</span></li>`
          : `<li class="wk-row"><span><b>${ctx.esc(l)}</b></span></li>`;
      }).join("");
      const chip = failed ? ctx.count("failed", failed) : running ? ctx.count("running", running) : "";
      el.innerHTML = `${ctx.head({ icon: "pipeline", label: ctx.t("label"), chip, live: !failed && running > 0, state: failed ? "bad" : "" })}
        ${rows ? `<ul class="wk-list">${rows}</ul>` : ctx.empty(ctx.tc("waiting"))}`;
    },
  });
})();
