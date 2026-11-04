(() => {
  const state = (v) => {
    const s = String(v || "");
    if (/fail|error|errore|fallit|fallid|échec|echec|erreur|broken|rott/i.test(s)) return "bad";
    if (/cancel|annullat|annul|skip|saltat|omit/i.test(s)) return "skip";
    if (/running|in corso|progress|ejecuci|en cours|build(ing)?$|deploy(ing)?$/i.test(s)) return "live";
    if (/pending|in attesa|queued|coda|attente|cola|waiting|scheduled/i.test(s)) return "wait";
    if (/success|passed|riuscit|superat|completat|\bok\b|done|green|éxito|exito|réussi|reussi|terminad|termin/i.test(s)) return "ok";
    return "";
  };
  const ICON = { bad: "error", ok: "check", live: "refresh", wait: "clock", skip: "stop", "": "pipeline" };
  const dur = (sec) => {
    const s = Math.max(0, Math.round(sec));
    return s >= 3600 ? `${Math.floor(s / 3600)}h ${Math.floor((s % 3600) / 60)}m` : s >= 60 ? `${Math.floor(s / 60)}m ${s % 60}s` : `${s}s`;
  };

  function fromData(d, ctx) {
    return ctx.arr(d.pipelines ?? d.runs, 12).map((p) => {
      if (!p || typeof p !== "object") return null;
      const name = ctx.pick(p, ["name", "workflow", "title", "job"], 60);
      if (!name) return null;
      const label = ctx.pick(p, ["status", "state", "conclusion"], 30);
      const stages = ctx.arr(p.stages ?? p.jobs, 12).map((s) => (s && typeof s === "object" ? { name: ctx.pick(s, ["name", "title"], 40), st: state(ctx.pick(s, ["status", "state", "conclusion"], 30)) } : null)).filter((s) => s && s.name);
      const started = ctx.stamp(p.started_at ?? p.at);
      const seconds = ctx.num(p.duration);
      return {
        name, label, st: state(label), stages,
        branch: ctx.pick(p, ["branch", "ref"], 40),
        commit: ctx.pick(p, ["commit", "sha"], 40).slice(0, 7),
        author: ctx.pick(p, ["author", "actor"], 40),
        time: seconds !== null && seconds >= 0 ? dur(seconds) : started ? ctx.ago(started) : "",
        progress: ctx.num(p.progress),
      };
    }).filter(Boolean);
  }

  function fromText(d, ctx) {
    return ctx.lines(d.content, 10).map((l) => {
      const p = ctx.pair(l);
      return p ? { name: p[1], label: p[2], st: state(p[2]), stages: [], branch: "", commit: "", author: "", time: "", progress: null } : { name: l, label: "", st: "", stages: [], branch: "", commit: "", author: "", time: "", progress: null };
    });
  }

  NuxivaDesk.register("cicd_tracker", {
    render(el, d, ctx) {
      const data = d && typeof d === "object" ? d : {};
      const structured = fromData(data, ctx);
      const runs = structured.length ? structured : fromText(data, ctx);
      const order = { bad: 0, live: 1, wait: 2, "": 3, ok: 4, skip: 5 };
      runs.sort((a, b) => order[a.st] - order[b.st]);
      const failed = runs.filter((r) => r.st === "bad").length;
      const running = runs.filter((r) => r.st === "live").length;
      const judged = runs.filter((r) => r.st === "ok" || r.st === "bad").length;
      const passed = runs.filter((r) => r.st === "ok").length;
      const rows = runs.map((r) => {
        const meta = [r.branch && `⎇ ${r.branch}`, r.commit, r.author, r.time].filter(Boolean).join(" · ");
        const stages = r.stages.length ? `<span class="ci-stages" aria-label="${ctx.esc(r.stages.map((s) => s.name).join(", "))}">${r.stages.map((s) => `<i class="ci-dot ${s.st || "none"}" title="${ctx.esc(s.name)}"></i>`).join("")}</span>` : "";
        return `<li class="ci-run ci-${r.st || "none"}">
          <span class="ci-ic">${ctx.icon(ICON[r.st])}</span>
          <span class="ci-main"><b>${ctx.esc(r.name)}</b>${meta || stages ? `<small>${stages}${ctx.esc(meta)}</small>` : ""}
          ${r.st === "live" && r.progress !== null ? ctx.bar(r.progress) : ""}</span>
          ${r.label ? `<span class="wk-chip${r.st === "live" ? " live" : r.st === "bad" ? " bad" : r.st === "ok" ? " ok" : r.st === "wait" ? " warn" : ""}">${ctx.esc(r.label.replace(/_/g, " "))}</span>` : ""}
        </li>`;
      }).join("");
      const chip = failed ? ctx.count("failed", failed) : running ? ctx.count("running", running) : judged ? ctx.t("pass_rate", { n: Math.round((passed / judged) * 100) }) : "";
      el.innerHTML = `${ctx.head({ icon: "pipeline", label: ctx.t("label"), chip, live: !failed && running > 0, state: failed ? "bad" : running ? "" : judged ? "ok" : "" })}
        ${rows ? `<ul class="ci-list" role="list">${rows}</ul>` : ctx.empty(ctx.tc("waiting"))}`;
    },
  });
})();
