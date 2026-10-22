(() => {
  const instances = new WeakMap();

  NuxivaDesk.register("chess_3d", {
    render(el, d, ctx) {
      if (instances.has(el)) return;
      instances.set(el, true);

      const frameUrl = (d && d.url) || "/giochi/scacchi-3d/index.html";

      el.innerHTML = `
        <div class="chess-widget">
          <div class="chess-widget-bar">
            <div class="chess-widget-actions">
              <button type="button" class="chess-widget-btn chess-btn-hint">${ctx.t("action_hint")}</button>
              <button type="button" class="chess-widget-btn chess-btn-restart">${ctx.t("action_restart")}</button>
            </div>
          </div>
          <div class="chess-widget-viewport">
            <iframe src="${frameUrl}" allow="autoplay; fullscreen" loading="lazy"></iframe>
          </div>
        </div>
      `;

      const restartBtn = el.querySelector(".chess-btn-restart");
      if (restartBtn) {
        restartBtn.addEventListener("click", () => {
          const iframe = el.querySelector("iframe");
          if (iframe) iframe.src = frameUrl + "?r=" + Date.now();
        });
      }

      const toast = (text) => {
        const old = el.querySelector(".chess-toast");
        if (old) old.remove();
        const note = document.createElement("div");
        note.className = "chess-toast";
        note.setAttribute("role", "status");
        note.textContent = text;
        el.querySelector(".chess-widget").appendChild(note);
        setTimeout(() => note.remove(), 9000);
      };

      const hintBtn = el.querySelector(".chess-btn-hint");
      if (hintBtn) {
        hintBtn.addEventListener("click", async () => {
          hintBtn.disabled = true;
          try {
            const res = await fetch("/api/assistant/chat", {
              method: "POST",
              headers: { "Content-Type": "application/json", "X-Nuxiva-Request": "1" },
              body: JSON.stringify({ text: ctx.t("hint_question") })
            });
            const data = await res.json();
            if (data && data.reply) toast(data.reply);
          } catch (err) {
            console.warn("Suggerimento non riuscito:", err);
          } finally {
            hintBtn.disabled = false;
          }
        });
      }
    }
  });
})();
