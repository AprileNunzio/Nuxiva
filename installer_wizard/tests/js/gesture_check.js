const assert = require("assert");
const G = require("../../web/display/hands_gesture.js");

const hand = (x, y) => {
  const h = Array(21).fill({ x: 0, y: 0 });
  h[4] = { x: x - 0.01, y };
  h[8] = { x: x + 0.01, y };
  return h;
};
const pose = (ax, ay, bx, by) => G.pair([hand(ax, ay), hand(bx, by)]);
const near = (a, b, eps = 1e-6) => assert.ok(Math.abs(a - b) < eps, `${a} != ${b}`);

const rest = pose(0.3, 0.5, 0.7, 0.5);
near(rest.span, 0.4);
near(rest.angle, 0);
near(rest.mid.x, 0.5);

const spread = G.delta(rest, pose(0.2, 0.5, 0.8, 0.5));
assert.ok(spread.scale > 1.2 && spread.scale <= 1.35 + 1e-9);
assert.strictEqual(spread.rotate, 0);

const squeeze = G.delta(rest, pose(0.4, 0.5, 0.6, 0.5));
assert.ok(squeeze.scale < 0.8);

const turned = G.delta(rest, pose(0.3, 0.4, 0.7, 0.6));
assert.ok(turned.rotate > 0.3, "clockwise rotation is positive");
const turnedBack = G.delta(rest, pose(0.3, 0.6, 0.7, 0.4));
assert.ok(turnedBack.rotate < -0.3, "counter-clockwise rotation is negative");
near(turned.scale, 1, 0.12);

const swapped = G.pair([hand(0.7, 0.6), hand(0.3, 0.4)]);
near(swapped.angle, G.pair([hand(0.3, 0.4), hand(0.7, 0.6)]).angle);

const moved = G.delta(rest, pose(0.4, 0.6, 0.8, 0.6));
assert.ok(moved.pan.x > 0.05 && moved.pan.y > 0.05);
near(moved.scale, 1, 1e-9);

const still = G.delta(rest, rest);
assert.deepStrictEqual(still, { scale: 1, rotate: 0, pan: { x: 0, y: 0 } });
const tremor = G.delta(rest, pose(0.3004, 0.5003, 0.7003, 0.5004));
assert.deepStrictEqual(tremor, { scale: 1, rotate: 0, pan: { x: 0, y: 0 } });

near(G.wrap(Math.PI * 2 + 0.1), 0.1);
const across = G.delta({ ...rest, angle: Math.PI - 0.05 }, { ...rest, angle: -Math.PI + 0.05 });
assert.ok(Math.abs(across.rotate) < 0.1, "angle wraps across ±π");

let state = null;
for (let i = 0; i < 20; i++) state = G.blend(state, pose(0.2, 0.5, 0.8, 0.5));
near(state.span, 0.6, 1e-3);
assert.deepStrictEqual(G.delta(null, rest), { scale: 1, rotate: 0, pan: { x: 0, y: 0 } });
console.log("ok");
