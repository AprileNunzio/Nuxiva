(() => {
  function fallback(text, done) {
    const area = document.createElement("textarea");
    area.value = text;
    area.style.position = "fixed";
    area.style.opacity = "0";
    document.body.appendChild(area);
    area.select();
    try { document.execCommand("copy"); done(); } catch (err) { console.warn(err); }
    area.remove();
  }

  function copy(text, button, ctx) {
    const done = () => { button.textContent = ctx.t("copied"); setTimeout(() => { button.textContent = ctx.t("copy"); }, 1500); };
    if (navigator.clipboard && window.isSecureContext) return navigator.clipboard.writeText(text).then(done).catch(() => fallback(text, done));
    fallback(text, done);
  }

  NuxivaDesk.register("code_view", {
    render(el, d, ctx) {
      const content = String(d.content || "");
      el.innerHTML = `${ctx.head({ icon: "code", label: String(d.language || ctx.t("plain_text")).slice(0, 24), title: String(d.title || "").slice(0, 120), chip: ctx.count("lines", content.split("\n").length) })}
        <pre class="wk-pre cv-code"><code>${ctx.esc(content)}</code></pre>
        <div class="wk-actions"><button class="wk-btn primary cv-copy" type="button">${ctx.esc(ctx.t("copy"))}</button></div>`;
      el.querySelector(".cv-copy").addEventListener("click", (e) => { e.stopPropagation(); copy(content, e.currentTarget, ctx); });
    },
  });
})();
