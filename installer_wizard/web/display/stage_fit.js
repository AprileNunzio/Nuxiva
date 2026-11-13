(() => {
  const D = window.NuxivaDisplay;
  const body = document.body;
  const stage = document.getElementById("stage");
  const box = document.getElementById("stage-body");
  if (!D || !stage || !box) return;

  const MIN = 0.5, READABLE = 0.72, MAX = 1.3, STEPS = 7;
  let frame = 0, settling = false;

  const overflowing = () => box.scrollHeight > box.clientHeight + 1 || box.scrollWidth > box.clientWidth + 1;
  const scale = (k) => box.style.setProperty("--fit", k.toFixed(3));
  const voice = (on) => { if (D.setVoiceOnly) D.setVoiceOnly(on, "stage"); };
  const ranked = () => [...new Set([...box.querySelectorAll("[data-prio]")].map((el) => Number(el.dataset.prio)).filter((n) => n > 1))].sort((a, b) => b - a);
  const cut = (level) => box.querySelectorAll("[data-prio]").forEach((el) => el.classList.toggle("fit-cut", level > 0 && Number(el.dataset.prio) >= level));

  const best = (lo, hi) => {
    scale(hi);
    if (!overflowing()) return hi;
    let a = lo, b = hi;
    for (let i = 0; i < STEPS; i++) {
      const mid = (a + b) / 2;
      scale(mid);
      if (overflowing()) b = mid; else a = mid;
    }
    scale(a);
    return a;
  };

  const fits = (k) => { scale(k); return !overflowing(); };

  const release = () => {
    body.classList.remove("stage-wide");
    box.removeAttribute("data-fit");
    cut(0);
    scale(1);
    voice(false);
  };

  const fit = () => {
    frame = 0;
    if (!body.classList.contains("focus") || !box.children.length) { release(); return; }
    settling = true;
    box.classList.add("fit-measuring");
    body.classList.remove("stage-wide");
    cut(0);
    let wide = false, level = 0, k;
    if (fits(1)) k = best(1, MAX);
    else {
      wide = true;
      body.classList.add("stage-wide");
      if (fits(1)) k = best(1, MAX);
      else if (fits(READABLE)) k = best(READABLE, 1);
      else {
        for (const prio of ranked()) {
          level = prio;
          cut(level);
          if (fits(READABLE)) break;
        }
        k = fits(READABLE) ? best(READABLE, 1) : best(MIN, READABLE);
      }
    }
    box.dataset.fit = wide ? (level ? "cut" : "wide") : "side";
    voice(wide);
    box.classList.remove("fit-measuring");
    settling = false;
  };

  const schedule = () => { if (!frame && !settling) frame = requestAnimationFrame(fit); };

  for (const name of ["renderStage", "renderSkeleton"]) {
    const original = D[name];
    if (typeof original !== "function") continue;
    D[name] = (...args) => { const out = original(...args); schedule(); return out; };
  }
  if (typeof D.setMode === "function") {
    const setMode = D.setMode;
    D.setMode = (...args) => { const out = setMode(...args); schedule(); return out; };
  }

  window.addEventListener("resize", schedule, { passive: true });
  box.addEventListener("load", schedule, true);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(schedule).catch(() => {});
  if ("ResizeObserver" in window) {
    let last = "";
    new ResizeObserver(() => {
      const key = `${window.innerWidth}x${window.innerHeight}`;
      if (key !== last) { last = key; schedule(); }
    }).observe(document.documentElement);
  }
  new MutationObserver(schedule).observe(box, { childList: true, subtree: true });
  D.fitStage = schedule;
})();
