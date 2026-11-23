(() => {
  const MIN_COL = 230, MAX_COL = 380, MAX_PER_WING = 4;

  function wings(W, M, GAP) {
    const availW = W - 2 * M;
    const centerW = Math.max(260, Math.min(520, W * 0.28));
    const wingW = Math.max(MIN_COL, (availW - centerW - 2 * GAP) / 2);
    const per = Math.max(1, Math.min(MAX_PER_WING, Math.floor((wingW + GAP) / (MIN_COL + GAP))));
    const colW = Math.max(MIN_COL - 20, Math.min(MAX_COL, Math.floor((wingW - GAP * (per - 1)) / per)));
    const left = Array.from({ length: per }, (_, i) => M + i * (colW + GAP));
    const right = Array.from({ length: per }, (_, i) => W - M - colW - (per - 1 - i) * (colW + GAP));
    const xs = [...left, ...right];
    const order = [];
    for (let depth = 0; depth < per; depth++) order.push(depth, per * 2 - 1 - depth);
    return { xs, colW, order };
  }

  const overlaps = (a, b) => a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;

  function settle(x, y, w, h, obstacles, gap) {
    let top = y, moved = true;
    while (moved) {
      moved = false;
      for (const o of obstacles) {
        if (overlaps({ x, y: top, w, h }, o)) { top = o.y + o.h + gap; moved = true; }
      }
    }
    return top;
  }

  function fit(grid, tops, h, bottom, obstacles, gap) {
    for (let k = 0; k < grid.order.length; k += 2) {
      const group = grid.order.slice(k, k + 2)
        .map((i) => ({ i, y: settle(grid.xs[i], tops[i], grid.colW, h, obstacles, gap) }))
        .filter((c) => c.y + h <= bottom);
      if (group.length) return group.reduce((a, b) => (b.y < a.y ? b : a));
    }
    return null;
  }

  window.NuxivaDeskGrid = Object.freeze({ wings, fit, settle });
})();
