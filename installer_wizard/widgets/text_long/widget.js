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

  const impl = {
    render(el, raw, ctx) {
      const d = raw && typeof raw === "object" ? raw : { content: raw };
      const content = typeof d.content === "string" ? d.content : typeof d.text === "string" ? d.text : "";
      const title = ctx.str(d.title, 80);
      if (!content.trim()) { el.innerHTML = `${title ? ctx.head({ icon: "doc", label: ctx.t("label"), title }) : ""}<div class="wk-text tx-long"><i>${ctx.esc(ctx.t("loading"))}</i></div>`; return; }
      el.innerHTML = `${ctx.head({ icon: "doc", label: ctx.t("label"), title, chip: "" })}
        <div class="tx-wrap"><div class="tx-prog"><i></i></div><div class="wk-text tx-long" tabindex="0"></div><div class="tx-fade"></div></div>
        <div class="tx-foot"><span class="tx-meta"></span><button type="button" class="wk-btn tx-copy">${ctx.icon("copy")}<span>${ctx.esc(ctx.t("copy"))}</span></button></div>`;
      const box = el.querySelector(".tx-long");
      fill(box, content, 60000);
      const words = (box.textContent.match(/\S+/g) || []).length;
      el.querySelector(".tx-meta").textContent = ctx.t("meta", { w: ctx.fmt(words), m: Math.max(1, Math.round(words / 200)) });
      const prog = el.querySelector(".tx-prog i"), fade = el.querySelector(".tx-fade");
      const sync = () => {
        const max = box.scrollHeight - box.clientHeight;
        const over = max > 4;
        el.querySelector(".tx-wrap").classList.toggle("over", over);
        prog.style.width = over ? `${Math.min(100, (box.scrollTop / max) * 100)}%` : "0";
        fade.hidden = !over || box.scrollTop >= max - 4;
      };
      box.onscroll = sync;
      requestAnimationFrame(sync);
      const btn = el.querySelector(".tx-copy");
      btn.onclick = async () => {
        const ok = await ctx.copy(box.innerText);
        btn.lastChild.textContent = ctx.t(ok ? "copied" : "copy_failed");
        btn.classList.toggle("ok", ok);
        clearTimeout(el._txTimer);
        el._txTimer = setTimeout(() => { if (btn.isConnected) { btn.lastChild.textContent = ctx.t("copy"); btn.classList.remove("ok"); } }, 2000);
      };
    },
    destroy(el) { clearTimeout(el._txTimer); },
  };
  NuxivaDesk.register("text_long", impl);
})();
