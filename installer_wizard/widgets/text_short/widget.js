(() => {
  const KEEP = new Set(["B", "STRONG", "I", "EM", "U", "S", "MARK", "SMALL", "SUB", "SUP", "CODE", "BR", "P", "UL", "OL", "LI", "BLOCKQUOTE", "H1", "H2", "H3", "H4", "PRE", "SPAN", "DIV", "HR", "TABLE", "THEAD", "TBODY", "TR", "TH", "TD", "DL", "DT", "DD"]);
  const DROP = new Set(["SCRIPT", "STYLE", "TEMPLATE", "IFRAME", "OBJECT", "EMBED", "SVG", "MATH", "NOSCRIPT", "TITLE", "HEAD", "FORM", "INPUT", "BUTTON", "SELECT", "TEXTAREA", "LINK", "META", "BASE"]);
  const HTML = /<\/?(?:p|br|b|strong|i|em|ul|ol|li|h[1-6]|div|span|code|pre|blockquote|table|tr|td|th|mark|u|s|hr)\b[^>]*>/i;

  const copy = (src, dst, depth) => {
    for (const n of src.childNodes) {
      if (n.nodeType === Node.TEXT_NODE) { dst.append(document.createTextNode(n.nodeValue)); continue; }
      if (n.nodeType !== Node.ELEMENT_NODE || DROP.has(n.tagName)) continue;
      if (depth > 12) { dst.append(document.createTextNode(n.textContent)); continue; }
      if (KEEP.has(n.tagName)) {
        const e = document.createElement(n.tagName === "H1" || n.tagName === "H2" ? "h3" : n.tagName.toLowerCase());
        copy(n, e, depth + 1);
        dst.append(e);
      } else copy(n, dst, depth + 1);
    }
  };

  const inline = (dst, text) => {
    const re = /(`[^`\n]+`|\*\*[^*\n]+\*\*|__[^_\n]+__|\*[^*\s][^*\n]*\*|_[^_\s][^_\n]*_|~~[^~\n]+~~|\[[^\]\n]+\]\((?:[^()\s]|\([^()\s]*\))+\))/g;
    let last = 0, m;
    while ((m = re.exec(text))) {
      if (m.index > last) dst.append(text.slice(last, m.index));
      const t = m[0];
      const [tag, inner] = t.startsWith("`") ? ["code", t.slice(1, -1)] : t.startsWith("**") || t.startsWith("__") ? ["strong", t.slice(2, -2)] : t.startsWith("~~") ? ["s", t.slice(2, -2)] : t.startsWith("[") ? ["u", t.slice(1, t.indexOf("]"))] : ["em", t.slice(1, -1)];
      const e = document.createElement(tag);
      if (tag === "code") e.textContent = inner; else inline(e, inner);
      dst.append(e);
      last = m.index + t.length;
    }
    if (last < text.length) dst.append(text.slice(last));
  };

  const markdown = (dst, src) => {
    const lines = src.replace(/\r\n?/g, "\n").split("\n");
    let list = null, para = null, quote = null, fence = null;
    const close = () => { list = null; para = null; quote = null; };
    for (const line of lines) {
      if (fence) {
        if (/^\s*```/.test(line)) { fence = null; continue; }
        fence.textContent += (fence.textContent ? "\n" : "") + line;
        continue;
      }
      if (/^\s*```/.test(line)) { close(); fence = document.createElement("pre"); dst.append(fence); continue; }
      if (!line.trim()) { close(); continue; }
      const h = line.match(/^\s*(#{1,4})\s+(.*)$/);
      if (h) { close(); const e = document.createElement(h[1].length <= 2 ? "h3" : "h4"); inline(e, h[2]); dst.append(e); continue; }
      if (/^\s*([-*_])(\s*\1){2,}\s*$/.test(line)) { close(); dst.append(document.createElement("hr")); continue; }
      const li = line.match(/^\s*(?:([-*+•])|(\d{1,3})[.)])\s+(.*)$/);
      if (li) {
        const kind = li[2] ? "ol" : "ul";
        if (!list || list.tagName.toLowerCase() !== kind) { para = null; quote = null; list = document.createElement(kind); dst.append(list); }
        const e = document.createElement("li");
        inline(e, li[3]);
        list.append(e);
        continue;
      }
      const q = line.match(/^\s*>\s?(.*)$/);
      if (q) {
        if (!quote) { list = null; para = null; quote = document.createElement("blockquote"); dst.append(quote); } else quote.append(document.createElement("br"));
        inline(quote, q[1]);
        continue;
      }
      if (!para) { list = null; quote = null; para = document.createElement("p"); dst.append(para); } else para.append(document.createElement("br"));
      inline(para, line.trim());
    }
  };

  const fill = (target, raw, limit) => {
    const text = String(raw).slice(0, limit);
    if (HTML.test(text)) copy(new DOMParser().parseFromString(text, "text/html").body, target, 0);
    else markdown(target, text);
  };

  NuxivaDesk.register("text_short", {
    render(el, raw, ctx) {
      const d = raw && typeof raw === "object" ? raw : { content: raw };
      const content = typeof d.content === "string" ? d.content : typeof d.text === "string" ? d.text : "";
      const title = ctx.str(d.title, 60);
      el.innerHTML = `${title ? ctx.head({ icon: "chat", label: ctx.t("label"), title }) : ""}<div class="wk-text tx-short"></div>`;
      const box = el.querySelector(".tx-short");
      if (!content.trim()) { box.classList.add("tx-empty"); box.textContent = ctx.tc("waiting"); return; }
      fill(box, content, 6000);
      const len = box.textContent.trim().length;
      box.classList.toggle("tx-hero", len > 0 && len <= 60 && !box.querySelector("ul, ol, pre, table, h3, h4"));
    },
  });
})();
