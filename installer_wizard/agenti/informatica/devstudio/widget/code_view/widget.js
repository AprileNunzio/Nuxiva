(() => {
  const MAX_CHARS = 200000;
  const ALIAS = { js: "javascript", mjs: "javascript", ts: "typescript", py: "python", sh: "bash", shell: "bash", zsh: "bash", yml: "yaml", rs: "rust", rb: "ruby", "c++": "cpp", cs: "csharp", kt: "kotlin", md: "markdown", htm: "html", ps1: "powershell" };
  const EXT = { javascript: "js", typescript: "ts", python: "py", bash: "sh", yaml: "yml", rust: "rs", ruby: "rb", cpp: "cpp", c: "c", csharp: "cs", kotlin: "kt", go: "go", java: "java", php: "php", sql: "sql", html: "html", css: "css", json: "json", markdown: "md", toml: "toml", lua: "lua", swift: "swift", powershell: "ps1", dockerfile: "Dockerfile" };
  const HASH = new Set(["python", "bash", "yaml", "ruby", "toml", "powershell", "dockerfile", "r", "perl", "makefile"]);
  const DASH = new Set(["sql", "lua", "haskell"]);
  const MARKUP = new Set(["html", "xml", "svg", "vue"]);
  const KEYWORDS = new Set(("abstract and as assert async await break case catch class const continue def default defer del delete do elif else enum except export extends false final finally fn for from func function if impl import in instanceof interface is lambda let loop match mod module mut new nil none not null or package pass private protected pub public raise return self static struct super switch this throw throws trait true try type typeof undefined use var void where while with yield "
    + "select insert update from where join left right inner outer on group by order having limit values into set create table drop alter index primary key foreign references not null and or as distinct union").split(" "));

  function lex(src, lang) {
    const parts = ["(\\/\\*[\\s\\S]*?\\*\\/)"];
    if (HASH.has(lang)) parts.push("(#[^\\n]*)"); else parts.push("(\\/\\/[^\\n]*)");
    if (DASH.has(lang)) parts.push("(--[^\\n]*)");
    if (MARKUP.has(lang)) parts.push("(<!--[\\s\\S]*?-->)");
    const re = new RegExp(`${parts.join("|")}|("(?:\\\\.|[^"\\\\\\n])*"|'(?:\\\\.|[^'\\\\\\n])*'|\`(?:\\\\.|[^\`\\\\])*\`)|(\\b\\d[\\d_]*(?:\\.\\d+)?(?:e[+-]?\\d+)?\\b|\\b0x[\\da-f]+\\b)|([A-Za-z_$][\\w$]*)`, "gi");
    const out = [];
    let last = 0, m;
    while ((m = re.exec(src)) !== null) {
      if (m.index > last) out.push(["", src.slice(last, m.index)]);
      const text = m[0];
      const isComment = m.slice(1, parts.length + 1).some(Boolean);
      const word = m[m.length - 1];
      const kind = isComment ? "c" : m[parts.length + 1] ? "s" : m[parts.length + 2] ? "n" : word && KEYWORDS.has(lang === "sql" ? word.toLowerCase() : word) ? "k" : word && src[re.lastIndex] === "(" ? "f" : "";
      out.push([kind, text]);
      last = re.lastIndex;
    }
    if (last < src.length) out.push(["", src.slice(last)]);
    return out;
  }

  function highlight(src, lang, esc) {
    if (src.length > 60000 || lang === "text" || lang === "markdown") return esc(src);
    return lex(src, lang).map(([k, t]) => (k ? `<span class="cv-${k}">${esc(t)}</span>` : esc(t))).join("");
  }

  function stop(el) { clearTimeout(el._cvT); }

  NuxivaDesk.register("code_view", {
    render(el, d, ctx) {
      stop(el);
      const data = d && typeof d === "object" ? d : {};
      const content = (typeof data.content === "string" ? data.content : "").replace(/\r\n?/g, "\n").slice(0, MAX_CHARS).replace(/\n+$/, "");
      const raw = ctx.str(data.language ?? data.lang, 24).toLowerCase();
      const lang = ALIAS[raw] || raw || "text";
      const title = ctx.str(data.title, 120);
      const count = content ? content.split("\n").length : 0;
      const gutter = Array.from({ length: Math.min(count, 5000) }, (_, i) => i + 1).join("\n");
      el.innerHTML = `${ctx.head({ icon: "code", label: raw ? raw : ctx.t("plain_text"), title, chip: count ? ctx.count("lines", count) : "" })}
        ${content ? `<div class="cv-frame"><pre class="cv-gutter" aria-hidden="true">${gutter}</pre><pre class="wk-pre cv-code" tabindex="0"><code>${highlight(content, lang, ctx.esc)}</code></pre></div>
        <div class="wk-actions">
          <button class="wk-btn primary" type="button" data-act="copy">${ctx.esc(ctx.t("copy"))}</button>
          <button class="wk-btn" type="button" data-act="wrap" aria-pressed="false">${ctx.esc(ctx.t("wrap"))}</button>
          <button class="wk-btn" type="button" data-act="save">${ctx.esc(ctx.t("download"))}</button>
        </div>` : ctx.empty(ctx.tc("empty_widget"))}`;
      if (!content) return;
      const frame = el.querySelector(".cv-frame");
      el.querySelector(".wk-actions").addEventListener("click", async (e) => {
        const btn = e.target instanceof Element ? e.target.closest("[data-act]") : null;
        if (!btn) return;
        e.stopPropagation();
        if (btn.dataset.act === "copy") {
          const ok = await ctx.copy(content);
          btn.textContent = ctx.t(ok ? "copied" : "copy_failed");
          clearTimeout(el._cvT);
          el._cvT = setTimeout(() => { if (btn.isConnected) btn.textContent = ctx.t("copy"); }, 1600);
        } else if (btn.dataset.act === "wrap") {
          const on = !frame.classList.contains("wrap");
          frame.classList.toggle("wrap", on);
          btn.setAttribute("aria-pressed", String(on));
        } else {
          const base = (title || "codice").normalize("NFKD").replace(/[^\w.-]+/g, "_").replace(/^_+|_+$/g, "").slice(0, 60) || "codice";
          const ext = EXT[lang] || "txt";
          const url = URL.createObjectURL(new Blob([content], { type: "text/plain;charset=utf-8" }));
          const a = document.createElement("a");
          a.href = url;
          a.download = ext === "Dockerfile" ? ext : `${base}.${ext}`;
          a.rel = "noopener";
          document.body.appendChild(a);
          a.click();
          a.remove();
          setTimeout(() => URL.revokeObjectURL(url), 4000);
        }
      });
      const code = el.querySelector(".cv-code"), gut = el.querySelector(".cv-gutter");
      code.addEventListener("scroll", () => { gut.scrollTop = code.scrollTop; }, { passive: true });
    },
    destroy(el) { stop(el); },
  });
})();
