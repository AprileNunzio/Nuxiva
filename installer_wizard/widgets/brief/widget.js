(() => {
  const safeUrl = (u) => {
    const s = typeof u === "string" ? u.trim() : "";
    if (s.length > 200000) return "";
    return /^(https:\/\/[^\s"'<>\\]+|\/(?!\/)[^\s"'<>\\]*|data:image\/(png|jpe?g|webp|gif|avif);base64,[a-z0-9+/=]+)$/i.test(s) ? s : "";
  };
  const MAX = 10;

  NuxivaDesk.register("brief", {
    render(el, d, ctx) {
      const data = d && typeof d === "object" ? d : {};
      const title = ctx.str(data.title, 80);
      const subtitle = ctx.str(data.subtitle, 160);
      const pic = data.image && typeof data.image === "object" ? data.image : null;
      const src = safeUrl(pic && pic.src);
      const credit = pic ? ctx.str(pic.credit, 120) : "";
      const details = ctx.arr(data.details, MAX);
      const rows = ctx.arr(data.lines, MAX)
        .map((l, i) => ({ text: l && typeof l === "object" ? ctx.pick(l, ["text", "label", "title"], 300) : ctx.str(l, 300), detail: details[i] && typeof details[i] === "object" ? details[i] : null }))
        .filter((r) => r.text);
      const blocks = [];
      for (const r of rows) {
        const p = ctx.pair(r.text, 40);
        const kind = p ? "kv" : "li";
        const last = blocks[blocks.length - 1];
        const item = { ...r, key: p ? p[1].trim() : "", value: p ? p[2].trim() : "" };
        if (last && last.kind === kind) last.items.push(item);
        else blocks.push({ kind, items: [item] });
      }
      const tap = (r) => (r.detail ? ` class="wk-tap"${ctx.detail(r.detail)}` : "");
      const body = blocks.map((b) => (b.kind === "kv"
        ? `<dl class="br-kv">${b.items.map((r) => `<div${tap(r)}><dt>${ctx.esc(r.key)}</dt><dd>${ctx.esc(r.value)}</dd></div>`).join("")}</dl>`
        : `<ul class="br-lines">${b.items.map((r) => `<li${tap(r)}>${ctx.esc(r.text)}</li>`).join("")}</ul>`)).join("");
      const at = ctx.stamp(data.updated_at ?? data.at);
      el.innerHTML = `${ctx.head({ icon: "pin", label: ctx.t("label"), title })}
        ${subtitle ? `<div class="wk-sub br-subtitle">${ctx.esc(subtitle)}</div>` : ""}
        ${src ? `<figure class="br-fig"><img alt="${ctx.esc(title)}" loading="lazy" decoding="async" referrerpolicy="no-referrer" src="${ctx.esc(src)}">${credit ? `<figcaption>${ctx.esc(credit)}</figcaption>` : ""}</figure>` : ""}
        ${body || (src ? "" : ctx.empty(ctx.tc("empty_widget")))}
        ${at ? `<div class="br-meta">${ctx.esc(ctx.ago(at))}</div>` : ""}`;
      const img = el.querySelector(".br-fig img");
      if (img) {
        img.addEventListener("load", () => img.parentElement.classList.add("on"), { once: true });
        img.addEventListener("error", () => img.parentElement.remove(), { once: true });
      }
    },
  });
})();
