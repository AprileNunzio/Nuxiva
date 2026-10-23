(() => {
  const instances = new WeakMap();
  const CHANNEL = "nuxiva-chess";
  const HEADERS = { "Content-Type": "application/json", "X-Nuxiva-Request": "1" };

  function focusSlug() {
    const d = window.NuxivaDisplay;
    const focus = d && d.state && d.state.panel && d.state.panel.focus;
    return focus && /^[a-z0-9][a-z0-9_-]{0,63}$/.test(focus.slug || "") ? focus.slug : "";
  }

  NuxivaDesk.register("chess_3d", {
    render(el, d, ctx) {
      if (instances.has(el)) return;
      instances.set(el, true);

      const frameUrl = (d && d.url) || "/giochi/scacchi-3d/index.html";
      const origin = window.location.origin;
      let slug = "";
      let currentId = "new";
      let saving = Promise.resolve();

      el.innerHTML = `
        <div class="chess-widget">
          <div class="chess-widget-bar">
            <button type="button" class="chess-widget-btn chess-btn-hint">${ctx.esc(ctx.t("action_hint"))}</button>
            <button type="button" class="chess-widget-btn chess-btn-restart">${ctx.esc(ctx.t("action_restart"))}</button>
            <button type="button" class="chess-widget-btn chess-btn-saved" aria-expanded="false">${ctx.esc(ctx.t("action_saved"))}</button>
            <span class="chess-widget-status" role="status"></span>
          </div>
          <div class="chess-widget-viewport">
            <iframe src="${ctx.esc(frameUrl)}" allow="autoplay; fullscreen" loading="lazy"></iframe>
            <div class="chess-saved" hidden></div>
          </div>
        </div>
      `;

      const frame = el.querySelector("iframe");
      const panel = el.querySelector(".chess-saved");
      const status = el.querySelector(".chess-widget-status");
      const savedBtn = el.querySelector(".chess-btn-saved");

      const send = (payload) => frame.contentWindow && frame.contentWindow.postMessage({ channel: CHANNEL, ...payload }, origin);
      const note = (key) => { status.textContent = key ? ctx.t(key) : ""; };

      const toast = (text) => {
        const old = el.querySelector(".chess-toast");
        if (old) old.remove();
        const box = document.createElement("div");
        box.className = "chess-toast";
        box.setAttribute("role", "status");
        box.textContent = text;
        el.querySelector(".chess-widget").appendChild(box);
        setTimeout(() => box.remove(), 9000);
      };

      const api = async (path, options) => {
        const res = await fetch(`/api/games/chess/${encodeURIComponent(slug)}${path}`, { ...options, headers: HEADERS });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      };

      const when = (ts) => new Date(ts * 1000).toLocaleString(ctx.locale() || undefined, { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });

      const resume = async (id) => {
        try {
          const row = await api(`/${id}`);
          currentId = id;
          send({ cmd: "load", save: row.save });
          panel.hidden = true;
          savedBtn.setAttribute("aria-expanded", "false");
        } catch (err) {
          console.warn("Partita non caricata:", err);
          note("save_failed");
        }
      };

      const drawList = async () => {
        if (!slug) {
          panel.innerHTML = `<p class="chess-saved-empty">${ctx.esc(ctx.t("no_person"))}</p>`;
          return;
        }
        try {
          const { saves } = await api("");
          panel.innerHTML = saves.length
            ? `<ul>${saves.map((s) => `
                <li data-id="${ctx.esc(s.id)}">
                  <span class="chess-saved-info">${ctx.esc(when(s.updated))} · ${ctx.esc(ctx.t("moves", { n: s.moves }))} · ${ctx.esc(s.over ? ctx.t("finished") : ctx.t(s.turn === "white" ? "turn_white" : "turn_black_short"))}</span>
                  <button type="button" class="chess-widget-btn" data-act="resume">${ctx.esc(ctx.t("resume"))}</button>
                  <button type="button" class="chess-widget-btn" data-act="delete" aria-label="${ctx.esc(ctx.t("delete"))}">✕</button>
                </li>`).join("")}</ul>`
            : `<p class="chess-saved-empty">${ctx.esc(ctx.t("no_saves"))}</p>`;
        } catch (err) {
          console.warn("Elenco partite non disponibile:", err);
          panel.innerHTML = `<p class="chess-saved-empty">${ctx.esc(ctx.t("save_failed"))}</p>`;
        }
      };

      panel.addEventListener("click", async (event) => {
        const row = event.target.closest("li[data-id]");
        const act = event.target.closest("[data-act]");
        if (!row || !act) return;
        if (act.dataset.act === "resume") { await resume(row.dataset.id); return; }
        try {
          await api(`/${row.dataset.id}`, { method: "DELETE" });
          if (currentId === row.dataset.id) currentId = "new";
        } catch (err) {
          console.warn("Partita non eliminata:", err);
        }
        drawList();
      });

      savedBtn.addEventListener("click", () => {
        slug = focusSlug();
        const open = panel.hidden;
        panel.hidden = !open;
        savedBtn.setAttribute("aria-expanded", String(open));
        if (open) drawList();
      });

      el.querySelector(".chess-btn-restart").addEventListener("click", () => {
        currentId = "new";
        send({ cmd: "new" });
        note("");
      });

      const persist = (message) => {
        slug = slug || focusSlug();
        if (!slug || !message.moves) { if (!slug && message.moves) note("not_saved"); return; }
        const body = JSON.stringify({ save: message.save, over: !!message.over, winner: message.winner || null });
        saving = saving.then(async () => {
          try {
            const row = await api(`/${currentId}`, { method: "PUT", body });
            currentId = row.id;
            note("autosaved");
          } catch (err) {
            console.warn("Salvataggio partita non riuscito:", err);
            note("save_failed");
          }
        });
      };

      const offerResume = async () => {
        slug = focusSlug();
        if (!slug) return;
        try {
          const { saves } = await api("");
          const last = saves.find((s) => !s.over && s.moves > 0);
          if (!last) return;
          const banner = document.createElement("div");
          banner.className = "chess-toast chess-resume";
          banner.innerHTML = `<span>${ctx.esc(ctx.t("resume_offer", { n: last.moves, when: when(last.updated) }))}</span>
            <button type="button" class="chess-widget-btn" data-act="yes">${ctx.esc(ctx.t("resume"))}</button>
            <button type="button" class="chess-widget-btn" data-act="no">${ctx.esc(ctx.t("new_one"))}</button>`;
          banner.addEventListener("click", (event) => {
            const act = event.target.closest("[data-act]");
            if (!act) return;
            banner.remove();
            if (act.dataset.act === "yes") resume(last.id);
          });
          el.querySelector(".chess-widget").appendChild(banner);
        } catch (err) {
          console.warn("Partite salvate non disponibili:", err);
        }
      };

      window.addEventListener("message", (event) => {
        if (!el.isConnected || event.origin !== origin || event.source !== frame.contentWindow) return;
        const message = event.data;
        if (!message || message.channel !== CHANNEL) return;
        if (message.type === "ready") offerResume();
        else if (message.type === "state") persist(message);
      });

      const hintBtn = el.querySelector(".chess-btn-hint");
      hintBtn.addEventListener("click", async () => {
        hintBtn.disabled = true;
        try {
          const res = await fetch("/api/assistant/chat", {
            method: "POST",
            headers: HEADERS,
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
  });
})();
