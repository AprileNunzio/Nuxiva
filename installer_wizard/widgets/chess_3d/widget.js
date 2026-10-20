(() => {
  const instances = new WeakMap();

  NuxivaDesk.register("chess_3d", {
    render(el, d, ctx) {
      if (instances.has(el)) return;
      instances.set(el, true);

      const headHtml = ctx.head({
        icon: "layout-grid",
        label: ctx.t("label"),
        title: ctx.t("status_playing"),
        chip: ctx.t("status_ready"),
        live: true
      });

      const frameUrl = (d && d.url) || "/giochi/scacchi-3d/index.html";

      el.innerHTML = `
        ${headHtml}
        <div class="chess-widget">
          <div class="chess-widget-bar">
            <div class="chess-widget-badge">
              <span class="chess-dot-indicator"></span>
              <span class="chess-status-text">${ctx.t("turn_white")}</span>
            </div>
            <div class="chess-widget-actions">
              <button type="button" class="chess-widget-btn chess-btn-hint">${ctx.t("action_hint")}</button>
              <button type="button" class="chess-widget-btn chess-btn-restart">${ctx.t("action_restart")}</button>
              <button type="button" class="chess-widget-btn chess-btn-close">${ctx.t("action_close")}</button>
            </div>
          </div>
          <div class="chess-widget-viewport">
            <iframe src="${frameUrl}" allow="autoplay; fullscreen" loading="lazy"></iframe>
          </div>
        </div>
      `;

      const closeBtn = el.querySelector(".chess-btn-close");
      if (closeBtn) {
        closeBtn.addEventListener("click", () => {
          fetch("/api/desk/close", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ key: "chess_3d" })
          }).catch(() => {});
        });
      }

      const restartBtn = el.querySelector(".chess-btn-restart");
      if (restartBtn) {
        restartBtn.addEventListener("click", () => {
          const iframe = el.querySelector("iframe");
          if (iframe) iframe.src = frameUrl + "?r=" + Date.now();
        });
      }

      const hintBtn = el.querySelector(".chess-btn-hint");
      if (hintBtn) {
        hintBtn.addEventListener("click", () => {
          fetch("/api/assistant/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: "Nuxiva, che mossa mi consigli a scacchi?" })
          }).catch(() => {});
        });
      }
    }
  });
})();
