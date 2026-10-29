(() => {
  const impls = {}, loading = {}, cards = new Map();
  let host = null, resizeObs = null, lastList = [], allList = [], layoutRaf = 0, lastZone = "", screens = [];
  const hooks = { speak: () => {}, onStage: () => {}, screen: 0, satellite: false, quiet: false, clientId: "", sessionMode: "shared" };
  const EDGE = 28;
  const gov = (id, fn, el, mount) => (window.nuxivaGovernor ? window.nuxivaGovernor.measure(id, fn, el, mount) : fn());

  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  function postPos(id, x, y) {
    fetch("/api/desk/position", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(y === null ? { id, clear: true } : { id, x, y }) }).catch(() => {});
  }
  function neighbor(dir) {
    const i = screens.findIndex((s) => s.n === hooks.screen);
    return i < 0 ? null : screens[i + dir] || null;
  }
  function moveTo(id, n) {
    const card = [...cards.values()].find((c) => c.inst.id === id);
    if (card) card.el.classList.add(n > hooks.screen ? "fly-right" : "fly-left");
    return fetch("/api/desk/screen", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id, screen: n }) }).catch(() => {});
  }
  function edgeDrop(card, x) {
    const W = window.innerWidth, dir = x < EDGE ? -1 : x > W - EDGE ? 1 : 0, target = dir && neighbor(dir);
    if (!target) return false;
    moveTo(card.inst.id, target.n);
    return true;
  }
  function edgeHint(x) {
    const W = window.innerWidth, b = document.body;
    b.classList.toggle("edge-l", x !== null && x < EDGE * 3 && !!neighbor(-1));
    b.classList.toggle("edge-r", x !== null && x > W - EDGE * 3 && !!neighbor(1));
  }
  function enableDrag(card) {
    const el = card.el;
    let sx, sy, ox, oy, moved;
    el.addEventListener("pointerdown", (e) => {
      if (e.button || card.inst.fullscreen || e.target.closest("button, input, select, textarea, a")) return;
      sx = e.clientX; sy = e.clientY; ox = el.offsetLeft; oy = el.offsetTop; moved = false;
      try { el.setPointerCapture(e.pointerId); } catch (err) {}
      const move = (ev) => {
        const dx = ev.clientX - sx, dy = ev.clientY - sy;
        if (!moved && Math.hypot(dx, dy) < 6) return;
        moved = true; el.classList.add("dragging");
        el.style.left = `${ox + dx}px`; el.style.top = `${oy + dy}px`;
        edgeHint(ev.clientX);
      };
      const up = (ev) => {
        el.removeEventListener("pointermove", move); el.removeEventListener("pointerup", up);
        el.classList.remove("dragging");
        edgeHint(null);
        if (!moved) return;
        if (edgeDrop(card, ev.clientX)) return;
        const W = window.innerWidth, H = window.innerHeight;
        const cx = (el.offsetLeft + el.offsetWidth / 2) / W, cy = (el.offsetTop + el.offsetHeight / 2) / H;
        card.inst.pos = { x: cx, y: cy };
        postPos(card.inst.id, cx, cy);
        scheduleLayout();
      };
      el.addEventListener("pointermove", move); el.addEventListener("pointerup", up);
    });
    el.addEventListener("dblclick", () => {
      if (!card.inst.pos) return;
      card.inst.pos = null; postPos(card.inst.id, null, null); scheduleLayout();
    });
  }
  const mmss = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
  const TONES = new Set(["cyan", "green", "blue", "violet", "amber", "red"]);
  const icon = (name) => (window.NuxivaIcons ? window.NuxivaIcons.icon(name) : "");
  const head = ({ icon: ic = "", label = "", title = "", chip = "", live = false, state = "" } = {}) =>
    `<div class="wk-head">${ic ? icon(ic) : ""}<span class="wk-k">${esc(label)}</span>${title !== "" && title != null ? `<span class="wk-n">${esc(title)}</span>` : ""}`
    + `${chip !== "" && chip != null ? `<span class="wk-chip${live ? " live" : ""}${state ? ` ${esc(state)}` : ""}">${esc(chip)}</span>` : ""}</div>`;
  const pct = (v) => Math.max(0, Math.min(100, Number(v) || 0));
  const bar = (v, state = "") => `<span class="wk-bar${state ? ` ${esc(state)}` : ""}"><i style="width:${pct(v)}%"></i></span>`;
  const ring = (v, text = "", sub = "") => {
    const c = 2 * Math.PI * 42, arc = c * 0.75;
    return `<span class="wk-ring"><svg viewBox="0 0 96 96" aria-hidden="true"><circle class="track" cx="48" cy="48" r="42" stroke-dasharray="${arc} ${c}"/>`
      + `<circle class="value" cx="48" cy="48" r="42" stroke-dasharray="${(arc * pct(v)) / 100} ${c}"/></svg><b><span>${esc(text)}${sub ? `<small>${esc(sub)}</small>` : ""}</span></b></span>`;
  };
  const detail = (obj) => (obj && typeof obj === "object" ? ` data-detail="${esc(JSON.stringify(obj).slice(0, 8000))}"` : "");
  const LOCALES = { it: "it-IT", en: "en-GB", es: "es-ES", fr: "fr-FR" };
  const lang = () => (LOCALES[String(document.documentElement.lang || "").slice(0, 2)] ? String(document.documentElement.lang).slice(0, 2) : "it");
  const locale = () => LOCALES[lang()];
  const plain = (v, max = 6000) => {
    const s = String(v ?? "").slice(0, max).replace(/<br\s*\/?>/gi, "\n").replace(/<\/(p|div|li|tr|h[1-6])>/gi, "\n");
    return s.includes("<") ? new DOMParser().parseFromString(s, "text/html").body.textContent : s;
  };
  const lines = (v, max = 10, size = 6000) => plain(v, size).split("\n").map((l) => l.trim()).filter(Boolean).slice(0, max);
  const pair = (line, size = 48) => line.match(new RegExp(`^([^:]{1,${size}}):\\s+(.+)$`));
  const empty = (text) => `<div class="wk-empty">${esc(text)}</div>`;
  const str = (v, max = 400) => (typeof v === "string" ? v : typeof v === "number" && Number.isFinite(v) ? String(v) : "").replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, "").trim().slice(0, max);
  const num = (v) => {
    const n = typeof v === "string" && v.trim() ? Number(v.trim().replace(",", ".")) : v;
    return typeof n === "number" && Number.isFinite(n) ? n : null;
  };
  const arr = (v, max = 50) => (Array.isArray(v) ? v.slice(0, max) : []);
  const pick = (o, keys, max = 400) => {
    if (!o || typeof o !== "object") return "";
    for (const k of keys) { const s = Object.hasOwn(o, k) ? str(o[k], max) : ""; if (s) return s; }
    return "";
  };
  const stamp = (v) => {
    const n = num(v);
    if (n !== null) return n > 0 ? (n > 1e12 ? n / 1000 : n) : null;
    const t = typeof v === "string" ? Date.parse(v) : NaN;
    return Number.isFinite(t) ? t / 1000 : null;
  };
  const intl = new Map();
  const cached = (kind, opts) => {
    const k = `${kind}|${locale()}|${JSON.stringify(opts || {})}`;
    if (!intl.has(k)) intl.set(k, kind === "n" ? new Intl.NumberFormat(locale(), opts) : kind === "r" ? new Intl.RelativeTimeFormat(locale(), opts) : new Intl.DateTimeFormat(locale(), opts));
    return intl.get(k);
  };
  const fmt = (v, opts) => { const n = num(v); return n === null ? "" : cached("n", opts).format(n); };
  const when = (v, opts = { hour: "2-digit", minute: "2-digit" }) => { const s = stamp(v); return s === null ? "" : cached("d", opts).format(new Date(s * 1000)); };
  const ago = (v) => {
    const s = stamp(v);
    if (s === null) return "";
    const d = s - Date.now() / 1000, a = Math.abs(d);
    const [n, unit] = a < 10 ? [0, "second"] : a < 50 ? [d, "second"] : a < 3000 ? [d / 60, "minute"] : a < 72000 ? [d / 3600, "hour"] : [d / 86400, "day"];
    return cached("r", { numeric: "auto", style: "short" }).format(Math.round(n), unit);
  };
  const copy = async (text) => {
    const value = String(text ?? "");
    try {
      if (navigator.clipboard && window.isSecureContext) { await navigator.clipboard.writeText(value); return true; }
    } catch (_) {}
    const area = document.createElement("textarea");
    area.value = value;
    area.setAttribute("readonly", "");
    area.style.cssText = "position:fixed;left:-9999px;top:0;opacity:0";
    document.body.appendChild(area);
    area.select();
    let ok = false;
    try { ok = document.execCommand("copy"); } catch (_) { ok = false; }
    area.remove();
    return ok;
  };
  const ctx = { esc, mmss, icon, head, bar, ring, pct, detail, plain, lines, pair, empty, str, num, arr, pick, stamp, fmt, when, ago, copy, locale, lang, speak: (t) => hooks.speak(t), now: () => Date.now() / 1000 };
  const i18n = () => window.NuxivaScopedI18n;
  const scopeOf = (id) => `widgets/${id}`;
  const COMMON = scopeOf("common");
  const word = (scope, key, params) => (i18n() ? i18n().t(scope, key, params) : "");
  const contexts = new Map();
  function ctxFor(id) {
    if (!contexts.has(id)) {
      const t = (key, params) => word(scopeOf(id), key, params);
      const tc = (key, params) => word(COMMON, key, params);
      const count = (key, n) => t(n === 1 ? `${key}_one` : `${key}_other`, { n });
      const metrics = (content) => {
        const rows = lines(content, 10);
        if (!rows.length) return empty(tc("waiting"));
        const pairs = rows.map((l) => pair(l, 32));
        if (!pairs.every(Boolean)) return `<p class="wk-text">${rows.map(esc).join("<br>")}</p>`;
        const [first, ...rest] = pairs;
        const hero = first[2].length <= 14;
        const items = hero ? rest : pairs;
        const pc = first[2].match(/(\d+(?:[.,]\d+)?)\s*%/);
        const level = pc ? Number(pc[1].replace(",", ".")) : null;
        return `${hero ? `<div class="wk-hero"><span class="wk-num sm">${esc(first[2])}</span><span class="wk-sub">${esc(first[1])}</span></div>${level === null ? "" : bar(level, level >= 90 ? "bad" : level >= 75 ? "warn" : "")}` : ""}
          ${items.length ? `<dl class="wk-kv">${items.map((p) => `<dt>${esc(p[1])}</dt><dd class="mono">${esc(p[2])}</dd>`).join("")}</dl>` : ""}`;
      };
      contexts.set(id, Object.freeze({ ...ctx, t, tc, count, metrics }));
    }
    return contexts.get(id);
  }
  async function preload(id) {
    if (!i18n()) return;
    try { await Promise.all([i18n().preload(scopeOf(id)), i18n().preload(COMMON)]); } catch (err) { console.warn(`widget ${id}: traduzioni non caricate`, err); }
  }
  document.addEventListener("nuxiva-translated", () => {
    setTimeout(async () => {
      for (const card of cards.values()) {
        await preload(card.inst.id);
        try { gov(card.inst.id, () => card.impl.render(card.el.firstChild, card.inst.data, ctxFor(card.inst.id)), card.el, false); } catch (err) { console.warn(`widget ${card.inst.id}:`, err); }
      }
    }, 0);
  });

  function load(inst) {
    const key = `${inst.id}@${inst.rev}`;
    if (impls[inst.id] && impls[inst.id].rev === inst.rev) return Promise.resolve(impls[inst.id]);
    if (loading[key]) return loading[key];
    if (inst.css && !document.querySelector(`link[data-widget="${inst.id}"][data-rev="${inst.rev}"]`)) {
      const l = document.createElement("link");
      l.rel = "stylesheet"; l.href = `/widgets/${inst.id}/widget.css?r=${inst.rev}`; l.dataset.widget = inst.id; l.dataset.rev = inst.rev;
      document.head.appendChild(l);
    }
    const words = preload(inst.id);
    loading[key] = new Promise((ok, ko) => {
      const s = document.createElement("script");
      s.src = `/widgets/${inst.id}/widget.js?r=${inst.rev}`;
      s.onload = () => (impls[inst.id] ? (impls[inst.id].rev = inst.rev, words.then(() => ok(impls[inst.id]))) : ko(new Error(`widget ${inst.id} non registrato`)));
      s.onerror = () => ko(new Error(`widget ${inst.id} non caricato`));
      document.head.appendChild(s);
    });
    return loading[key];
  }

  async function draw(inst) {
    let card = cards.get(inst.key);
    const sig = JSON.stringify(inst.data);
    if (card && card.sig === sig && card.rev === inst.rev) {
      const renewed = card.inst.refreshed_at !== inst.refreshed_at;
      card.inst = inst;
      if (renewed) pulse(card);
      return card;
    }
    let impl;
    try { impl = await load(inst); } catch (err) { console.warn(err); return null; }
    if (!card || card.rev !== inst.rev) {
      if (card) remove(inst.key, true);
      const el = document.createElement("section");
      el.className = `widget size-${inst.size} w-${inst.id} tone-${TONES.has(inst.tone) ? inst.tone : "cyan"}${inst.essential ? " essential" : ""}${inst.urgent ? " urgent" : ""}${inst.takeover ? " takeover" : ""}${inst.immersive ? " immersive" : ""}${inst.chrome === false ? " frameless" : ""} hidden`;
      el.dataset.key = inst.key;
      el.innerHTML = '<div class="w-body"></div><i class="w-cycle" aria-hidden="true"></i>';
      card = { el, sig, rev: inst.rev, impl, inst, placed: false };
      cards.set(inst.key, card);
      host.appendChild(el);
      enableDrag(card);
      if (resizeObs) resizeObs.observe(el);
      try { gov(inst.id, () => impl.render(el.firstChild, inst.data, ctxFor(inst.id)), el, true); } catch (err) { console.warn(`widget ${inst.id}:`, err); }
      if ((inst.takeover || (inst.data && inst.data.announce)) && inst.data && inst.data.speak) ctx.speak(inst.data.speak);
    } else {
      card.sig = sig; card.inst = inst;
      try { gov(inst.id, () => (impl.update || impl.render)(card.el.firstChild, inst.data, ctxFor(inst.id)), card.el, false); } catch (err) { console.warn(`widget ${inst.id}:`, err); }
    }
    pulse(card);
    return card;
  }

  function pulse(card) {
    const cycle = card.el.querySelector(".w-cycle"), every = Number(card.inst.refresh) || 0;
    if (!cycle) return;
    card.el.classList.toggle("has-cycle", every > 0);
    if (!every) return;
    cycle.style.setProperty("--cycle", `${every}s`);
    cycle.classList.remove("run");
    void cycle.offsetWidth;
    cycle.classList.add("run");
    card.el.title = `${ctxFor(card.inst.id).tc("refresh_every", { n: every })}`;
  }

  function remove(key, now) {
    const card = cards.get(key);
    if (!card) return;
    cards.delete(key);
    try { card.impl.destroy && card.impl.destroy(card.el.firstChild); } catch (e) {}
    if (now) { card.el.remove(); return; }
    card.el.classList.add("leave");
    setTimeout(() => card.el.remove(), 450);
  }

  const place = (card, x, y, w, h) => {
    const s = card.el.style;
    s.left = `${Math.round(x)}px`; s.top = `${Math.round(y)}px`; s.width = `${Math.round(w)}px`;
    s.height = h ? `${Math.round(h)}px` : "";
    card.el.classList.remove("hidden");
    if (!card.placed) {
      card.placed = true;
      card.el.classList.add("enter");
      card.el.addEventListener("animationend", () => card.el.classList.remove("enter"), { once: true });
    }
  };
  function covers(cards, W, H) {
    const r = Math.min(W, H) * 0.36, cx = W / 2, cy = H * 0.46;
    return cards.some((c) => {
      if (c.el.classList.contains("hidden")) return false;
      const x0 = c.el.offsetLeft, y0 = c.el.offsetTop, x1 = x0 + c.el.offsetWidth, y1 = y0 + c.el.offsetHeight;
      const nx = Math.max(x0, Math.min(cx, x1)), ny = Math.max(y0, Math.min(cy, y1));
      return (nx - cx) ** 2 + (ny - cy) ** 2 < r * r;
    });
  }
  const PIN_GAP = 14;
  const hits = (a, b) => a.x < b.x + b.w + PIN_GAP && a.x + a.w + PIN_GAP > b.x && a.y < b.y + b.h + PIN_GAP && a.y + a.h + PIN_GAP > b.y;
  function clearSpot(want, blocked, box) {
    if (!blocked.some((b) => hits(want, b))) {
      if (want.x >= box.x0 && want.x + want.w <= box.x1 && want.y >= box.y0 && want.y + want.h <= box.y1) {
        return { x: want.x, y: want.y };
      }
    }
    const candidates = [];
    for (const o of blocked) {
      const opts = [
        { x: want.x, y: o.y + o.h + PIN_GAP },
        { x: want.x, y: o.y - want.h - PIN_GAP },
        { x: o.x + o.w + PIN_GAP, y: want.y },
        { x: o.x - want.w - PIN_GAP, y: want.y },
        { x: o.x, y: o.y + o.h + PIN_GAP },
        { x: o.x + o.w + PIN_GAP, y: o.y },
        { x: box.x0, y: o.y + o.h + PIN_GAP },
        { x: box.x1 - want.w, y: o.y + o.h + PIN_GAP },
      ];
      for (const p of opts) {
        if (p.x >= box.x0 && p.x + want.w <= box.x1 && p.y >= box.y0 && p.y + want.h <= box.y1) {
          if (!blocked.some((b) => hits({ x: p.x, y: p.y, w: want.w, h: want.h }, b))) {
            candidates.push(p);
          }
        }
      }
    }
    if (candidates.length) {
      candidates.sort((a, b) => Math.hypot(a.x - want.x, a.y - want.y) - Math.hypot(b.x - want.x, b.y - want.y));
      return candidates[0];
    }
    for (let y = box.y0; y <= box.y1 - want.h; y += 24) {
      for (let x = box.x0; x <= box.x1 - want.w; x += 24) {
        const test = { x, y, w: want.w, h: want.h };
        if (!blocked.some((b) => hits(test, b))) {
          return { x, y };
        }
      }
    }
    return null;
  }
  const measure = (card, w) => {
    const s = card.el.style, prior = s.transition;
    s.transition = "none";
    s.width = `${Math.round(w)}px`; s.height = "";
    const h = card.el.offsetHeight;
    s.transition = prior;
    return h;
  };
  const reserved = () => (document.body.matches(".desk-full, .desk-whiteboard") ? [] : [...document.querySelectorAll("[data-desk-reserve]:not([hidden])")])
    .filter((el) => getComputedStyle(el).display !== "none")
    .map((el) => el.getBoundingClientRect())
    .filter((r) => r.width > 0 && r.height > 0)
    .map((r) => ({ x: r.left, y: r.top, w: r.width, h: r.height }));

  function layoutFullscreen(ordered) {
    const full = ordered.find((c) => c.inst.fullscreen);
    ordered.forEach((c) => { c.el.classList.toggle("fullscreen", c === full); c.el.classList.remove("priority-overlay"); });
    document.body.classList.toggle("desk-full", !!full);
    document.body.classList.toggle("desk-immersive", !!(full && full.inst.immersive));
    document.body.dataset.deskFullscreen = full ? full.inst.id : "";
    document.body.classList.toggle("desk-whiteboard", ordered.some((c) => c.inst.id === "lavagna"));
    if (!full) return false;
    const isPriority = (card) => card.inst.urgent || card.inst.essential || (card.inst.priority && card.inst.priority >= 80);
    full.el.classList.remove("pinned");
    place(full, 0, 0, window.innerWidth, window.innerHeight);
    const W = window.innerWidth, H = window.innerHeight;
    const pw = Math.max(220, Math.min(320, W * 0.22));
    const column = { x: W - pw - 24, y: 0, w: pw, h: H };
    let py = reserved().filter((r) => hits(r, column)).reduce((y, r) => Math.max(y, r.y + r.h + PIN_GAP), 110);
    for (const c of ordered) {
      if (c === full) continue;
      if (!isPriority(c)) {
        c.el.classList.add("hidden");
        continue;
      }
      const ph = measure(c, pw);
      if (py + ph > H - 80) {
        c.el.classList.add("hidden");
        continue;
      }
      place(c, W - pw - 24, py, pw);
      c.el.classList.remove("hidden");
      c.el.classList.add("priority-overlay");
      py += ph + 14;
    }
    hooks.onStage(null);
    return true;
  }

  function layoutGrid() {
    const W = window.innerWidth, H = window.innerHeight, M = 26, GAP = 16, TOP = 96, BOTTOM = H - 30;
    if (layoutFullscreen(lastList.map((i) => cards.get(i.key)).filter(Boolean))) return;
    const cols = Math.max(1, Math.floor((W - 2 * M + GAP) / 420)), colW = (W - 2 * M - GAP * (cols - 1)) / cols;
    const heights = Array(cols).fill(TOP);
    const ordered = lastList.map((i) => cards.get(i.key)).filter(Boolean);
    const takeover = ordered.find((c) => c.inst.takeover);
    for (const c of ordered) {
      c.el.classList.remove("pinned");
      if (takeover && c !== takeover) { c.el.classList.add("hidden"); continue; }
      if (c === takeover) { place(c, M, TOP, W - 2 * M, BOTTOM - TOP); continue; }
      const fit = (span) => {
        let col = 0, best = Infinity;
        for (let i = 0; i + span <= cols; i++) {
          const top = Math.max(...heights.slice(i, i + span));
          if (top < best) { best = top; col = i; }
        }
        const w = colW * span + GAP * (span - 1);
        return { span, col, best, w, h: measure(c, w) };
      };
      const wide = c.inst.size === "full" ? cols : c.inst.size === "l" ? Math.min(2, cols) : 1;
      let f = fit(wide);
      if (f.best + f.h > BOTTOM && wide > 1) f = fit(1);
      const { span, col, best, w, h } = f;
      if (best + h > BOTTOM && best > TOP) { c.el.classList.add("hidden"); continue; }
      place(c, M + col * (colW + GAP), best, w, c.inst.size === "full" ? BOTTOM - best : 0);
      for (let i = col; i < col + span; i++) heights[i] = best + (c.inst.size === "full" ? BOTTOM : h) + GAP;
    }
    document.body.classList.toggle("desk-has", ordered.length > 0);
    document.body.classList.toggle("desk-alert", !!takeover);
  }

  function layout() {
    if (hooks.satellite) { layoutGrid(); return; }
    if (layoutFullscreen(lastList.map((i) => cards.get(i.key)).filter(Boolean))) return;
    const W = window.innerWidth, H = window.innerHeight;
    const M = W < 700 ? 14 : 26, GAP = 14, TOP = W < 700 ? 110 : 124, BOTTOM = H - (W < 700 ? 96 : 104);
    const ordered = lastList.map((i) => cards.get(i.key)).filter(Boolean);
    const takeover = ordered.find((c) => c.inst.takeover);
    const pinned = ordered.filter((c) => c.inst.pos && !c.inst.takeover);
    const normal = ordered.filter((c) => !c.inst.takeover && !c.inst.pos);
    const portrait = W < H || W < 760;
    let zone = null;
    ordered.forEach((c) => c.el.classList.remove("pinned"));

    const fixed = reserved();
    const blocked = [];
    const radius = Math.min(W, H) * 0.34;
    const keepOut = portrait || takeover ? [] : [{ x: W / 2 - radius, y: H * 0.46 - radius, w: 2 * radius, h: 2 * radius }];
    for (const c of pinned) {
      if (takeover) { c.el.classList.add("hidden"); continue; }
      const w = Math.max(240, Math.min(400, W * 0.26));
      const h = measure(c, w);
      const x = Math.max(M, Math.min(W - M - w, c.inst.pos.x * W - w / 2));
      const y = Math.max(TOP, Math.min(BOTTOM - h, c.inst.pos.y * H - h / 2));
      const spot = clearSpot({ x, y, w, h }, blocked.concat(keepOut, fixed), { x0: M, y0: TOP, x1: W - M, y1: BOTTOM });
      if (!spot) { c.el.classList.add("hidden"); continue; }
      place(c, spot.x, spot.y, w);
      blocked.push({ x: spot.x, y: spot.y, w, h });
      c.el.classList.add("pinned");
    }

    if (takeover) {
      normal.forEach((c) => c.el.classList.add("hidden"));
      if (portrait) {
        const top = Math.round(H * 0.36);
        place(takeover, M, top, W - 2 * M, BOTTOM - top);
        zone = { x: M, y: TOP - 20, w: W - 2 * M, h: top - TOP - 50 };
      } else {
        const left = Math.round(W * 0.36);
        place(takeover, left, TOP, W - left - M, BOTTOM - TOP);
        zone = { x: M, y: TOP, w: left - M - GAP, h: BOTTOM - TOP - 60 };
      }
    } else if (normal.length && portrait) {
      const cols = W >= 560 ? 2 : 1, colW = (W - 2 * M - GAP * (cols - 1)) / cols, limit = TOP + (H - TOP) * 0.42;
      for (const c of normal) {
        const w = colW;
        const h = measure(c, w);
        let bestSpot = null;
        for (let col = 0; col < cols; col++) {
          const x = M + col * (colW + GAP);
          const spot = clearSpot({ x, y: BOTTOM - h, w, h }, blocked.concat(fixed), { x0: M, y0: limit, x1: W - M, y1: BOTTOM });
          if (spot && (!bestSpot || spot.y > bestSpot.y)) {
            bestSpot = spot;
          }
        }
        if (!bestSpot) { c.el.classList.add("hidden"); continue; }
        place(c, bestSpot.x, bestSpot.y, w);
        blocked.push({ x: bestSpot.x, y: bestSpot.y, w, h });
      }
      const used = blocked.length ? Math.min(...blocked.map((b) => b.y)) : BOTTOM;
      zone = { x: M, y: TOP - 20, w: W - 2 * M, h: Math.max(160, used - TOP - 50) };
    } else if (normal.length) {
      const colW = Math.max(240, Math.min(380, W * 0.22));
      const sides = [{ x0: M, x1: M + colW }, { x0: W - M - colW, x1: W - M }];
      for (const c of normal) {
        const w = c.inst.size === "s" ? Math.max(220, Math.min(colW, 280)) : colW;
        const h = measure(c, w);
        const options = sides.map((side, index) => {
          const x = index === 0 ? side.x0 : side.x1 - w;
          return clearSpot({ x, y: TOP, w, h }, blocked.concat(keepOut, fixed), { x0: side.x0, y0: TOP, x1: side.x1, y1: BOTTOM });
        }).filter(Boolean);
        if (!options.length) { c.el.classList.add("hidden"); continue; }
        const chosen = options.reduce((best, o) => (o.y < best.y ? o : best));
        place(c, chosen.x, chosen.y, w);
        blocked.push({ x: chosen.x, y: chosen.y, w, h });
      }
      const leftBlocked = blocked.filter((b) => b.x < W / 2);
      const rightBlocked = blocked.filter((b) => b.x >= W / 2);
      const x0 = leftBlocked.length ? Math.max(...leftBlocked.map((b) => b.x + b.w)) + GAP : M;
      const x1 = rightBlocked.length ? Math.min(...rightBlocked.map((b) => b.x)) - GAP : W - M;
      const free = { x: x0, y: TOP - 30, w: Math.max(120, x1 - x0), h: BOTTOM - TOP - 70 };
      zone = { x: free.x + free.w * 0.05, y: free.y + free.h * 0.09, w: free.w * 0.9, h: free.h * 0.82 };
    }

    if (!takeover && zone && !blocked.length && !covers(normal, W, H)) zone = null;
    document.body.classList.toggle("desk-has", normal.length > 0 || !!takeover);
    document.body.classList.toggle("desk-alert", !!takeover);
    const stage = zone ? { ...zone, cx: zone.x + zone.w / 2, cy: zone.y + zone.h / 2 } : null;
    const sig = JSON.stringify(stage);
    if (sig !== lastZone) { lastZone = sig; hooks.onStage(stage); }
  }
  const scheduleLayout = () => { cancelAnimationFrame(layoutRaf); layoutRaf = requestAnimationFrame(layout); };

  const LOCAL = ["127.0.0.1", "localhost", "::1", "[::1]"].includes(location.hostname);
  const mine = (i) => {
    const mode = (window.NuxivaDisplay && window.NuxivaDisplay.state && window.NuxivaDisplay.state.display_settings && window.NuxivaDisplay.state.display_settings.session_mode) || hooks.sessionMode || "shared";
    if (mode === "isolated" && i.client_id) return i.client_id === hooks.clientId;
    if (mode === "shared" && !hooks.satellite && !LOCAL && hooks.screen === 0) return true;
    return i.screen === -1 || (i.screen == null ? hooks.screen === 0 : i.screen === hooks.screen);
  };
  let veto = () => false;
  const setVeto = (fn) => { veto = typeof fn === "function" ? fn : () => false; render(allList); };

  async function render(list) {
    allList = list || [];
    const mineNow = allList.filter((i) => mine(i) && !veto(i));
    lastList = window.nuxivaGovernor ? window.nuxivaGovernor.limit(mineNow) : mineNow;
    document.body.classList.toggle("desk-whiteboard", lastList.some((i) => i.id === "lavagna"));
    if (!host) return;
    const live = new Set(lastList.map((i) => i.key));
    [...cards.keys()].filter((k) => !live.has(k)).forEach((k) => remove(k));
    for (const inst of lastList) await draw(inst);
    scheduleLayout();
  }

  function hello() {
    fetch("/api/desk/hello", { method: "POST", headers: { "Content-Type": "application/json", "X-Nuxiva-Client": hooks.clientId || "" },
      body: JSON.stringify({ screen: hooks.screen, x: hooks.x || 0, w: window.innerWidth, h: window.innerHeight,
        local: ["127.0.0.1", "localhost"].includes(location.hostname), ear: window.nuxivaEar ? `${window.nuxivaEar.state} ${window.nuxivaEar.link}` : "",
        perf: window.nuxivaPerf ? window.nuxivaPerf.text : "", client: hooks.clientId || "" }) }).catch(() => {});
  }

  function mount(container, options = {}) {
    host = container;
    Object.assign(hooks, options);
    if (!hooks.quiet) { hello(); setInterval(hello, 10000); }
    ["l", "r"].forEach((side) => { const g = document.createElement("div"); g.className = `edge-glow ${side}`; document.body.appendChild(g); });
    window.addEventListener("resize", scheduleLayout);
    window.addEventListener("nuxiva-policy", () => render(allList));
    if (window.ResizeObserver) resizeObs = new ResizeObserver(scheduleLayout);
    render(allList);
  }

  window.NuxivaDesk = {
    register(id, impl) { impls[id] = impl; },
    ctx,
    implOf: (id) => impls[id] || null,
    mount, render, relayout: scheduleLayout, moveTo, neighbor, setVeto,
    setScreens(list) { screens = list || []; document.body.classList.toggle("multi-screen", screens.length > 1); },
    cardAt(x, y) {
      const el = document.elementFromPoint(x, y), sec = el && el.closest(".desk > .widget");
      return sec ? cards.get(sec.dataset.key) || null : null;
    },
    get screen() { return hooks.screen; },
    get active() { return lastList; },
    get all() { return allList; },
    get candidates() { return allList.filter(mine); },
  };
})();
