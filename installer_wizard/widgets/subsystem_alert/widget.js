(() => {
  const ICON = { docker: "container", ollama: "brain", llm: "chat", core: "chip", qdrant: "memory", voice: "wave", vision: "eye", ear: "mic", kiosk: "board", disk: "server" };

  NuxivaDesk.register("subsystem_alert", {
    render(el, raw, ctx) {
      const d = raw && typeof raw === "object" ? raw : {};
      const items = ctx.arr(d.items, 12).filter((i) => i && typeof i === "object").map((i) => ({
        key: ctx.str(i.key, 40), label: ctx.pick(i, ["label", "name", "key"], 60), detail: ctx.str(i.detail, 160), since: ctx.stamp(i.since),
        tries: Math.max(0, Math.floor(ctx.num(i.failures ?? i.attempts) || 0)), critical: i.critical === true })).filter((i) => i.label)
        .sort((a, b) => (b.critical - a.critical) || ((a.since ?? Infinity) - (b.since ?? Infinity)));
      const critical = items.filter((i) => i.critical).length;
      const head = ctx.head({ icon: "alert", label: ctx.t("label"), title: items.length ? ctx.t("title") : "", chip: items.length ? ctx.count("faults", items.length) : ctx.t("all_ok"), live: items.length > 0, state: items.length ? "bad" : "ok" });
      if (!items.length) { el.innerHTML = `${head}<div class="sa-ok">${ctx.icon("check")}<span>${ctx.esc(ctx.t("healthy"))}</span></div>`; return; }
      el.innerHTML = `${head}
        <div class="sa-repair"><span class="sa-spin" aria-hidden="true"></span><span>${ctx.esc(ctx.t(critical ? "repair_critical" : "repair"))}</span></div>
        <ul class="sa-list">${items.map((i) => `<li class="sa-row${i.critical ? " crit" : ""}"><span class="sa-ic">${ctx.icon(ICON[i.key] || "error")}</span>
          <span class="sa-txt"><b>${ctx.esc(i.label)}${i.critical ? `<em>${ctx.esc(ctx.t("critical"))}</em>` : ""}</b>${i.detail ? `<small>${ctx.esc(i.detail)}</small>` : ""}</span>
          <span class="sa-meta">${i.since !== null ? `<span>${ctx.esc(ctx.ago(i.since))}</span>` : ""}${i.tries ? `<span class="mono" title="${ctx.esc(ctx.count("tries", i.tries))}">${ctx.icon("refresh")}${i.tries}</span>` : ""}</span></li>`).join("")}</ul>`;
    },
  });
})();
