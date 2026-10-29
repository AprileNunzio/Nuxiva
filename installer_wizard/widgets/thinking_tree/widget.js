(() => {
  const GLYPH = /^[\s│|]*(?:[├└┣┗+`]\s*[─━-]+\s*|[-*•·]\s+|\d{1,3}[.)]\s+)?/;
  const DONE = /^(?:\[x\]\s*|[✓✔]\s*)|\s[✓✔]$/i;
  const FAIL = /^(?:\[!\]\s*|[✗✘×]\s*)|\s[✗✘]$/;
  const NOW = /^(?:→|->|>|…)\s*|\s(?:…|\.\.\.)$/;
  const ASK = /\?\s*$/;
  const FINAL = /^(?:=>|⇒|conclusion[ei]?|risposta|decisione|answer|decision|respuesta|décision|réponse)\s*[:-]?\s*/i;

  const status = (t) => DONE.test(t) ? "done" : FAIL.test(t) ? "fail" : FINAL.test(t) ? "final" : NOW.test(t) ? "now" : ASK.test(t) ? "ask" : "";
  const clean = (t) => t.replace(DONE, "").replace(FAIL, "").replace(NOW, "").replace(/^\s*\[\s\]\s*/, "").trim();

  const fromText = (text) => {
    const out = [];
    for (const raw of text.split("\n")) {
      if (!raw.trim()) continue;
      const lead = raw.match(GLYPH)[0];
      const indent = lead.replace(/\t/g, "    ").length;
      const body = raw.slice(lead.length).trim();
      if (!body) continue;
      out.push({ indent, text: body });
    }
    const levels = [...new Set(out.map((n) => n.indent))].sort((a, b) => a - b);
    return out.map((n) => ({ depth: Math.min(6, levels.indexOf(n.indent)), state: status(n.text), text: clean(n.text).replace(FINAL, "") || n.text }));
  };

  const fromNodes = (nodes, depth, out, ctx) => {
    for (const n of ctx.arr(nodes, 60)) {
      if (out.length >= 80) return;
      const o = typeof n === "string" ? { text: n } : n && typeof n === "object" ? n : null;
      if (!o) continue;
      const text = ctx.pick(o, ["text", "label", "title", "step"], 240);
      if (text) out.push({ depth: Math.min(6, depth), state: ["done", "fail", "now", "ask", "final"].includes(o.status) ? o.status : status(text), text: clean(text) || text });
      if (Array.isArray(o.children)) fromNodes(o.children, depth + 1, out, ctx);
    }
    return out;
  };

  const ICON = { done: "check", fail: "close", now: "play", ask: "info", final: "star" };

  const impl = {
    render(el, raw, ctx) {
      const d = raw && typeof raw === "object" ? raw : {};
      const rows = (Array.isArray(d.nodes) ? fromNodes(d.nodes, 0, [], ctx) : fromText(ctx.plain(d.content, 12000))).slice(0, 80).map((r) => ({ ...r, text: ctx.str(r.text, 240) }));
      const ui = el._tt || (el._tt = { shut: new Set() });
      const done = rows.filter((r) => r.state === "done").length;
      const failed = rows.filter((r) => r.state === "fail").length;
      const final = rows.find((r) => r.state === "final");
      const thinking = !final && rows.some((r) => r.state === "now");
      const head = ctx.head({ icon: "tree", label: ctx.t("label"), title: ctx.str(d.title ?? d.question, 80), chip: rows.length ? ctx.count("steps", rows.length) : "", live: thinking, state: failed && !final ? "warn" : final ? "ok" : "" });
      if (!rows.length) { el.innerHTML = `${head}${ctx.empty(ctx.tc("waiting"))}`; return; }
      const hidden = new Set();
      rows.forEach((r, i) => { if (ui.shut.has(i)) for (let j = i + 1; j < rows.length && rows[j].depth > r.depth; j++) hidden.add(j); });
      const parent = (i) => i + 1 < rows.length && rows[i + 1].depth > rows[i].depth;
      el.innerHTML = `${head}
        ${done || failed ? `<div class="tt-sum">${done ? `<span class="ok">${ctx.icon("check")}${ctx.esc(ctx.count("verified", done))}</span>` : ""}${failed ? `<span class="bad">${ctx.icon("close")}${ctx.esc(ctx.count("discarded", failed))}</span>` : ""}</div>` : ""}
        <ul class="tt-tree" role="tree">${rows.map((r, i) => hidden.has(i) || r === final ? "" : `<li role="treeitem" class="tt-node d${r.depth}${r.state ? ` ${r.state}` : ""}${parent(i) ? " parent" : ""}${ui.shut.has(i) ? " shut" : ""}" style="--d:${r.depth}"${parent(i) ? ` data-i="${i}" aria-expanded="${!ui.shut.has(i)}" tabindex="0"` : ""}>
          <span class="tt-dot">${ICON[r.state] ? ctx.icon(ICON[r.state]) : ""}</span><span class="tt-txt">${ctx.esc(r.text)}</span>${parent(i) && ui.shut.has(i) ? `<em class="tt-more">+${rows.slice(i + 1).findIndex((x) => x.depth <= r.depth) === -1 ? rows.length - i - 1 : rows.slice(i + 1).findIndex((x) => x.depth <= r.depth)}</em>` : ""}</li>`).join("")}</ul>
        ${final ? `<div class="tt-final">${ctx.icon("star")}<span><small>${ctx.esc(ctx.t("conclusion"))}</small>${ctx.esc(final.text)}</span></div>` : ""}`;
      const toggle = (li) => { const i = Number(li.dataset.i); if (ui.shut.has(i)) ui.shut.delete(i); else ui.shut.add(i); impl.render(el, raw, ctx); };
      el.onclick = (e) => { const li = e.target.closest(".tt-node[data-i]"); if (li) toggle(li); };
      el.onkeydown = (e) => { const li = e.target.closest(".tt-node[data-i]"); if (li && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); toggle(li); } };
    },
    destroy(el) { el.onclick = el.onkeydown = null; },
  };
  NuxivaDesk.register("thinking_tree", impl);
})();
