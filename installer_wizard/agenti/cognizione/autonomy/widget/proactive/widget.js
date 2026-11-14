(() => {
  const SUMMARIES = ["morning_briefing", "meeting_soon", "window_open_away", "evening_lights", "heart_rate_high", "important_email", "intrusion_alert"];
  const REASONS = ["signal", "habit", "habit_support", "forecast", "window", "conditions", "critical", "learned_up", "learned_down", "low_confidence",
    "muted_by_person", "muted_by_feedback", "privacy_block", "privacy_redact", "quiet_hours", "cost", "cap_global", "cap_person", "level_lowered",
    "auto_approved", "needs_approval", "consent_needed", "mode_speak", "mode_widget"];
  const obj = (v) => (v && typeof v === "object" ? v : {});
  const call = (method, path) => fetch(path, { method, headers: { "Content-Type": "application/json" }, body: method === "POST" ? "{}" : undefined })
    .then((r) => (r.ok ? r.json().catch(() => ({})) : null)).catch(() => null);

  function summary(key) {
    const name = typeof key === "string" ? key.replace(/^proactive\./, "") : "";
    if (name === "redacted") return "s_redacted";
    return SUMMARIES.includes(name) ? `s_${name}` : "s_other";
  }

  function rows(d, ctx) {
    return ctx.arr(obj(d).items, 6).map((x) => obj(x)).map((x) => ({
      id: Math.trunc(ctx.num(x.id) ?? -1), key: summary(x.summary_key), actionable: x.actionable === true,
    })).filter((x) => x.id >= 0);
  }

  function undos(d, ctx) {
    return ctx.arr(obj(d).undo, 6).map((x) => obj(x)).map((x) => ({ id: Math.trunc(ctx.num(x.id) ?? -1), key: summary(x.summary_key) })).filter((x) => x.id >= 0);
  }

  function reasonText(r, ctx) {
    const code = typeof r.code === "string" ? r.code.replace(/^proactive\.why\./, "") : "";
    if (!REASONS.includes(code)) return "";
    const params = obj(r.params);
    return ctx.t(`why_${code}`).replace(/\{(\w+)\}/g, (_m, k) => (/^[a-z0-9._:-]{0,64}$/.test(String(params[k] ?? "")) ? String(params[k] ?? "") : ""));
  }

  NuxivaDesk.register("proactive", {
    headline(d, ctx) {
      const n = rows(d, ctx).length;
      return n ? { text: ctx.count("say_some", n) } : { text: ctx.t("say_none"), tone: "ok" };
    },
    render(el, d, ctx) {
      const list = rows(d, ctx);
      const back = undos(d, ctx);
      const body = list.map((r) => `<li class="pa-card" data-id="${r.id}"><span class="pa-text">${ctx.esc(ctx.t(r.key))}</span>
        <ul class="pa-why" role="list" hidden></ul>
        <span class="pa-act">${r.actionable ? `<button type="button" class="wk-btn primary" data-a="accept">${ctx.esc(ctx.t("yes"))}</button>` : `<button type="button" class="wk-btn primary" data-a="dismiss">${ctx.esc(ctx.t("ok"))}</button>`}
        <button type="button" class="wk-btn" data-a="refuse">${ctx.esc(ctx.t("not_now"))}</button>
        <button type="button" class="wk-btn" data-a="why">${ctx.esc(ctx.t("why"))}</button></span></li>`).join("");
      const undone = back.map((r) => `<li class="pa-card" data-id="${r.id}"><span class="pa-text">${ctx.esc(ctx.t(r.key))}</span>
        <span class="pa-act"><button type="button" class="wk-btn" data-a="undo">${ctx.esc(ctx.t("undo"))}</button></span></li>`).join("");
      el.innerHTML = `${ctx.head({ icon: "brain", label: ctx.t("label"), chip: list.length ? ctx.count("count", list.length) : "" })}
        ${body ? `<ul class="pa-list" role="list">${body}</ul>` : ctx.empty(ctx.t("say_none"))}
        ${undone ? `<p class="pa-sub">${ctx.esc(ctx.t("done_title"))}</p><ul class="pa-list" role="list">${undone}</ul>` : ""}`;
      el.onclick = (e) => {
        const b = e.target.closest("[data-a]");
        const card = b && b.closest("[data-id]");
        if (!card) return;
        e.stopPropagation();
        const id = encodeURIComponent(card.dataset.id);
        const action = b.dataset.a;
        if (action === "why") {
          const box = card.querySelector(".pa-why");
          if (!box.hidden) { box.hidden = true; return; }
          call("GET", `/api/autonomy/proactive/${id}/why`).then((data) => {
            const reasons = ctx.arr(obj(data).reasons, 24).map((r) => reasonText(obj(r), ctx)).filter(Boolean);
            box.innerHTML = reasons.map((t) => `<li>${ctx.esc(t)}</li>`).join("");
            box.hidden = false;
          });
          return;
        }
        if (!["accept", "refuse", "dismiss", "undo"].includes(action)) return;
        b.disabled = true;
        call("POST", `/api/autonomy/proactive/${id}/${action}`).then((ok) => { if (ok) card.remove(); else b.disabled = false; });
      };
    },
  });
})();
