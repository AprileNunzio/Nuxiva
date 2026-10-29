(() => {
  const safe = (u) => {
    const s = typeof u === "string" ? u.trim() : "";
    if (!s || s.length > 2000) return "";
    try {
      const url = new URL(s, location.href);
      return url.protocol === "https:" || (url.protocol === "http:" && url.origin === location.origin) ? url.href : "";
    } catch { return ""; }
  };
  const songKey = (d) => [d.key, d.title, d.artist].map((x) => String(x ?? "")).join("|");

  function stop(el) { clearInterval(el._muT); el._muT = 0; }

  function paint(el, d, ctx) {
    const title = ctx.str(d.title, 120), artist = ctx.str(d.artist, 120);
    if (!title) { el._muKey = ""; el.innerHTML = `${ctx.head({ icon: "music", label: ctx.t("listening") })}${ctx.empty(ctx.t("silence"))}`; return; }
    const cover = safe(d.cover);
    const bio = d.bio && typeof d.bio === "object" ? d.bio : {};
    const text = ctx.str(bio.text, 600), desc = ctx.str(bio.description, 120);
    const meta = [ctx.str(d.album, 60), ctx.str(String(d.year ?? ""), 10), ctx.str(d.genre, 30), ctx.str(d.label, 40)].filter(Boolean);
    const lyrics = d.lyrics && typeof d.lyrics === "object" && (Array.isArray(d.lyrics.synced) && d.lyrics.synced.length || ctx.str(d.lyrics.plain, 10));
    el.innerHTML = `${cover ? `<div class="mu-bg" aria-hidden="true"><img src="${ctx.esc(cover)}" alt="" referrerpolicy="no-referrer" decoding="async"></div>` : ""}
      ${ctx.head({ icon: "music", label: ctx.t("listening"), chip: lyrics ? ctx.t("lyrics") : "", live: true })}
      <div class="mu-row">
        <div class="mu-cover">${cover ? `<img src="${ctx.esc(cover)}" alt="" referrerpolicy="no-referrer" decoding="async">` : ""}<span class="mu-ph">${ctx.icon("music")}</span></div>
        <div class="mu-txt"><div class="wk-title mu-title" title="${ctx.esc(title)}"><span class="mu-eq" aria-hidden="true"><i></i><i></i><i></i><i></i></span>${ctx.esc(title)}</div>
          <div class="wk-accent mu-artist">${ctx.esc(artist)}</div>
          ${meta.length ? `<div class="mu-meta">${meta.map((m) => `<span>${ctx.esc(m)}</span>`).join("")}</div>` : ""}</div>
      </div>
      <div class="mu-prog" hidden><span class="mono mu-pos"></span><span class="wk-bar mu-track"><i></i></span><span class="mono mu-left"></span></div>
      ${text ? `<div class="mu-bio">${desc ? `<b>${ctx.esc(desc)}</b>` : ""}<p>${ctx.esc(text)}</p></div>` : ""}`;
    el.querySelectorAll("img").forEach((img) => {
      img.addEventListener("load", () => img.classList.add("ok"), { once: true });
      img.addEventListener("error", () => { const bg = img.closest(".mu-bg"); if (bg) bg.remove(); else img.remove(); }, { once: true });
    });
    el._muKey = songKey(d);
  }

  function tick(el, ctx) {
    const d = el._muD || {};
    const prog = el.querySelector(".mu-prog");
    if (!prog) return;
    const dur = ctx.num(d.duration), start = ctx.stamp(d.started_at);
    const show = dur > 0 && start !== null;
    prog.hidden = !show;
    const playing = !show || ctx.now() - start < dur;
    el.querySelector(".mu-eq")?.classList.toggle("on", playing);
    if (!show) return;
    const pos = Math.max(0, Math.min(dur, ctx.now() - start));
    prog.querySelector("i").style.width = `${(pos / dur) * 100}%`;
    prog.querySelector(".mu-pos").textContent = ctx.mmss(pos);
    prog.querySelector(".mu-left").textContent = `-${ctx.mmss(dur - pos)}`;
  }

  const impl = {
    render(el, d, ctx) {
      stop(el);
      el._muD = d && typeof d === "object" ? d : {};
      paint(el, el._muD, ctx);
      tick(el, ctx);
      el._muT = setInterval(() => { if (!el.isConnected) stop(el); else tick(el, ctx); }, 1000);
    },
    update(el, d, ctx) {
      const data = d && typeof d === "object" ? d : {};
      if (!el._muT || songKey(data) !== el._muKey) { impl.render(el, data, ctx); return; }
      el._muD = data;
      tick(el, ctx);
    },
    destroy: stop,
  };
  NuxivaDesk.register("music", impl);
})();
