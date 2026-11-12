(() => {
  const DEAD_SCALE = 0.006, DEAD_ROTATE = 0.01, DEAD_PAN = 0.0015, MAX_SCALE = 1.35, MAX_ROTATE = 0.7, SMOOTH = 0.55;

  const midpoint = (hand) => ({ x: (hand[4].x + hand[8].x) / 2, y: (hand[4].y + hand[8].y) / 2 });
  const wrap = (a) => Math.atan2(Math.sin(a), Math.cos(a));
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  const dead = (v, zone) => (Math.abs(v) < zone ? 0 : v - Math.sign(v) * zone);

  function pair(hands) {
    const a = midpoint(hands[0]), b = midpoint(hands[1]);
    const left = a.x <= b.x ? a : b, right = a.x <= b.x ? b : a;
    return { mid: { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 }, span: Math.hypot(a.x - b.x, a.y - b.y), angle: Math.atan2(right.y - left.y, right.x - left.x) };
  }

  function blend(previous, current) {
    if (!previous) return current;
    return {
      mid: { x: previous.mid.x + (current.mid.x - previous.mid.x) * SMOOTH, y: previous.mid.y + (current.mid.y - previous.mid.y) * SMOOTH },
      span: previous.span + (current.span - previous.span) * SMOOTH,
      angle: previous.angle + wrap(current.angle - previous.angle) * SMOOTH,
    };
  }

  function delta(previous, current) {
    if (!previous || !current || previous.span <= 0) return { scale: 1, rotate: 0, pan: { x: 0, y: 0 } };
    const ratio = Math.log(current.span / previous.span);
    const scale = Math.exp(clamp(dead(ratio, DEAD_SCALE), -Math.log(MAX_SCALE), Math.log(MAX_SCALE)));
    const rotate = clamp(dead(wrap(current.angle - previous.angle), DEAD_ROTATE), -MAX_ROTATE, MAX_ROTATE);
    return {
      scale,
      rotate,
      pan: { x: dead(current.mid.x - previous.mid.x, DEAD_PAN), y: dead(current.mid.y - previous.mid.y, DEAD_PAN) },
    };
  }

  const api = { pair, blend, delta, wrap };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else window.NuxivaGesture = api;
})();
