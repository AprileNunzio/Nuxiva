(() => {
  const state = (v) => {
    if (/unhealthy|exited|dead|error|errore|stopped|fermo|detenido|arrêté|arrete|erreur|oomkilled|crash/i.test(v)) return "bad";
    if (/restarting|paused|riavvio|in pausa|starting|reinici|pausado|redémarr|redemarr|en pause|created|creato/i.test(v)) return "warn";
    if (/running|healthy|\bup\b|attivo|in esecuzione|activo|en ejecuci|actif|en cours/i.test(v)) return "ok";
    return "";
  };
  const ORDER = { bad: 0, warn: 1, "": 2, ok: 3 };

  function parse(d, ctx) {
    const list = ctx.arr(d.containers, 40).map((c) => {
      if (!c || typeof c !== "object") return null;
      const name = ctx.pick(c, ["name", "names", "id"], 48).replace(/^\//, "");
      if (!name) return null;
      const status = ctx.pick(c, ["status", "state"], 40);
      const health = ctx.pick(c, ["health"], 20);
      const st = state(health === "unhealthy" ? health : status || health);
      return {
        name, status: health && health !== "none" ? `${status || ""}${status ? " · " : ""}${health}` : status, st,
        image: ctx.pick(c, ["image"], 60).replace(/@sha256:.*/, ""),
        cpu: ctx.num(c.cpu ?? c.cpu_percent), mem: ctx.num(c.mem ?? c.mem_percent ?? c.memory_percent),
        restarts: Math.floor(ctx.num(c.restarts ?? c.restart_count) || 0),
        ports: ctx.pick(c, ["ports"], 60),
      };
    }).filter(Boolean);
    if (list.length) return list;
    return ctx.lines(d.content, 24).map((l) => {
      const p = ctx.pair(l);
      return p ? { name: p[1].trim(), status: p[2].trim(), st: state(p[2]), image: "", cpu: null, mem: null, restarts: 0, ports: "" } : null;
    }).filter(Boolean);
  }

  NuxivaDesk.register("docker_matrix", {
    render(el, d, ctx) {
      const data = d && typeof d === "object" ? d : {};
      const items = parse(data, ctx).sort((a, b) => ORDER[a.st] - ORDER[b.st] || a.name.localeCompare(b.name));
      const notes = items.length ? [] : ctx.lines(data.content, 8);
      const ok = items.filter((i) => i.st === "ok").length;
      const bad = items.filter((i) => i.st === "bad").length;
      const warn = items.filter((i) => i.st === "warn").length;
      const tiles = items.map((i) => {
        const meter = (v, k) => (v === null ? "" : `<span class="dm-m"><em>${ctx.esc(ctx.t(k))}</em>${ctx.bar(v, v >= 90 ? "bad" : v >= 75 ? "warn" : "")}</span>`);
        return `<li class="dm-tile dm-${i.st || "none"}" title="${ctx.esc([i.image, i.ports].filter(Boolean).join(" · "))}">
          <div class="dm-top"><i class="dm-led" aria-hidden="true"></i><b>${ctx.esc(i.name)}</b>${i.restarts > 0 ? `<span class="dm-rs" title="${ctx.esc(ctx.t("restarts"))}">↻${ctx.esc(String(i.restarts))}</span>` : ""}</div>
          <small>${ctx.esc(i.status || "—")}</small>
          ${meter(i.cpu, "cpu")}${meter(i.mem, "ram")}
        </li>`;
      }).join("");
      el.innerHTML = `${ctx.head({ icon: "container", label: ctx.t("label"), chip: items.length ? `${ok}/${items.length}` : "", state: bad ? "bad" : warn ? "warn" : items.length ? "ok" : "" })}
        ${items.length ? `<div class="dm-sum"><span class="ok">${ctx.esc(ctx.t("sum_ok", { n: ok }))}</span>${warn ? `<span class="warn">${ctx.esc(ctx.t("sum_warn", { n: warn }))}</span>` : ""}${bad ? `<span class="bad">${ctx.esc(ctx.t("sum_bad", { n: bad }))}</span>` : ""}</div>
          <ul class="dm-grid">${tiles}</ul>` : notes.length ? `<p class="wk-text">${notes.map(ctx.esc).join("<br>")}</p>` : ctx.empty(ctx.tc("waiting"))}`;
    },
  });
})();
