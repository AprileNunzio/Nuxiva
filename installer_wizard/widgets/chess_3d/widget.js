(() => {
  const instances = new WeakMap();
  const CHANNEL = "nuxiva-chess";
  const HEADERS = { "Content-Type": "application/json", "X-Nuxiva-Request": "1" };
  const FRAME = "/giochi/scacchi-3d/index.html";
  const SAVE_ID = /^[\w-]{1,64}$/;
  const FILES = "abcdefgh";
  const PROMO = { queen: "q", rook: "r", bishop: "b", knight: "n" };
  const HINT_TIMEOUT = 45000;

  function focusSlug() {
    const d = window.NuxivaDisplay;
    const focus = d && d.state && d.state.panel && d.state.panel.focus;
    return focus && /^[a-z0-9][a-z0-9_-]{0,63}$/.test(focus.slug || "") ? focus.slug : "";
  }

  function frameUrl(raw) {
    if (typeof raw !== "string") return FRAME;
    try {
      const u = new URL(raw, window.location.origin);
      return u.origin === window.location.origin && u.pathname.startsWith("/giochi/") && !u.pathname.includes("..") ? u.pathname + u.search : FRAME;
    } catch (_) {
      return FRAME;
    }
  }

  function notation(save) {
    const moves = save && Array.isArray(save.moves) ? save.moves.slice(-300) : [];
    const sq = (r, c) => (Number.isInteger(r) && Number.isInteger(c) && r >= 0 && r < 8 && c >= 0 && c < 8 ? `${FILES[c]}${8 - r}` : "");
    return moves.map((m) => (Array.isArray(m) ? `${sq(m[0], m[1])}${sq(m[2], m[3])}${PROMO[m[4]] || ""}` : "")).filter((m) => m.length >= 4);
  }

  function labels(el, ctx) {
    const set = (sel, key) => { const b = el.querySelector(sel); if (b) b.textContent = ctx.t(key); };
    set(".chess-btn-hint", "action_hint");
    set(".chess-btn-restart", "action_restart");
    set(".chess-btn-saved", "action_saved");
  }

  NuxivaDesk.register("chess_3d", {
    render(el, d, ctx) {
      const live = instances.get(el);
      if (live) { live.ctx = ctx; labels(el, ctx); return; }
      const inst = { ctx, abort: new AbortController(), timers: new Set(), last: null, armed: "" };
      instances.set(el, inst);
      const signal = inst.abort.signal;
      const t = (k, p) => inst.ctx.t(k, p);
      const later = (fn, ms) => { const id = setTimeout(() => { inst.timers.delete(id); fn(); }, ms); inst.timers.add(id); return id; };

      const origin = window.location.origin;
      let slug = "";
      let currentId = "new";
      let saving = Promise.resolve();

      el.innerHTML = `
        <div class="chess-widget">
          <div class="chess-widget-bar">
            <button type="button" class="chess-widget-btn chess-btn-hint"></button>
            <button type="button" class="chess-widget-btn chess-btn-restart"></button>
            <button type="button" class="chess-widget-btn chess-btn-saved" aria-expanded="false" aria-controls="chess-saved"></button>
            <span class="chess-widget-turn" aria-live="polite"></span>
            <span class="chess-widget-status" role="status"></span>
          </div>
          <div class="chess-widget-viewport">
            <iframe src="${ctx.esc(frameUrl(d && d.url))}" allow="autoplay; fullscreen" loading="lazy" referrerpolicy="same-origin" title="${ctx.esc(ctx.t("label"))}"></iframe>
            <div class="chess-saved" hidden></div>
          </div>
        </div>`;
      labels(el, ctx);

      const frame = el.querySelector("iframe");
      const panel = el.querySelector(".chess-saved");
      const status = el.querySelector(".chess-widget-status");
      const turnEl = el.querySelector(".chess-widget-turn");
      const savedBtn = el.querySelector(".chess-btn-saved");
      const hintBtn = el.querySelector(".chess-btn-hint");

      const send = (payload) => frame.contentWindow && frame.contentWindow.postMessage({ channel: CHANNEL, ...payload }, origin);
      const note = (key) => {
        status.textContent = key ? t(key) : "";
        status.classList.toggle("bad", key === "save_failed");
        if (key === "autosaved") later(() => { if (status.textContent === t("autosaved")) status.textContent = ""; }, 4000);
      };

      const toast = (text, ms = 12000) => {
        el.querySelectorAll(".chess-toast:not(.chess-resume)").forEach((n) => n.remove());
        const box = document.createElement("div");
        box.className = "chess-toast";
        box.setAttribute("role", "status");
        const span = document.createElement("span");
        span.textContent = String(text).slice(0, 600);
        const close = document.createElement("button");
        close.type = "button";
        close.className = "chess-toast-x";
        close.setAttribute("aria-label", t("action_close"));
        close.textContent = "×";
        close.addEventListener("click", () => box.remove(), { signal });
        box.append(span, close);
        el.querySelector(".chess-widget").appendChild(box);
        later(() => box.remove(), ms);
      };

      const api = async (path, options = {}) => {
        const res = await fetch(`/api/games/chess/${encodeURIComponent(slug)}${path}`, { credentials: "same-origin", ...options, headers: HEADERS, signal });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      };

      const stamp = (ts) => inst.ctx.when(ts, { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });

      const closePanel = () => { panel.hidden = true; savedBtn.setAttribute("aria-expanded", "false"); inst.armed = ""; };

      const resume = async (id) => {
        if (!SAVE_ID.test(id)) return;
        try {
          const row = await api(`/${encodeURIComponent(id)}`);
          currentId = id;
          send({ cmd: "load", save: row.save });
          closePanel();
        } catch (err) {
          if (!signal.aborted) { console.warn("Partita non caricata:", err); note("save_failed"); }
        }
      };

      const drawList = async () => {
        if (!slug) {
          panel.innerHTML = `<p class="chess-saved-empty">${inst.ctx.esc(t("no_person"))}</p>`;
          return;
        }
        panel.innerHTML = `<p class="chess-saved-empty">${inst.ctx.esc(t("loading"))}</p>`;
        try {
          const data = await api("");
          const saves = Array.isArray(data && data.saves) ? data.saves.filter((s) => s && SAVE_ID.test(String(s.id))) : [];
          const esc = inst.ctx.esc;
          panel.innerHTML = saves.length
            ? `<ul>${saves.map((s) => `
                <li data-id="${esc(s.id)}" class="${s.id === currentId ? "current" : ""}">
                  <span class="chess-saved-info"><b>${esc(stamp(s.updated))}</b><small>${esc(t("moves", { n: Number(s.moves) || 0 }))} · ${esc(s.over ? t("finished") : t(s.turn === "white" ? "turn_white" : "turn_black_short"))}</small></span>
                  <button type="button" class="chess-widget-btn" data-act="resume">${esc(t("resume"))}</button>
                  <button type="button" class="chess-widget-btn chess-del" data-act="delete" aria-label="${esc(t("delete"))}">×</button>
                </li>`).join("")}</ul>`
            : `<p class="chess-saved-empty">${esc(t("no_saves"))}</p>`;
        } catch (err) {
          if (signal.aborted) return;
          console.warn("Elenco partite non disponibile:", err);
          panel.innerHTML = `<p class="chess-saved-empty">${inst.ctx.esc(t("save_failed"))}</p>`;
        }
      };

      panel.addEventListener("click", async (event) => {
        const row = event.target.closest("li[data-id]");
        const act = event.target.closest("[data-act]");
        if (!row || !act) return;
        const id = row.dataset.id;
        if (act.dataset.act === "resume") { await resume(id); return; }
        if (inst.armed !== id) {
          inst.armed = id;
          act.textContent = t("confirm_delete");
          act.classList.add("armed");
          later(() => { if (inst.armed === id && act.isConnected) { inst.armed = ""; act.textContent = "×"; act.classList.remove("armed"); } }, 3500);
          return;
        }
        inst.armed = "";
        try {
          await api(`/${encodeURIComponent(id)}`, { method: "DELETE" });
          if (currentId === id) currentId = "new";
        } catch (err) {
          if (!signal.aborted) console.warn("Partita non eliminata:", err);
        }
        drawList();
      }, { signal });

      savedBtn.addEventListener("click", () => {
        slug = focusSlug();
        const open = panel.hidden;
        if (!open) { closePanel(); return; }
        panel.hidden = false;
        savedBtn.setAttribute("aria-expanded", "true");
        drawList();
      }, { signal });

      el.addEventListener("keydown", (e) => { if (e.key === "Escape" && !panel.hidden) { e.stopPropagation(); closePanel(); savedBtn.focus(); } }, { signal });
      document.addEventListener("pointerdown", (e) => {
        if (!panel.hidden && !panel.contains(e.target) && !savedBtn.contains(e.target)) closePanel();
      }, { signal, capture: true });

      el.querySelector(".chess-btn-restart").addEventListener("click", () => {
        currentId = "new";
        inst.last = null;
        send({ cmd: "new" });
        note("");
      }, { signal });

      const showTurn = (m) => {
        if (!m) { turnEl.textContent = ""; return; }
        turnEl.textContent = m.over ? (m.winner ? t(m.winner === "white" ? "won_white" : "won_black") : t("draw")) : t(m.turn === "white" ? "turn_white" : "turn_black");
        turnEl.dataset.side = m.over ? "over" : m.turn === "white" ? "white" : "black";
      };

      const persist = (message) => {
        slug = slug || focusSlug();
        if (!slug || !message.moves) { if (!slug && message.moves) note("not_saved"); return; }
        const body = JSON.stringify({ save: message.save, over: !!message.over, winner: message.winner || null });
        saving = saving.then(async () => {
          if (signal.aborted) return;
          try {
            const row = await api(`/${SAVE_ID.test(currentId) ? encodeURIComponent(currentId) : "new"}`, { method: "PUT", body });
            if (row && SAVE_ID.test(String(row.id))) currentId = String(row.id);
            note("autosaved");
          } catch (err) {
            if (signal.aborted) return;
            console.warn("Salvataggio partita non riuscito:", err);
            note("save_failed");
          }
        });
      };

      const offerResume = async () => {
        slug = focusSlug();
        if (!slug) return;
        try {
          const data = await api("");
          const saves = Array.isArray(data && data.saves) ? data.saves : [];
          const last = saves.find((s) => s && !s.over && s.moves > 0 && SAVE_ID.test(String(s.id)));
          if (!last || signal.aborted) return;
          el.querySelectorAll(".chess-resume").forEach((n) => n.remove());
          const esc = inst.ctx.esc;
          const banner = document.createElement("div");
          banner.className = "chess-toast chess-resume";
          banner.innerHTML = `<span>${esc(t("resume_offer", { n: Number(last.moves) || 0, when: stamp(last.updated) }))}</span>
            <button type="button" class="chess-widget-btn" data-act="yes">${esc(t("resume"))}</button>
            <button type="button" class="chess-widget-btn" data-act="no">${esc(t("new_one"))}</button>`;
          banner.addEventListener("click", (event) => {
            const act = event.target.closest("[data-act]");
            if (!act) return;
            banner.remove();
            if (act.dataset.act === "yes") resume(String(last.id));
          }, { signal });
          el.querySelector(".chess-widget").appendChild(banner);
          later(() => banner.remove(), 30000);
        } catch (err) {
          if (!signal.aborted) console.warn("Partite salvate non disponibili:", err);
        }
      };

      window.addEventListener("message", (event) => {
        if (!el.isConnected || event.origin !== origin || event.source !== frame.contentWindow) return;
        const message = event.data;
        if (!message || typeof message !== "object" || message.channel !== CHANNEL) return;
        if (message.type === "ready") offerResume();
        else if (message.type === "state") { inst.last = message; showTurn(message); persist(message); }
      }, { signal });

      hintBtn.addEventListener("click", async () => {
        if (hintBtn.disabled) return;
        hintBtn.disabled = true;
        hintBtn.classList.add("busy");
        const moves = inst.last ? notation(inst.last.save) : [];
        const text = moves.length
          ? t("hint_question_moves", { moves: moves.join(" "), turn: t(inst.last.turn === "white" ? "side_white" : "side_black") })
          : t("hint_question");
        const timeout = new AbortController();
        const timer = later(() => timeout.abort(), HINT_TIMEOUT);
        const onAbort = () => timeout.abort();
        signal.addEventListener("abort", onAbort, { once: true });
        try {
          const res = await fetch("/api/assistant/chat", { method: "POST", credentials: "same-origin", headers: HEADERS, body: JSON.stringify({ text }), signal: timeout.signal });
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          const data = await res.json();
          if (data && typeof data.reply === "string" && data.reply.trim()) toast(data.reply.trim(), 20000);
        } catch (err) {
          if (!signal.aborted) { console.warn("Suggerimento non riuscito:", err); toast(t("hint_failed"), 6000); }
        } finally {
          clearTimeout(timer);
          inst.timers.delete(timer);
          signal.removeEventListener("abort", onAbort);
          hintBtn.disabled = false;
          hintBtn.classList.remove("busy");
        }
      }, { signal });
    },
    destroy(el) {
      const inst = instances.get(el);
      if (!inst) return;
      inst.abort.abort();
      inst.timers.forEach(clearTimeout);
      inst.timers.clear();
      instances.delete(el);
    },
  });
})();
