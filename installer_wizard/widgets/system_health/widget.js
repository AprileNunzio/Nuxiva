(() => {
  const ICON = { cpu: "cpu", memory: "memory", disk: "server", temperature: "therm", swap: "memory", gpu: "chip", vram: "chip" };
  const LIMIT = { temperature: [70, 82], disk: [85, 95] };
  const KEEP = 40;

  const spark = (h) => {
    if (h.length < 2) return "";
    const pts = h.map((v, i) => `${((i / (h.length - 1)) * 100).toFixed(1)},${(22 - (v / 100) * 20).toFixed(1)}`);
    return `<svg class="sh-spark" viewBox="0 0 100 24" preserveAspectRatio="none" aria-hidden="true"><polyline points="${pts.join(" ")}"/></svg>`;
  };

  NuxivaDesk.register("system_health", {
    render(el, raw, ctx) {
      const d = raw && typeof raw === "object" ? raw : {};
      const items = ctx.arr(d.items, 8).filter((i) => i && typeof i === "object").map((i) => {
        const id = ctx.str(i.id, 20).toLowerCase();
        const pct = ctx.num(i.percent);
        return { id, label: ICON[id] && ["cpu", "memory", "disk", "temperature"].includes(id) ? ctx.t(`res_${id}`) : ctx.pick(i, ["label", "name", "id"], 40), value: ctx.str(i.value, 20), pct: pct === null ? null : ctx.pct(pct) };
      }).filter((i) => i.label);
      const hist = el._shHist || (el._shHist = {});
      const level = (i) => {
        if (i.pct === null) return "";
        const [warn, bad] = LIMIT[i.id] || [75, 90];
        return i.pct >= bad ? "bad" : i.pct >= warn ? "warn" : "";
      };
      for (const i of items) if (i.pct !== null) { const h = hist[i.id || i.label] || (hist[i.id || i.label] = []); if (h.at(-1) !== i.pct || h.length < 2) h.push(i.pct); if (h.length > KEEP) h.shift(); }
      const worst = items.some((i) => level(i) === "bad") ? "bad" : items.some((i) => level(i) === "warn") ? "warn" : items.length ? "ok" : "";
      el.innerHTML = `${ctx.head({ icon: "gauge", label: ctx.t("label"), title: ctx.t("title"), chip: worst ? ctx.t(`v_${worst}`) : "", state: worst, live: items.length > 0 })}
        ${items.length ? `<ul class="sh-list">${items.map((i) => {
          const s = level(i);
          const h = hist[i.id || i.label] || [];
          const trend = h.length >= 4 ? h.at(-1) - h.at(-4) : 0;
          return `<li class="sh-row${s ? ` ${s}` : ""}"><span class="sh-ic">${ctx.icon(ICON[i.id] || "chip")}</span>
            <span class="sh-main"><span class="sh-top"><b>${ctx.esc(i.label)}</b><span class="sh-val mono">${ctx.esc(i.value || (i.pct === null ? "—" : `${Math.round(i.pct)}%`))}${Math.abs(trend) >= 5 ? `<em class="${trend > 0 ? "up" : "down"}">${trend > 0 ? "▲" : "▼"}</em>` : ""}</span></span>
              ${i.pct !== null ? ctx.bar(i.pct, s) : ""}</span>${spark(h)}</li>`;
        }).join("")}</ul>` : ctx.empty(ctx.t("unavailable"))}`;
    },
  });
})();
