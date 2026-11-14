(() => {
  const KINDS = ["reminder_time", "notify_channel", "reply_length", "reply_tone", "step_order"];
  const VALUES = ["morning", "afternoon", "evening", "voice", "screen", "short", "long", "warm", "neutral", "formal", "tests_first", "build_first"];
  const obj = (v) => (v && typeof v === "object" ? v : {});
  const post = (path) => fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" }).then((r) => r.ok).catch(() => false);

  function rows(d, ctx) {
    return ctx.arr(obj(d).items, 20).map((x) => obj(x)).map((x) => ({
      id: Math.trunc(ctx.num(x.id) ?? -1),
      kind: KINDS.includes(x.kind) ? x.kind : "other",
      value: VALUES.includes(x.value) ? x.value : "",
      state: x.state === "adopted" ? "adopted" : "candidate",
    })).filter((x) => x.id >= 0 && x.value);
  }

  function phrase(r, ctx) {
    return ctx.t(`lesson_${r.kind}`, { value: ctx.t(`value_${r.value}`) });
  }

  NuxivaDesk.register("learned", {
    headline(d, ctx) {
      const n = rows(d, ctx).length;
      return n ? { text: ctx.count("say_some", n) } : { text: ctx.t("say_none"), tone: "ok" };
    },
    render(el, d, ctx) {
      const list = rows(d, ctx);
      const body = list.map((r) => `<li class="ln-row" data-id="${r.id}"><span class="ln-text">${ctx.esc(phrase(r, ctx))}</span>
        <span class="ln-act"><button type="button" class="wk-btn primary" data-a="keep">${ctx.esc(ctx.t("keep"))}</button><button type="button" class="wk-btn" data-a="forget">${ctx.esc(ctx.t("forget"))}</button></span></li>`).join("");
      el.innerHTML = `${ctx.head({ icon: "brain", label: ctx.t("label"), chip: list.length ? ctx.count("count", list.length) : "" })}
        ${body ? `<ul class="ln-list" role="list">${body}</ul>` : ctx.empty(ctx.t("say_none"))}`;
      el.onclick = (e) => {
        const b = e.target.closest("[data-a]");
        const row = b && b.closest("[data-id]");
        if (!row) return;
        e.stopPropagation();
        b.disabled = true;
        post(`/api/mind/lessons/${encodeURIComponent(row.dataset.id)}/${b.dataset.a === "keep" ? "keep" : "forget"}`).then((ok) => { if (ok) row.remove(); else b.disabled = false; });
      };
    },
  });
})();
