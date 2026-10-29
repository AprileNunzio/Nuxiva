(() => {
  const STATES = new Set(["loading", "playing", "blocked", "error"]);
  const RETRIES = 3;

  const safeSrc = (v) => {
    const s = typeof v === "string" ? v.trim() : "";
    if (!s || s.length > 2000) return "";
    try {
      const u = new URL(s, location.href);
      return u.origin === location.origin && u.pathname.startsWith("/api/tv/") ? `${u.pathname}${u.search}` : "";
    } catch { return ""; }
  };

  const ensure = (src) => window.NuxivaTv ? Promise.resolve() : new Promise((ok, fail) => {
    const s = document.createElement("script");
    s.src = src; s.onload = ok; s.onerror = () => fail(new Error("player"));
    document.head.appendChild(s);
  });

  const stop = (el) => {
    const p = el._tv;
    if (!p) return;
    p.alive = false;
    clearTimeout(p.timer);
    try { p.handle && p.handle.stop(); } catch {}
    const v = p.video;
    if (v) { v.pause(); v.removeAttribute("src"); v.load(); }
    el._tv = null;
  };

  const impl = {
    render(el, raw, ctx) {
      const d = raw && typeof raw === "object" ? raw : {};
      const src = safeSrc(d.src);
      const cur = el._tv;
      if (cur && cur.src === src && cur.alive) {
        cur.ctx = ctx;
        cur.paint();
        return;
      }
      stop(el);
      el.innerHTML = `${ctx.head({ icon: "video", label: ctx.t("label"), title: ctx.str(d.name, 60), chip: ctx.t("state_loading"), live: true })}
        <div class="tv-frame"><video playsinline></video><div class="tv-msg"></div>
          <button type="button" class="tv-unmute" hidden>${ctx.icon("music")}<span></span></button>
          <button type="button" class="tv-retry wk-btn" hidden>${ctx.icon("refresh")}<span></span></button></div>
        ${d.group ? `<div class="wk-sub tv-group">${ctx.icon("list")}${ctx.esc(ctx.str(d.group, 60))}</div>` : ""}`;
      const video = el.querySelector("video"), chip = el.querySelector(".wk-chip"), msg = el.querySelector(".tv-msg");
      const unmute = el.querySelector(".tv-unmute"), retry = el.querySelector(".tv-retry");
      const p = { src, video, ctx, alive: true, handle: null, state: "loading", tries: 0, error: "", timer: 0 };
      p.paint = () => {
        const t = p.ctx.t;
        if (chip) { chip.textContent = STATES.has(p.state) ? t(`state_${p.state}`) : p.state; chip.classList.toggle("bad", p.state === "error"); chip.classList.toggle("live", p.state === "playing" || p.state === "loading"); }
        msg.textContent = !src ? t("no_channel") : p.state === "error" ? t("open_failed", { reason: p.error === "player" ? t("player_missing") : p.error }) : p.state === "loading" && p.tries ? t("retrying", { n: p.tries, max: RETRIES }) : "";
        unmute.hidden = !(p.state === "blocked" || (p.state === "playing" && video.muted));
        unmute.lastChild.textContent = t("unmute");
        retry.hidden = p.state !== "error";
        retry.lastChild.textContent = t("retry");
        el.querySelector(".tv-frame").classList.toggle("loading", p.state === "loading");
      };
      el._tv = p;
      if (!src) { p.state = "error"; p.error = ""; p.paint(); msg.textContent = ctx.t("no_channel"); retry.hidden = true; return; }
      const start = () => {
        if (!p.alive) return;
        p.state = "loading";
        p.paint();
        ensure("/static/shared/tvplayer.js")
          .then(() => window.NuxivaTv.play(video, src, (s) => { if (p.alive) { p.state = s; p.paint(); } }))
          .then((h) => { if (p.alive) { p.handle = h; p.tries = 0; } else h.stop(); })
          .catch((e) => {
            if (!p.alive) return;
            p.error = String(e && e.message || "").slice(0, 160);
            if (p.error !== "player" && p.tries < RETRIES) { p.tries += 1; p.paint(); p.timer = setTimeout(start, 1500 * 2 ** p.tries); return; }
            p.state = "error"; p.paint();
          });
      };
      unmute.onclick = () => { video.muted = false; video.play().then(() => { p.state = "playing"; p.paint(); }).catch(() => {}); };
      retry.onclick = () => { p.tries = 0; try { p.handle && p.handle.stop(); } catch {} p.handle = null; start(); };
      video.onvolumechange = () => p.paint();
      video.onstalled = video.onwaiting = () => { if (p.state === "playing") el.querySelector(".tv-frame").classList.add("buffering"); };
      video.onplaying = () => el.querySelector(".tv-frame").classList.remove("buffering");
      start();
    },
    destroy(el) { stop(el); },
  };
  NuxivaDesk.register("tv_player", impl);
})();
