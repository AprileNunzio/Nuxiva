(() => {
  const ID = /^[0-9a-f]{8}$/;
  const SLOW_MS = 25000;
  const src = (id) => `/diorama-stage?id=${encodeURIComponent(id)}`;

  function stop(el) {
    const s = el._dio;
    if (!s) return;
    s.abort.abort();
    clearTimeout(s.slow);
    el._dio = null;
  }

  function mount(el, id, ctx) {
    stop(el);
    const st = { id, abort: new AbortController(), slow: 0 };
    el._dio = st;
    el.innerHTML = `<div class="dio-wrap">
        <iframe class="diorama-frame" allow="fullscreen" referrerpolicy="same-origin" title="${ctx.esc(ctx.t("title"))}"></iframe>
        <div class="dio-veil" role="status" aria-live="polite">
          <span class="dio-orb" aria-hidden="true"><i></i><i></i><i></i></span>
          <b class="dio-name">${ctx.esc(ctx.t("title"))}</b>
          <span class="dio-msg">${ctx.esc(ctx.t("loading"))}</span>
          <button type="button" class="wk-btn primary dio-retry" hidden>${ctx.esc(ctx.t("retry"))}</button>
        </div>
      </div>`;
    const frame = el.querySelector("iframe");
    const veil = el.querySelector(".dio-veil");
    const msg = el.querySelector(".dio-msg");
    const retry = el.querySelector(".dio-retry");
    const fail = (key) => { veil.classList.remove("gone"); veil.classList.add("err"); msg.textContent = ctx.t(key); retry.hidden = key === "missing"; };
    retry.addEventListener("click", (e) => { e.stopPropagation(); mount(el, id, ctx); }, { signal: st.abort.signal });
    frame.addEventListener("load", () => {
      if (!frame.getAttribute("src")) return;
      clearTimeout(st.slow);
      veil.classList.add("gone");
    }, { signal: st.abort.signal });
    fetch(`/api/diorama/${encodeURIComponent(id)}/display`, { credentials: "same-origin", cache: "no-store", headers: { "X-Nuxiva-Request": "1" }, signal: st.abort.signal })
      .then(async (r) => {
        if (r.status === 404) { fail("missing"); return; }
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const data = await r.json().catch(() => ({}));
        const title = data && typeof data.title === "string" ? data.title.trim().slice(0, 80) : "";
        if (title) { el.querySelector(".dio-name").textContent = title; frame.title = title; }
        frame.src = src(id);
        st.slow = setTimeout(() => { if (!veil.classList.contains("gone")) { msg.textContent = ctx.t("slow"); retry.hidden = false; } }, SLOW_MS);
      })
      .catch((err) => { if (!st.abort.signal.aborted) { console.warn("Diorama non raggiungibile:", err.message); fail("offline"); } });
  }

  NuxivaDesk.register("diorama", {
    render(el, data, ctx) {
      const id = String((data && data.id) || "");
      if (!ID.test(id)) { stop(el); el.innerHTML = ctx.empty(ctx.t("missing")); return; }
      if (el._dio && el._dio.id === id) return;
      mount(el, id, ctx);
    },
    update(el, data, ctx) {
      const id = String((data && data.id) || "");
      if (ID.test(id) && (!el._dio || el._dio.id !== id)) mount(el, id, ctx);
    },
    destroy(el) { stop(el); el.replaceChildren(); },
  });
})();
