(() => {
  const GAP = 6;

  const cover = (u) => {
    const s = typeof u === "string" ? u.trim() : "";
    if (!s || s.length > 2000) return "";
    try {
      const url = new URL(s, location.href);
      return url.protocol === "https:" || (url.protocol === "http:" && url.origin === location.origin) ? url.href : "";
    } catch { return ""; }
  };

  const songKey = (d) => [d.key, d.title, d.artist].map((x) => String(x ?? "")).join("|");

  function lyricsOf(d, ctx) {
    const ly = d.lyrics && typeof d.lyrics === "object" ? d.lyrics : {};
    const synced = ctx.arr(ly.synced, 400)
      .filter((l) => l && typeof l === "object" && ctx.num(l.t) !== null)
      .map((l) => ({ t: ctx.num(l.t), text: ctx.str(l.text, 200) }))
      .sort((a, b) => a.t - b.t);
    return { synced: synced.length ? synced : null, plain: typeof ly.plain === "string" ? ly.plain.slice(0, 8000) : "" };
  }

  function stop(el) { clearInterval(el._kaT); el._kaT = 0; }

  function paint(el, d, ctx) {
    const { synced, plain } = lyricsOf(d, ctx);
    const title = ctx.str(d.title, 80), artist = ctx.str(d.artist, 80);
    const art = cover(d.cover);
    const head = ctx.head({ icon: "mic", label: ctx.t("label"), title: [title, artist].filter(Boolean).join(" — "), chip: synced ? ctx.t("synced") : "", live: !!synced });
    el._ka = { synced, cur: -2 };
    const back = art ? `<div class="ka-art" aria-hidden="true"><img src="${ctx.esc(art)}" alt="" referrerpolicy="no-referrer" decoding="async"></div>` : "";
    const bar = `<div class="ka-prog" hidden><span class="ka-track"><i></i></span><span class="mono ka-time"></span></div>`;
    if (!synced) {
      el.innerHTML = `${back}<div class="ka-body">${head}${plain ? `<div class="ka-plain" tabindex="0">${ctx.esc(plain)}</div>` : ctx.empty(ctx.t("no_lyrics"))}${bar}</div>`;
    } else {
      el.innerHTML = `${back}<div class="ka-body">${head}<div class="ka-lines" aria-live="off">${synced.map((l, i) => {
        const gap = (synced[i + 1] ? synced[i + 1].t : l.t + GAP) - l.t;
        return `<div class="ka-line${l.text ? "" : " ka-pause"}" data-i="${i}" style="--d:${Math.max(0.3, Math.min(gap, 20)).toFixed(2)}s">${l.text ? `<span class="ka-fill" data-text="${ctx.esc(l.text)}">${ctx.esc(l.text)}</span>` : "<i></i><i></i><i></i>"}</div>`;
      }).join("")}</div>
        <div class="ka-next" aria-hidden="true"></div>${bar}</div>`;
    }
    const img = el.querySelector(".ka-art img");
    if (img) img.addEventListener("error", () => img.parentElement.remove(), { once: true });
  }

  function tick(el, ctx) {
    const d = el._d || {}, st = el._ka;
    if (!st) return;
    const start = ctx.stamp(d.started_at), dur = ctx.num(d.duration);
    const pos = start ? ctx.now() - start : null;
    const prog = el.querySelector(".ka-prog");
    if (prog) {
      const show = pos !== null && dur > 0;
      prog.hidden = !show;
      if (show) {
        const p = Math.max(0, Math.min(dur, pos));
        prog.querySelector("i").style.width = `${(p / dur) * 100}%`;
        prog.querySelector(".ka-time").textContent = `${ctx.mmss(p)} / ${ctx.mmss(dur)}`;
      }
    }
    if (!st.synced || pos === null) return;
    const lines = st.synced;
    let cur = -1;
    for (let i = 0; i < lines.length; i++) { if (lines[i].t <= pos + 0.25) cur = i; else break; }
    const box = el.querySelector(".ka-lines");
    if (!box) return;
    if (cur !== st.cur) {
      const nodes = box.children;
      for (let i = 0; i < nodes.length; i++) {
        nodes[i].classList.toggle("on", i === cur);
        nodes[i].classList.toggle("past", i < cur);
      }
      st.cur = cur;
      const node = nodes[Math.max(0, cur)];
      const fill = cur >= 0 && node ? node.querySelector(".ka-fill") : null;
      if (fill) fill.style.animationDelay = `${-Math.max(0, pos - lines[cur].t).toFixed(2)}s`;
      if (node) {
        const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
        box.scrollTo({ top: Math.max(0, node.offsetTop - box.clientHeight / 2 + node.offsetHeight / 2), behavior: reduce ? "auto" : "smooth" });
      }
    }
    const next = el.querySelector(".ka-next");
    if (next) {
      const upcoming = lines[cur + 1];
      const wait = upcoming ? upcoming.t - pos : 0;
      const idle = cur < 0 || !lines[cur].text || (upcoming && wait > GAP && pos - lines[cur].t > GAP);
      next.textContent = upcoming && idle && wait > 1 ? `${ctx.t("next_in", { n: Math.ceil(wait) })}` : "";
    }
  }

  const impl = {
    render(el, d, ctx) {
      stop(el);
      el._d = d && typeof d === "object" ? d : {};
      el._kaKey = songKey(el._d);
      paint(el, el._d, ctx);
      tick(el, ctx);
      el._kaT = setInterval(() => { if (!el.isConnected) { stop(el); return; } tick(el, ctx); }, 250);
    },
    update(el, d, ctx) {
      const data = d && typeof d === "object" ? d : {};
      if (!el._ka || songKey(data) !== el._kaKey) { impl.render(el, data, ctx); return; }
      el._d = data;
      tick(el, ctx);
    },
    destroy: stop,
  };
  NuxivaDesk.register("karaoke", impl);
})();
