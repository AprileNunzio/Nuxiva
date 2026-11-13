(() => {
  const LEAD = 0.12;
  const SYNC_EVERY = 45000;
  const SAMPLES = 5;
  const DEFAULT_GAP = 6;
  const reduce = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

  const clock = { skew: 0, best: Infinity, timer: 0, users: 0 };

  async function syncClock() {
    const t0 = performance.now();
    const wall0 = Date.now();
    try {
      const r = await fetch("/api/music/clock", { cache: "no-store" });
      if (!r.ok) return;
      const body = await r.json();
      const rtt = performance.now() - t0;
      const server = Number(body && body.now);
      if (!Number.isFinite(server) || !Number.isFinite(rtt) || rtt > 4000) return;
      const offset = server + rtt / 2000 - (wall0 + rtt / 2) / 1000;
      if (rtt <= clock.best * 1.5 || clock.best === Infinity) {
        clock.skew = clock.skew && clock.best !== Infinity ? clock.skew * 0.5 + offset * 0.5 : offset;
        clock.best = Math.min(clock.best, rtt);
      }
    } catch (_) {}
  }

  function startClock() {
    clock.users += 1;
    if (clock.timer) return;
    clock.best = Infinity;
    let burst = 0;
    const run = async () => { await syncClock(); burst += 1; clock.timer = setTimeout(run, burst < SAMPLES ? 600 : SYNC_EVERY); };
    run();
  }

  function stopClock() {
    clock.users = Math.max(0, clock.users - 1);
    if (!clock.users) { clearTimeout(clock.timer); clock.timer = 0; }
  }

  const serverNow = () => Date.now() / 1000 + clock.skew;
  const songKey = (d) => [d.key, d.title, d.artist].map((x) => String(x ?? "")).join("|");
  const cover = (u) => {
    const s = typeof u === "string" ? u.trim() : "";
    if (!s || s.length > 2000) return "";
    try {
      const url = new URL(s, location.href);
      return url.protocol === "https:" || (url.protocol === "http:" && url.origin === location.origin) ? url.href : "";
    } catch { return ""; }
  };

  function linesOf(d, ctx) {
    const ly = d.lyrics && typeof d.lyrics === "object" ? d.lyrics : {};
    const synced = ctx.arr(ly.synced, 400)
      .filter((l) => l && typeof l === "object" && ctx.num(l.t) !== null)
      .map((l) => ({
        t: ctx.num(l.t), text: ctx.str(l.text, 200),
        words: ctx.arr(l.words, 64).filter((w) => w && ctx.num(w.t) !== null).map((w) => ({ t: ctx.num(w.t), text: ctx.str(w.text, 60) })).sort((a, b) => a.t - b.t),
      }))
      .sort((a, b) => a.t - b.t);
    return { synced, plain: typeof ly.plain === "string" ? ly.plain.slice(0, 8000) : "" };
  }

  function lineHtml(l, i, ctx) {
    if (!l.text) return `<div class="ka-line ka-pause" data-i="${i}"><i></i><i></i><i></i></div>`;
    if (l.words.length) {
      return `<div class="ka-line" data-i="${i}"><span class="ka-words">${l.words.map((w, k) => `<span class="ka-w" data-k="${k}">${ctx.esc(w.text)}</span>`).join(" ")}</span></div>`;
    }
    return `<div class="ka-line" data-i="${i}"><span class="ka-fill">${ctx.esc(l.text)}</span></div>`;
  }

  function stop(el) {
    if (el._kaRaf) cancelAnimationFrame(el._kaRaf);
    el._kaRaf = 0;
    if (el._kaRo) el._kaRo.disconnect();
    el._kaRo = null;
    if (el._kaOn) { el._kaOn = false; stopClock(); }
  }

  function paint(el, d, ctx) {
    const { synced, plain } = linesOf(d, ctx);
    const state = ctx.str(d.lyrics_state, 12);
    const title = ctx.str(d.title, 90), artist = ctx.str(d.artist, 90);
    const art = cover(d.cover);
    const origin = d.lyrics_origin === "lrclib" ? ctx.t("from_lrclib") : d.lyrics_origin === "local" ? ctx.t("from_local") : "";
    const mode = synced.length ? "synced" : plain ? "plain" : state === "loading" ? "loading" : "none";
    el._ka = { synced, mode, cur: -2, shift: 0, dur: ctx.num(d.duration) || 0 };
    const stageHtml = mode === "synced"
      ? `<div class="ka-stage"><div class="ka-track">${synced.map((l, i) => lineHtml(l, i, ctx)).join("")}</div></div>`
      : mode === "plain"
        ? `<div class="ka-stage"><div class="ka-track ka-plain">${ctx.esc(plain)}</div></div>`
        : `<div class="ka-state"><span class="ka-pulse" aria-hidden="true"></span><span>${ctx.esc(ctx.t(mode === "loading" ? "loading" : "no_lyrics"))}</span></div>`;
    el.innerHTML = `${art ? `<div class="ka-art" aria-hidden="true"><img src="${ctx.esc(art)}" alt="" referrerpolicy="no-referrer" decoding="async"></div>` : ""}
      <div class="ka-root ka-${mode}">
        <div class="ka-top"><span class="ka-song"><b>${ctx.esc(title)}</b>${artist ? `<em>${ctx.esc(artist)}</em>` : ""}</span><span class="ka-chip ${mode === "synced" ? "on" : ""}">${ctx.esc(ctx.t(mode === "synced" ? "synced" : "karaoke"))}</span></div>
        ${stageHtml}
        <div class="ka-foot"><span class="ka-next" aria-hidden="true"></span><span class="ka-src">${ctx.esc(origin)}</span><span class="ka-time mono"></span></div>
        <div class="ka-bar" aria-hidden="true"><i></i></div>
      </div>`;
    const img = el.querySelector(".ka-art img");
    if (img) img.addEventListener("error", () => img.parentElement.remove(), { once: true });
    el._kaTrack = el.querySelector(".ka-track");
    el._kaStage = el.querySelector(".ka-stage");
    el._kaLines = el._kaTrack ? [...el._kaTrack.querySelectorAll(".ka-line")] : [];
    if (el._kaStage && typeof ResizeObserver === "function") {
      el._kaRo = new ResizeObserver(() => { if (el._ka) el._ka.cur = -2; });
      el._kaRo.observe(el._kaStage);
    }
  }

  function currentIndex(lines, pos) {
    let lo = 0, hi = lines.length - 1, found = -1;
    while (lo <= hi) {
      const mid = (lo + hi) >> 1;
      if (lines[mid].t - LEAD <= pos) { found = mid; lo = mid + 1; } else hi = mid - 1;
    }
    return found;
  }

  function center(el, st, idx, pos, animate) {
    const stage = el._kaStage, track = el._kaTrack;
    if (!stage || !track) return;
    const nodes = el._kaLines;
    const node = nodes[Math.max(0, idx)];
    if (!node) return;
    const shift = stage.clientHeight / 2 - (node.offsetTop + node.offsetHeight / 2);
    st.shift = shift;
    track.style.transition = animate && !reduce() ? "transform 0.55s cubic-bezier(0.22, 0.8, 0.2, 1)" : "none";
    track.style.transform = `translate3d(0, ${shift.toFixed(1)}px, 0)`;
  }

  function paintWords(node, words, pos) {
    const spans = node.querySelectorAll(".ka-w");
    for (let k = 0; k < spans.length; k++) {
      const w = words[k];
      const end = words[k + 1] ? words[k + 1].t : w.t + 0.6;
      const p = Math.max(0, Math.min(1, (pos - w.t) / Math.max(0.12, end - w.t)));
      spans[k].style.setProperty("--p", `${(p * 100).toFixed(1)}%`);
    }
  }

  function frame(el, ctx) {
    el._kaRaf = requestAnimationFrame(() => frame(el, ctx));
    const d = el._d || {}, st = el._ka;
    if (!st) return;
    const start = ctx.num(d.started_at);
    const pos = start !== null ? serverNow() - start : null;
    const time = el.querySelector(".ka-time"), bar = el.querySelector(".ka-bar i");
    if (time) time.textContent = pos !== null && st.dur > 0 ? `${ctx.mmss(Math.max(0, Math.min(st.dur, pos)))} / ${ctx.mmss(st.dur)}` : "";
    if (bar) bar.style.transform = pos !== null && st.dur > 0 ? `scaleX(${Math.max(0, Math.min(1, pos / st.dur)).toFixed(4)})` : "scaleX(0)";
    if (pos === null) return;
    if (st.mode === "plain" && el._kaTrack && el._kaStage) {
      const overflow = Math.max(0, el._kaTrack.scrollHeight - el._kaStage.clientHeight);
      const k = st.dur > 0 ? Math.max(0, Math.min(1, pos / st.dur)) : 0;
      el._kaTrack.style.transform = `translate3d(0, ${(-overflow * k).toFixed(1)}px, 0)`;
      return;
    }
    if (st.mode !== "synced") return;
    const lines = st.synced;
    const idx = currentIndex(lines, pos);
    if (idx !== st.cur) {
      const first = st.cur === -2;
      el._kaLines.forEach((n, i) => {
        n.classList.toggle("on", i === idx);
        n.classList.toggle("past", i < idx);
        n.classList.toggle("near", i === idx + 1);
      });
      st.cur = idx;
      center(el, st, idx, pos, !first);
    }
    const line = idx >= 0 ? lines[idx] : null;
    const node = idx >= 0 ? el._kaLines[idx] : null;
    if (line && node && line.text) {
      if (line.words.length) paintWords(node, line.words, pos);
      else {
        const next = lines[idx + 1];
        const span = Math.max(0.4, Math.min(20, (next ? next.t : line.t + DEFAULT_GAP) - line.t));
        const fill = node.firstElementChild;
        if (fill) fill.style.setProperty("--p", `${(Math.max(0, Math.min(1, (pos - line.t) / span)) * 100).toFixed(1)}%`);
      }
    }
    const nextLine = lines[idx + 1];
    const wait = nextLine ? nextLine.t - pos : 0;
    const resting = idx < 0 || !line || !line.text || (nextLine && wait > DEFAULT_GAP);
    const hint = el.querySelector(".ka-next");
    if (hint) {
      const text = nextLine && resting && wait > 1.5 ? ctx.t("next_in", { n: Math.ceil(wait) }) : "";
      if (hint.textContent !== text) hint.textContent = text;
    }
  }

  const impl = {
    render(el, d, ctx) {
      stop(el);
      el._d = d && typeof d === "object" ? d : {};
      el._kaKey = songKey(el._d) + "|" + String(el._d.lyrics_state || "") + "|" + String(((el._d.lyrics || {}).synced || []).length);
      paint(el, el._d, ctx);
      el._kaOn = true;
      startClock();
      frame(el, ctx);
    },
    update(el, d, ctx) {
      const data = d && typeof d === "object" ? d : {};
      const key = songKey(data) + "|" + String(data.lyrics_state || "") + "|" + String(((data.lyrics || {}).synced || []).length);
      if (!el._ka || key !== el._kaKey) { impl.render(el, data, ctx); return; }
      el._d = data;
    },
    destroy: stop,
  };
  NuxivaDesk.register("karaoke", impl);
})();
