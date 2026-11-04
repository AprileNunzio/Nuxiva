(() => {
  const st = { page: 0, pages: 1, turn: "", turnTimer: 0, relayout: () => {} };
  const listeners = new Set();
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

  function frame() {
    const W = window.innerWidth, H = window.innerHeight;
    const M = Math.round(clamp(W * 0.028, 16, 96));
    const GAP = Math.round(clamp(W * 0.012, 12, 40));
    const head = document.querySelector("[data-screen-head]");
    const foot = document.querySelector("[data-screen-foot]");
    const top = head ? Math.round(head.getBoundingClientRect().bottom + GAP) : M;
    const bottom = H - (foot ? Math.round(foot.offsetHeight + GAP) : M);
    return { W, H, M, GAP, top, bottom, room: Math.max(120, bottom - top) };
  }

  function spanOf(card, fit) {
    const size = card.inst.size;
    return size === "full" ? fit : size === "l" ? Math.min(2, fit) : 1;
  }

  function grid(cards, f) {
    const min = f.W < 720 ? f.W - 2 * f.M : Math.max(360, f.W / 5.5);
    const fit = Math.max(1, Math.floor((f.W - 2 * f.M + f.GAP) / (min + f.GAP)));
    const units = cards.reduce((sum, c) => sum + spanOf(c, fit), 0);
    const cols = clamp(units, 1, fit);
    const colW = Math.min(min * 1.7, (f.W - 2 * f.M - f.GAP * (cols - 1)) / cols);
    return { cols, colW };
  }

  function slotIn(heights, span) {
    let col = 0, top = Infinity;
    for (let i = 0; i + span <= heights.length; i++) {
      const t = Math.max(...heights.slice(i, i + span));
      if (t < top) { top = t; col = i; }
    }
    return { col, top };
  }

  function paginate(cards, f, g, measure) {
    const pages = [];
    const open = () => { const p = { heights: Array(g.cols).fill(0), slots: [] }; pages.push(p); return p; };
    for (const card of cards) {
      const span = spanOf(card, g.cols);
      const w = g.colW * span + f.GAP * (span - 1);
      const natural = measure(card, w);
      const h = Math.min(f.room, natural);
      let page = null, slot = null;
      for (const p of pages) {
        const s = slotIn(p.heights, span);
        if (s.top + h <= f.room || !p.slots.length) { page = p; slot = s; break; }
      }
      if (!page) { page = open(); slot = slotIn(page.heights, span); }
      page.slots.push({ card, x: slot.col * (g.colW + f.GAP), y: slot.top, w, h, clamped: natural > f.room });
      for (let i = slot.col; i < slot.col + span; i++) page.heights[i] = slot.top + h + f.GAP;
    }
    return pages.length ? pages : [open()];
  }

  function centre(page, f) {
    const width = Math.max(0, ...page.slots.map((s) => s.x + s.w));
    const height = Math.max(0, ...page.slots.map((s) => s.y + s.h));
    return { dx: f.M + Math.max(0, (f.W - 2 * f.M - width) / 2), dy: f.top + Math.max(0, (f.room - height) * 0.42) };
  }

  function emit() {
    document.body.dataset.screenPages = String(st.pages);
    listeners.forEach((fn) => {
      try { fn({ page: st.page, pages: st.pages, turn: st.turn }); } catch (err) { console.error("multi-schermo: aggiornamento non riuscito", err); }
    });
  }

  function layout({ cards, place, measure }) {
    const f = frame();
    const takeover = cards.find((c) => c.inst.takeover);
    document.body.classList.toggle("desk-has", cards.length > 0);
    document.body.classList.toggle("desk-alert", !!takeover);
    cards.forEach((c) => c.el.classList.remove("pinned", "sg-clamped"));
    if (takeover) {
      cards.forEach((c) => { if (c !== takeover) c.el.classList.add("hidden"); });
      place(takeover, f.M, f.top, f.W - 2 * f.M, f.room);
      st.pages = 1; st.page = 0;
      emit();
      return;
    }
    const pages = paginate(cards, f, grid(cards, f), measure);
    st.pages = pages.length;
    st.page = clamp(st.page, 0, st.pages - 1);
    pages.forEach((page, index) => {
      const { dx, dy } = centre(page, f);
      for (const s of page.slots) {
        if (index !== st.page) { s.card.el.classList.add("hidden"); continue; }
        place(s.card, dx + s.x, dy + s.y, s.w, s.clamped ? s.h : 0);
        s.card.el.classList.toggle("sg-clamped", s.clamped);
      }
    });
    emit();
  }

  function go(n, turn = "") {
    const target = clamp(Math.round(Number(n) || 0), 0, st.pages - 1);
    if (target === st.page) return false;
    st.turn = turn || (target > st.page ? "next" : "prev");
    st.page = target;
    const desk = document.getElementById("desk");
    if (desk) {
      desk.dataset.turn = st.turn;
      clearTimeout(st.turnTimer);
      st.turnTimer = setTimeout(() => { desk.dataset.turn = ""; }, 700);
    }
    st.relayout();
    return true;
  }

  window.NuxivaScreenGrid = Object.freeze({
    layout,
    bind(relayout) { st.relayout = typeof relayout === "function" ? relayout : () => {}; },
    go,
    next: () => go(st.page + 1 >= st.pages ? 0 : st.page + 1, "next"),
    prev: () => go(st.page - 1 < 0 ? st.pages - 1 : st.page - 1, "prev"),
    onChange(fn) { if (typeof fn === "function") listeners.add(fn); },
    get page() { return st.page; },
    get pages() { return st.pages; },
  });
})();
