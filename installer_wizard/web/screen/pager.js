(() => {
  const ROTATE_MS = 20000, PAUSE_MS = 60000, SWIPE = 70;
  const st = { el: null, dots: null, timer: 0, drawn: false, pausedUntil: 0, down: null, pages: 1, page: 0 };
  const grid = () => window.NuxivaScreenGrid;

  function pause() { st.pausedUntil = Date.now() + PAUSE_MS; }

  function schedule(delay = ROTATE_MS) {
    clearTimeout(st.timer);
    const wait = Math.max(delay, st.pausedUntil - Date.now());
    st.el.style.setProperty("--rotate", `${wait}ms`);
    st.el.classList.remove("run");
    if (st.pages < 2) return;
    void st.el.offsetWidth;
    st.el.classList.add("run");
    st.timer = setTimeout(tick, wait);
  }

  function draw({ page, pages }) {
    const moved = page !== st.page || pages !== st.pages || !st.drawn;
    st.page = page; st.pages = pages; st.drawn = true;
    if (!moved) return;
    st.el.classList.toggle("off", pages < 2);
    document.body.classList.toggle("screen-paged", pages > 1);
    if (st.dots.childElementCount !== pages) {
      st.dots.replaceChildren(...Array.from({ length: pages }, (_, i) => {
        const b = document.createElement("button");
        b.type = "button";
        b.className = "sp-dot";
        b.dataset.page = String(i);
        PageText.attr(b, { "aria-label": "page_go", title: "page_go" }, { n: i + 1 });
        return b;
      }));
    }
    [...st.dots.children].forEach((b, i) => {
      b.classList.toggle("on", i === page);
      b.setAttribute("aria-current", i === page ? "page" : "false");
    });
    PageText.bind(st.el.querySelector("[data-pager-label]"), "page_of", { n: page + 1, total: pages });
    schedule();
  }

  function step(dir) {
    if (st.pages < 2) return;
    pause();
    if (dir > 0) grid().next(); else grid().prev();
  }

  function tick() {
    if (st.pages < 2) return;
    const busy = document.hidden || document.body.classList.contains("desk-full") || document.querySelector(".widget.dragging, .wt-menu, .wt-sheet");
    if (busy || Date.now() < st.pausedUntil) { schedule(busy ? ROTATE_MS / 2 : 0); return; }
    grid().next();
  }

  function onKey(e) {
    if (e.target && e.target.closest && e.target.closest("input, textarea, select, [contenteditable]")) return;
    if (["ArrowRight", "PageDown"].includes(e.key)) { step(1); e.preventDefault(); }
    if (["ArrowLeft", "PageUp"].includes(e.key)) { step(-1); e.preventDefault(); }
  }

  function onDown(e) {
    if (e.button || (e.target.closest && e.target.closest(".widget, button, a, input, select, textarea"))) { st.down = null; return; }
    st.down = { x: e.clientX, y: e.clientY, t: Date.now() };
  }

  function onUp(e) {
    const d = st.down;
    st.down = null;
    if (!d || Date.now() - d.t > 900) return;
    const dx = e.clientX - d.x, dy = e.clientY - d.y;
    if (Math.abs(dx) > SWIPE && Math.abs(dx) > Math.abs(dy) * 1.5) step(dx < 0 ? 1 : -1);
  }

  function mount(el) {
    st.el = el;
    st.dots = el.querySelector("[data-pager-dots]");
    st.dots.addEventListener("click", (e) => {
      const b = e.target.closest("[data-page]");
      if (!b) return;
      pause();
      grid().go(Number(b.dataset.page));
    });
    el.querySelector("[data-pager-prev]").addEventListener("click", () => step(-1));
    el.querySelector("[data-pager-next]").addEventListener("click", () => step(1));
    document.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onDown, { passive: true });
    document.addEventListener("pointerup", onUp, { passive: true });
    grid().onChange(draw);
  }

  window.NuxivaScreenPager = Object.freeze({ mount });
})();
