(() => {
  const COMMIT = /^([0-9a-f]{6,40})\s+(.*)$/i;
  const CONV = /^(\w+)(?:\(([^)]{1,40})\))?(!)?:\s*(.+)$/;
  const KIND = { feat: ["sparkle", "k_feat"], fix: ["check", "k_fix"], perf: ["bolt", "k_perf"], security: ["shield", "k_sec"], sec: ["shield", "k_sec"], refactor: ["code", "k_other"], docs: ["book", "k_other"], test: ["check", "k_other"], chore: ["refresh", "k_other"], style: ["pen", "k_other"], build: ["cube", "k_other"], ci: ["pipeline", "k_other"] };

  const entry = (line, ctx) => {
    const raw = ctx.str(line, 200);
    const m = raw.match(COMMIT);
    const sha = m ? m[1].slice(0, 7) : "";
    let text = m ? m[2] : raw;
    const c = text.match(CONV);
    const type = c ? c[1].toLowerCase() : "";
    const scope = c ? c[2] || "" : "";
    text = c ? c[4] : text;
    const parts = text.split(" / ");
    if (parts.length === 2) text = ctx.locale().startsWith("it") ? parts[0] : parts[1];
    return { sha, type, scope, breaking: !!(c && c[3]), text: text.trim() };
  };

  NuxivaDesk.register("system_update", {
    render(el, raw, ctx) {
      const d = raw && typeof raw === "object" ? raw : {};
      const changes = ctx.arr(d.changes, 12).map((l) => entry(l, ctx)).filter((e) => e.text);
      const total = Math.max(changes.length, Math.floor(ctx.num(d.count) || 0));
      const local = ctx.str(d.local, 10).slice(0, 7), remote = ctx.str(d.remote, 10).slice(0, 7);
      const window = ctx.str(d.window, 5);
      const checked = ctx.stamp(d.checked);
      const counts = changes.reduce((a, e) => { const k = (KIND[e.type] || [null, "k_other"])[1]; a[k] = (a[k] || 0) + 1; return a; }, {});
      const plan = d.auto === true ? (window ? ctx.t("auto_at", { t: window }) : ctx.t("auto_soon")) : d.auto === false ? ctx.t("manual") : "";
      if (!local && !remote && !changes.length) { el.innerHTML = `${ctx.head({ icon: "download", label: ctx.t("label") })}${ctx.empty(ctx.tc("waiting"))}`; return; }
      el.innerHTML = `${ctx.head({ icon: "download", label: ctx.t("label"), chip: total ? ctx.count("changes", total) : ctx.t("available"), live: true })}
        <div class="su-ver"><span class="mono su-old">${ctx.esc(local || "—")}</span><span class="su-arrow">${ctx.icon("play")}</span><span class="mono su-new">${ctx.esc(remote || "—")}</span>
          <span class="su-ok">${ctx.icon("shield")}${ctx.esc(ctx.t("tested"))}</span></div>
        ${Object.keys(counts).length ? `<div class="su-mix">${["k_feat", "k_fix", "k_perf", "k_sec", "k_other"].filter((k) => counts[k]).map((k) => `<span class="${k}"><b>${counts[k]}</b>${ctx.esc(ctx.t(k))}</span>`).join("")}</div>` : ""}
        ${changes.length ? `<ul class="su-list">${changes.slice(0, 6).map((e) => `<li class="su-row ${(KIND[e.type] || [null, "k_other"])[1]}${e.breaking ? " brk" : ""}"><span class="su-ic">${ctx.icon((KIND[e.type] || ["info"])[0])}</span>
          <span class="su-txt"><b>${ctx.esc(e.text)}</b><small>${[e.scope, e.sha].filter(Boolean).map(ctx.esc).join(" · ")}${e.breaking ? ` <em>${ctx.esc(ctx.t("breaking"))}</em>` : ""}</small></span></li>`).join("")}</ul>
          ${total > 6 ? `<div class="wk-faint su-more">${ctx.esc(ctx.t("more", { n: total - 6 }))}</div>` : ""}` : ""}
        ${plan || checked !== null ? `<div class="su-plan">${ctx.icon(d.auto === false ? "info" : "clock")}<span>${ctx.esc(plan)}${plan && checked !== null ? " · " : ""}${checked !== null ? ctx.esc(ctx.t("checked", { t: ctx.ago(checked) })) : ""}</span></div>` : ""}`;
    },
  });
})();
