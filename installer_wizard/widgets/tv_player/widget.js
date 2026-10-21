(() => {
  const players = new WeakMap();
  const STATES = new Set(["loading", "playing", "blocked", "error"]);

  function ensure(src) {
    if (window.NuxivaTv) return Promise.resolve();
    return new Promise((ok, fail) => {
      const s = document.createElement("script");
      s.src = src; s.onload = ok; s.onerror = () => fail(new Error("player"));
      document.head.appendChild(s);
    });
  }

  NuxivaDesk.register("tv_player", {
    render(el, d, ctx) {
      const current = players.get(el);
      if (current && current.src === d.src) return;
      if (current) current.handle && current.handle.stop();
      el.innerHTML = `${ctx.head({ icon: "video", label: ctx.t("label"), title: d.name || "", chip: ctx.t("state_loading"), live: true })}
        <div class="tv-frame"><video playsinline></video><div class="tv-msg"></div></div>
        ${d.group ? `<div class="wk-sub">${ctx.esc(d.group)}</div>` : ""}`;
      const video = el.querySelector("video"), chip = el.querySelector(".wk-chip"), msg = el.querySelector(".tv-msg");
      const entry = { src: d.src, handle: null };
      players.set(el, entry);
      if (!d.src) { msg.textContent = ctx.t("no_channel"); return; }
      ensure("/static/shared/tvplayer.js")
        .then(() => window.NuxivaTv.play(video, d.src, (s) => { if (chip) chip.textContent = STATES.has(s) ? ctx.t(`state_${s}`) : s; }))
        .then((h) => { entry.handle = h; })
        .catch((e) => { msg.textContent = ctx.t("open_failed", { reason: e.message === "player" ? ctx.t("player_missing") : e.message }); });
    },
  });
})();
