(() => {
  const URLISH = /^https?:\/\/[^\s<>"']{3,2000}$/i;
  const SECRET = /^(?=.*\d)(?=.*[a-z])(?=.*[A-Z]|.*[^\w\s])\S{12,128}$/;
  const OTP = /^\d{6,8}$/;
  const CODE = /[{};]\s*$|^\s*(def |class |function |const |let |import |#include|SELECT |<\?php|\$ )/m;
  const REVEAL_MS = 10000;

  const kind = (text, flagged) => {
    if (flagged) return "secret";
    if (URLISH.test(text)) return "link";
    if (!/\s/.test(text) && (SECRET.test(text) || OTP.test(text))) return "secret";
    if (CODE.test(text) && text.includes("\n")) return "code";
    return "text";
  };

  function stop(el) { clearTimeout(el._clipHide); clearTimeout(el._clipCopied); }

  NuxivaDesk.register("clipboard_sync", {
    render(el, d, ctx) {
      stop(el);
      const data = d && typeof d === "object" ? d : {};
      const text = ctx.plain(data.content ?? data.text, 4000).replace(/\r\n?/g, "\n").trim();
      const type = text ? kind(text, data.sensitive === true) : "";
      const source = ctx.pick(data, ["source", "device", "from"], 40);
      const at = ctx.stamp(data.at ?? data.copied_at);
      const words = text ? text.split(/\s+/).filter(Boolean).length : 0;
      const linesN = text ? text.split("\n").length : 0;
      let body = "";
      if (type === "secret") {
        body = `<div class="cb-secret"><span class="cb-mask" aria-label="${ctx.esc(ctx.t("hidden"))}">${"•".repeat(Math.min(16, text.length))}</span><span class="cb-real wk-mono" hidden></span></div>`;
      } else if (type === "link") {
        let host = "";
        try { host = new URL(text).hostname; } catch (_) { host = ""; }
        body = `<div class="cb-link">${ctx.icon("network")}<span><b>${ctx.esc(host || text)}</b><small class="wk-mono">${ctx.esc(text)}</small></span></div>`;
      } else if (text) {
        body = `<pre class="wk-pre cb-text${type === "code" ? " code" : ""}">${ctx.esc(text)}</pre>`;
      }
      const meta = [source && ctx.t("from", { source }), at && ctx.ago(at)].filter(Boolean).join(" · ");
      el.innerHTML = `${ctx.head({ icon: "clipboard", label: ctx.t("label"), chip: text ? (type === "secret" ? ctx.t("kind_secret") : ctx.count("chars", text.length)) : "", state: type === "secret" ? "warn" : "" })}
        ${text ? body : ctx.empty(ctx.t("empty"))}
        ${text ? `<div class="cb-foot"><span class="cb-meta">${ctx.esc([meta, type !== "secret" && words > 1 ? (linesN > 1 ? ctx.t("stats", { w: ctx.fmt(words), l: ctx.fmt(linesN) }) : ctx.t("words", { w: ctx.fmt(words) })) : ""].filter(Boolean).join(" · "))}</span>
          <span class="wk-actions">${type === "secret" ? `<button type="button" class="wk-btn" data-act="reveal">${ctx.esc(ctx.t("reveal"))}</button>` : ""}<button type="button" class="wk-btn primary" data-act="copy">${ctx.esc(ctx.t("copy"))}</button></span></div>` : ""}`;
      if (!text) return;
      el.querySelector(".cb-foot").addEventListener("click", async (e) => {
        const btn = e.target instanceof Element ? e.target.closest("[data-act]") : null;
        if (!btn) return;
        e.stopPropagation();
        if (btn.dataset.act === "copy") {
          const ok = await ctx.copy(text);
          btn.textContent = ctx.t(ok ? "copied" : "copy_failed");
          clearTimeout(el._clipCopied);
          el._clipCopied = setTimeout(() => { if (btn.isConnected) btn.textContent = ctx.t("copy"); }, 1600);
          return;
        }
        const real = el.querySelector(".cb-real"), mask = el.querySelector(".cb-mask");
        const show = real.hidden;
        real.textContent = show ? text : "";
        real.hidden = !show;
        mask.hidden = show;
        btn.textContent = ctx.t(show ? "hide" : "reveal");
        clearTimeout(el._clipHide);
        if (show) el._clipHide = setTimeout(() => { if (!real.isConnected) return; real.textContent = ""; real.hidden = true; mask.hidden = false; btn.textContent = ctx.t("reveal"); }, REVEAL_MS);
      });
    },
    destroy(el) { stop(el); },
  });
})();
