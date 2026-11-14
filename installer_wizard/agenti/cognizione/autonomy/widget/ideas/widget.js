(() => {
  const KEYS = ["idea_run_checks"];
  const obj = (v) => (v && typeof v === "object" ? v : {});
  const post = (path) => fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" }).then((r) => r.ok).catch(() => false);

  function rows(d, ctx) {
    return ctx.arr(obj(d).items, 6).map((x) => obj(x)).map((x) => ({
      id: Math.trunc(ctx.num(x.id) ?? -1),
      key: KEYS.includes(x.summary_key) ? x.summary_key : "idea_other",
    })).filter((x) => x.id >= 0);
  }

  NuxivaDesk.register("ideas", {
    headline(d, ctx) {
      const n = rows(d, ctx).length;
      return n ? { text: ctx.count("say_some", n) } : { text: ctx.t("say_none"), tone: "ok" };
    },
    render(el, d, ctx) {
      const list = rows(d, ctx);
      const body = list.map((r) => `<li class="id-card" data-id="${r.id}"><span class="id-text">${ctx.esc(ctx.t(r.key))}</span>
        <span class="id-act"><button type="button" class="wk-btn primary" data-a="accept">${ctx.esc(ctx.t("yes"))}</button><button type="button" class="wk-btn" data-a="refuse">${ctx.esc(ctx.t("not_now"))}</button></span></li>`).join("");
      el.innerHTML = `${ctx.head({ icon: "brain", label: ctx.t("label"), chip: list.length ? ctx.count("count", list.length) : "" })}
        ${body ? `<ul class="id-list" role="list">${body}</ul>` : ctx.empty(ctx.t("say_none"))}`;
      el.onclick = (e) => {
        const b = e.target.closest("[data-a]");
        const card = b && b.closest("[data-id]");
        if (!card) return;
        e.stopPropagation();
        b.disabled = true;
        post(`/api/autonomy/ideas/${encodeURIComponent(card.dataset.id)}/${b.dataset.a === "accept" ? "accept" : "refuse"}`).then((ok) => { if (ok) card.remove(); else b.disabled = false; });
      };
    },
  });
})();
