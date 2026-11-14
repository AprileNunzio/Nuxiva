(() => {
  const STATES = ["queued", "running", "retrying", "done", "failed", "cancelled", "expired"];
  const KINDS = ["build", "test", "search", "check"];
  const obj = (v) => (v && typeof v === "object" ? v : {});
  const post = (path) => fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" }).then((r) => r.ok).catch(() => false);

  function rows(d, ctx) {
    return ctx.arr(obj(d).items, 12).map((x) => obj(x)).map((x) => ({
      id: ctx.str(x.id, 128), state: STATES.includes(x.state) ? x.state : "queued",
      kind: KINDS.includes(x.kind) ? x.kind : "other", progress: Math.max(0, Math.min(100, ctx.num(x.progress) ?? 0)),
    })).filter((x) => /^[a-z0-9._:-]+$/.test(x.id));
  }

  NuxivaDesk.register("doing_now", {
    headline(d, ctx) {
      const n = rows(d, ctx).filter((r) => r.state === "running" || r.state === "queued" || r.state === "retrying").length;
      return n ? { text: ctx.count("say_busy", n) } : { text: ctx.t("say_none"), tone: "ok" };
    },
    render(el, d, ctx) {
      const list = rows(d, ctx);
      const live = list.filter((r) => r.state === "running" || r.state === "queued" || r.state === "retrying");
      const body = list.map((r) => `<li class="dn-row dn-${r.state}"><span class="dn-main"><b>${ctx.esc(ctx.t(`kind_${r.kind}`))}</b>${r.state === "running" ? ctx.bar(r.progress, "") : `<small>${ctx.esc(ctx.t(`state_${r.state}`))}</small>`}</span></li>`).join("");
      el.innerHTML = `${ctx.head({ icon: "brain", label: ctx.t("label"), chip: live.length ? ctx.count("active", live.length) : "", live: live.length > 0 })}
        ${body ? `<ul class="dn-list" role="list" aria-live="polite">${body}</ul>` : ctx.empty(ctx.t("say_none"))}
        ${live.length ? `<button type="button" class="wk-btn primary dn-stop" data-a="stop">${ctx.icon("stop")}<span>${ctx.esc(ctx.t("stop"))}</span></button>` : ""}`;
      el.onclick = (e) => {
        const b = e.target.closest("[data-a=stop]");
        if (!b) return;
        e.stopPropagation();
        b.disabled = true;
        Promise.all(live.map((r) => post(`/api/tasks/queue/${encodeURIComponent(r.id)}/cancel`)));
      };
    },
  });
})();
