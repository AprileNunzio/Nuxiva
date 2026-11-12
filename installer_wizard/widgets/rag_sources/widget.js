(() => {
  const KIND = [[/\.pdf$/i, "file", "PDF"], [/\.(md|txt|rst|log)$/i, "text", "TXT"], [/\.(docx?|odt|rtf)$/i, "doc", "DOC"], [/\.(xlsx?|ods|csv)$/i, "chart", "XLS"], [/\.(png|jpe?g|webp|gif|svg)$/i, "image", "IMG"], [/\.(py|js|ts|rs|go|java|c|cpp|h|json|ya?ml|toml)$/i, "code", "CODE"], [/^https?:\/\//i, "network", "WEB"]];

  const score = (v, ctx) => {
    const n = ctx.num(typeof v === "string" ? v.replace("%", "") : v);
    if (n === null || !Number.isFinite(n)) return null;
    return Math.max(0, Math.min(100, n <= 1 && !String(v).includes("%") ? n * 100 : n));
  };

  const parse = (d, ctx) => {
    const raw = Array.isArray(d.sources) ? d.sources : Array.isArray(d.items) ? d.items : Array.isArray(d.documents) ? d.documents : [];
    const rows = [];
    for (const s of raw.slice(0, 60)) {
      const o = typeof s === "string" ? { name: s } : s && typeof s === "object" ? s : null;
      if (!o) continue;
      const name = ctx.str(o.name ?? o.title ?? o.file ?? o.source ?? o.path ?? o.url, 160);
      if (!name) continue;
      const where = ctx.str(o.path ?? o.url ?? name, 300);
      const base = name.split(/[\\/]/).pop() || name;
      const kind = KIND.find(([re]) => re.test(where) || re.test(name)) || [null, "book", ""];
      let host = "";
      if (/^https?:\/\//i.test(where)) { try { host = new URL(where).hostname; } catch { host = ""; } }
      const page = ctx.str(o.page ?? o.pages ?? o.section ?? o.chunk ?? "", 30);
      rows.push({ name: base, folder: !host && /[\\/]/.test(where) ? where.replace(/[\\/][^\\/]*$/, "").slice(-60) : "", host, icon: kind[1], tag: kind[2],
        rel: score(o.relevance ?? o.score ?? o.similarity ?? o.confidence, ctx), page, snippet: ctx.str(o.snippet ?? o.excerpt ?? o.text ?? o.content ?? o.quote ?? "", 600) });
    }
    const scored = rows.some((r) => r.rel !== null);
    if (scored) rows.sort((a, b) => (b.rel ?? -1) - (a.rel ?? -1));
    return { rows, scored };
  };

  const impl = {
    render(el, raw, ctx) {
      const d = raw && typeof raw === "object" ? raw : {};
      const { rows, scored } = parse(d, ctx);
      const query = ctx.str(d.query ?? d.question, 140);
      const open = el._rag && el._rag.q === query ? el._rag.open : 0;
      el._rag = { q: query, open };
      const head = ctx.head({ icon: "book", label: ctx.t("label"), title: query ? `«${query}»` : "", chip: rows.length ? ctx.count("n", rows.length) : "" });
      if (!rows.length) { el.innerHTML = `${head}${ctx.empty(ctx.tc("waiting"))}`; return; }
      const best = rows[0].rel;
      const level = (v) => v === null ? "" : v >= 75 ? "hi" : v >= 45 ? "mid" : "lo";
      const shown = rows.slice(0, 8);
      el.innerHTML = `${head}
        ${scored && best !== null ? `<div class="rg-sum"><span>${ctx.esc(ctx.t(best >= 75 ? "strong" : best >= 45 ? "fair" : "weak"))}</span></div>` : ""}
        <ol class="rg-list">${shown.map((r, i) => `<li class="rg-row ${level(r.rel)}${r.snippet ? " has" : ""}${open === i + 1 ? " open" : ""}"${r.snippet ? ` data-i="${i + 1}" role="button" tabindex="0" aria-expanded="${open === i + 1}"` : ""}>
          <span class="rg-rank mono">${i + 1}</span>
          <span class="rg-ic">${ctx.icon(r.icon)}</span>
          <span class="rg-body"><b title="${ctx.esc(r.name)}">${ctx.esc(r.name)}</b>
            <small>${[r.tag, r.host, r.folder, r.page ? ctx.t("page", { p: r.page }) : ""].filter(Boolean).map(ctx.esc).join(" · ")}</small>
            ${r.rel !== null ? ctx.bar(r.rel, r.rel < 45 ? "warn" : "") : ""}
            ${r.snippet ? `<q class="rg-snip">${ctx.esc(r.snippet)}</q>` : ""}</span>
          ${r.rel !== null ? `<span class="rg-val mono">${Math.round(r.rel)}<small>%</small></span>` : ""}</li>`).join("")}</ol>
        ${rows.length > shown.length ? `<div class="wk-faint rg-more">${ctx.esc(ctx.t("more", { n: rows.length - shown.length }))}</div>` : ""}`;
      const toggle = (li) => { const i = Number(li.dataset.i); el._rag.open = el._rag.open === i ? 0 : i; impl.render(el, raw, ctx); };
      el.onclick = (e) => { const li = e.target.closest(".rg-row[data-i]"); if (li) toggle(li); };
      el.onkeydown = (e) => { const li = e.target.closest(".rg-row[data-i]"); if (li && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); toggle(li); } };
    },
    destroy(el) { el.onclick = null; el.onkeydown = null; },
  };
  NuxivaDesk.register("rag_sources", impl);
})();
