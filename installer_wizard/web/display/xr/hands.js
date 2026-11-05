(() => {
  const PINCH = 0.025;

  function create(renderer, target) {
    const hands = [renderer.xr.getHand(0), renderer.xr.getHand(1)];
    let last = null;

    const tip = (hand, name) => (hand.joints && hand.joints[name] ? hand.joints[name].position : null);
    function pinching(hand) {
      const a = tip(hand, "thumb-tip"), b = tip(hand, "index-finger-tip");
      return a && b && a.distanceTo(b) < PINCH ? b.clone() : null;
    }

    function update() {
      const points = hands.map(pinching).filter(Boolean);
      if (!points.length) { last = null; return; }
      if (points.length === 2) {
        const span = points[0].distanceTo(points[1]), angle = Math.atan2(points[1].z - points[0].z, points[1].x - points[0].x);
        if (last && last.length === 2) {
          target.scale.multiplyScalar(Math.min(1.5, Math.max(0.66, span / Math.max(last.span, 1e-3)))).clampScalar(0.1, 10);
          target.rotation.y -= angle - last.angle;
        }
        last = { length: 2, span, angle };
        return;
      }
      const p = points[0];
      if (last && last.length === 1) {
        target.rotation.y += (p.x - last.p.x) * 4;
        target.rotation.x += (p.y - last.p.y) * 4;
      }
      last = { length: 1, p };
    }

    return { update };
  }

  window.NuxivaXrHands = Object.freeze({ create });
})();
