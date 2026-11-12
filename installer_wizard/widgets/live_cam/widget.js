(() => {
  const ID = /^[\w.-]{1,64}$/;
  const MAX_BACKOFF = 30000;
  const post = (path, body) => fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), credentials: "same-origin" }).catch(() => {});

  function stop(el) {
    const s = el._lc;
    if (!s) return;
    s.dead = true;
    clearTimeout(s.retry);
    clearTimeout(s.flash);
    clearInterval(s.clock);
    document.removeEventListener("visibilitychange", s.onVis);
    if (s.img) { s.img.onload = null; s.img.onerror = null; s.img.removeAttribute("src"); }
    el._lc = null;
  }

  function snapshot(img, name) {
    if (!img.naturalWidth) return false;
    const c = document.createElement("canvas");
    c.width = img.naturalWidth;
    c.height = img.naturalHeight;
    try {
      c.getContext("2d").drawImage(img, 0, 0);
      c.toBlob((blob) => {
        if (!blob) return;
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = `${name.replace(/[^\w.-]+/g, "_").slice(0, 40) || "camera"}_${new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19)}.jpg`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        setTimeout(() => URL.revokeObjectURL(a.href), 2000);
      }, "image/jpeg", 0.92);
      return true;
    } catch { return false; }
  }

  const impl = {
    render(el, d, ctx) {
      stop(el);
      const data = d && typeof d === "object" ? d : {};
      const source = ctx.str(data.source, 64);
      const valid = ID.test(source);
      const name = ctx.str(data.name, 80) || ctx.t("label");
      el.innerHTML = `<div class="lc"><img alt="${ctx.esc(name)}" draggable="false" decoding="async">
        <div class="lc-bar">${ctx.head({ icon: "video", label: ctx.t("label"), title: name, chip: ctx.tc("live"), live: valid, state: "bad" })}
          <button type="button" class="wk-btn icon" data-act="snap" title="${ctx.esc(ctx.t("snapshot"))}" aria-label="${ctx.esc(ctx.t("snapshot"))}">${ctx.icon("camera")}</button><button type="button" class="wk-btn icon" data-act="full" title="${ctx.esc(ctx.t("fullscreen"))}" aria-label="${ctx.esc(ctx.t("fullscreen"))}">${ctx.icon("expand")}</button><button type="button" class="wk-btn icon" data-act="close" title="${ctx.esc(ctx.t("close"))}" aria-label="${ctx.esc(ctx.t("close"))}">${ctx.icon("close")}</button></div>
        <div class="lc-osd"><span class="lc-rec">REC</span><span class="lc-clock mono"></span></div>
        <div class="lc-note" role="status"><span class="lc-spin" aria-hidden="true"></span><span class="lc-msg">${ctx.esc(ctx.t(valid ? "connecting" : "unavailable"))}</span></div>
        <div class="lc-flash" aria-hidden="true"></div></div>`;
      const box = el.querySelector(".lc"), img = el.querySelector("img"), note = el.querySelector(".lc-note"), msg = el.querySelector(".lc-msg"), clock = el.querySelector(".lc-clock");
      const st = { dead: false, retry: 0, clock: 0, flash: 0, fails: 0, img, onVis: null };
      el._lc = st;
      const key = valid ? `live:${source}` : "";
      el.onclick = (e) => {
        const act = e.target.closest("[data-act]");
        if (!act) return;
        e.stopPropagation();
        if (act.dataset.act === "snap") {
          if (snapshot(img, name)) { box.classList.remove("shot"); void box.offsetWidth; box.classList.add("shot"); }
          return;
        }
        if (!key) return;
        if (act.dataset.act === "close") post("/api/desk/close", { key });
        else post("/api/desk/fullscreen", { key, on: !el.closest(".widget")?.classList.contains("fullscreen") });
      };
      const tick = () => { clock.textContent = ctx.when(Date.now(), { hour: "2-digit", minute: "2-digit", second: "2-digit" }); };
      tick();
      st.clock = setInterval(() => { if (!el.isConnected) stop(el); else tick(); }, 1000);
      if (!valid) { box.classList.add("err"); return; }
      const connect = () => {
        if (st.dead || document.hidden) return;
        img.onload = () => { if (st.dead) return; st.fails = 0; note.hidden = true; box.classList.add("on"); box.classList.remove("err"); };
        img.onerror = () => {
          if (st.dead) return;
          st.fails += 1;
          const wait = Math.min(MAX_BACKOFF, 1000 * 2 ** Math.min(st.fails, 5));
          box.classList.remove("on");
          box.classList.toggle("err", st.fails > 2);
          note.hidden = false;
          msg.textContent = ctx.t(st.fails > 2 ? "unavailable_retry" : "reconnecting", { n: Math.round(wait / 1000) });
          clearTimeout(st.retry);
          st.retry = setTimeout(connect, wait);
        };
        img.src = `/api/cameras/live/${encodeURIComponent(source)}.mjpg?t=${Date.now()}`;
      };
      st.onVis = () => {
        if (st.dead) return;
        if (document.hidden) { clearTimeout(st.retry); img.removeAttribute("src"); box.classList.remove("on"); }
        else { note.hidden = false; msg.textContent = ctx.t("connecting"); connect(); }
      };
      document.addEventListener("visibilitychange", st.onVis);
      connect();
    },
    update(el, d, ctx) {
      const s = el._lc, data = d && typeof d === "object" ? d : {};
      if (!s || !s.img || !s.img.src.includes(`/live/${encodeURIComponent(String(data.source || ""))}.`)) impl.render(el, d, ctx);
    },
    destroy: stop,
  };
  NuxivaDesk.register("live_cam", impl);
})();
