(() => {
  const ID = /^[\w.-]{1,64}$/;
  const MAX_BACKOFF = 30000;
  let catalog = null;

  async function sources() {
    if (catalog && Date.now() - catalog.at < 60000) return catalog.rows;
    const r = await fetch("/api/cameras/sources", { credentials: "same-origin", cache: "no-store", headers: { "X-Nuxiva-Request": "1" } });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const d = await r.json();
    const rows = Array.isArray(d && d.sources) ? d.sources.filter((s) => s && typeof s.id === "string" && ID.test(s.id)) : [];
    catalog = { at: Date.now(), rows };
    return rows;
  }

  function resolve(rows, wanted) {
    const w = wanted.toLowerCase();
    if (!w) return rows.find((s) => s.main) || rows[0] || null;
    return rows.find((s) => s.id === wanted)
      || rows.find((s) => String(s.name || "").toLowerCase() === w)
      || rows.find((s) => String(s.name || "").toLowerCase().includes(w) || String(s.room || "").toLowerCase().includes(w))
      || null;
  }

  function stop(el) {
    const s = el._cam;
    if (!s) return;
    s.dead = true;
    clearTimeout(s.retry);
    clearInterval(s.clock);
    if (s.img) { s.img.removeAttribute("src"); s.img.onload = null; s.img.onerror = null; }
    el._cam = null;
  }

  NuxivaDesk.register("cam_stream", {
    render(el, d, ctx) {
      stop(el);
      const data = d && typeof d === "object" ? d : {};
      const motion = data.motion_detected === true || data.motion === true;
      const motionAt = ctx.stamp(data.motion_at);
      const wantedId = ctx.str(data.source ?? data.id, 64);
      const wantedName = ctx.str(data.camera ?? data.name, 80);
      el.innerHTML = `${ctx.head({ icon: "camera", label: ctx.t("label"), title: wantedName, chip: ctx.t(motion ? "chip_motion" : "chip_listening"), live: true, state: motion ? "bad" : "" })}
        <div class="wk-media cs-feed${motion ? " cs-motion" : ""}">
          <img alt="" draggable="false" decoding="async">
          <div class="cs-note wk-mono">${ctx.esc(ctx.t("connecting"))}</div>
          <div class="cs-osd"><span class="cs-rec">${ctx.esc(ctx.tc("live"))}</span><span class="cs-clock"></span></div>
          ${motion ? `<div class="cs-alert">${ctx.icon("eye")}<span>${ctx.esc(ctx.t("motion"))}</span></div>` : ""}
        </div>
        <dl class="wk-kv cs-kv">
          <dt>${ctx.esc(ctx.t("source"))}</dt><dd class="cs-name">${ctx.esc(wantedName || "—")}</dd>
          <dt>${ctx.esc(ctx.t("state"))}</dt><dd class="${motion ? "wk-accent" : "wk-faint"}">${ctx.esc(ctx.t(motion ? "motion" : "no_motion"))}${motionAt ? ` · ${ctx.esc(ctx.ago(motionAt))}` : ""}</dd>
        </dl>`;
      const st = { dead: false, retry: 0, clock: 0, fails: 0, img: el.querySelector("img") };
      el._cam = st;
      const note = el.querySelector(".cs-note");
      const clock = el.querySelector(".cs-clock");
      const nameEl = el.querySelector(".cs-name");
      const tick = () => { clock.textContent = ctx.when(Date.now(), { hour: "2-digit", minute: "2-digit", second: "2-digit" }); };
      tick();
      st.clock = setInterval(() => { if (!el.isConnected) stop(el); else tick(); }, 1000);
      const fail = (key) => { note.hidden = false; note.textContent = ctx.t(key); el.querySelector(".cs-feed").classList.remove("on"); };
      const connect = (id) => {
        if (st.dead) return;
        const snap = st.fails >= 3;
        st.img.onload = () => {
          if (st.dead) return;
          note.hidden = true;
          el.querySelector(".cs-feed").classList.add("on");
          if (!snap) st.fails = 0;
          else st.retry = setTimeout(() => connect(id), 2000);
        };
        st.img.onerror = () => {
          if (st.dead) return;
          st.fails += 1;
          fail("reconnecting");
          st.retry = setTimeout(() => connect(id), Math.min(MAX_BACKOFF, 1000 * 2 ** Math.min(st.fails, 5)));
        };
        st.img.src = `/api/cameras/live/${encodeURIComponent(id)}.${snap ? "jpg" : "mjpg"}?t=${Date.now()}`;
      };
      (async () => {
        let id = ID.test(wantedId) ? wantedId : "";
        if (!id && !wantedId) {
          try {
            const found = resolve(await sources(), wantedName);
            if (found) { id = found.id; if (!wantedName) nameEl.textContent = String(found.name || found.id).slice(0, 80); }
          } catch (_) { id = ""; }
        }
        if (st.dead) return;
        if (!id) { fail("no_stream"); return; }
        st.img.alt = wantedName || id;
        connect(id);
      })();
    },
    destroy(el) { stop(el); },
  });
})();
