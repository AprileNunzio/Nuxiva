(() => {
  NuxivaDesk.register("alert_info", {
    render(el, d, ctx) {
      const data = d && typeof d === "object" ? d : {};
      const title = ctx.pick(data, ["title", "message", "text"], 120) || ctx.t("fallback_title");
      const body = ctx.lines(ctx.pick(data, ["content", "detail", "description"], 1200), 8, 1200);
      const items = ctx.arr(data.items, 6).map((i) => (i && typeof i === "object" ? ctx.pick(i, ["label", "title", "name", "text"], 120) : ctx.str(i, 120))).filter(Boolean);
      const source = ctx.pick(data, ["source", "component", "service"], 40);
      const hint = ctx.pick(data, ["hint", "action", "fix"], 200);
      const times = Math.floor(ctx.num(data.count) || 0);
      const at = ctx.stamp(data.at ?? data.time);
      const meta = [source, at ? `${ctx.when(at)} · ${ctx.ago(at)}` : ""].filter(Boolean);
      el.innerHTML = `${ctx.head({ icon: "info", label: ctx.t("label"), chip: times > 1 ? `×${times > 999 ? "999+" : times}` : "", live: false, state: "" })}
        <div class="wk-alert" role="status">
          <div class="wk-title">${ctx.esc(title)}</div>
          ${body.length ? `<div class="wk-sub wk-alert-body">${body.map(ctx.esc).join("<br>")}</div>` : ""}
          ${items.length ? `<ul class="wk-alert-items">${items.map((i) => `<li>${ctx.esc(i)}</li>`).join("")}</ul>` : ""}
          ${hint ? `<div class="wk-alert-hint">${ctx.icon("sparkle")}<span>${ctx.esc(hint)}</span></div>` : ""}
          ${meta.length ? `<div class="wk-alert-meta">${meta.map(ctx.esc).join('<span aria-hidden="true">·</span>')}</div>` : ""}
        </div>`;
    },
  });
})();
