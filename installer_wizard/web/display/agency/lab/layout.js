(() => {
  const LAB = (window.NuxivaLab = window.NuxivaLab || {});
  const COLUMNS = [-3.9, -1.3, 1.3, 3.9];
  const ROWS = [0.5, 3.9];
  const SLOTS = [];
  for (const z of ROWS) for (const x of COLUMNS) SLOTS.push({ x, z });
  const GAPS = [-5.2, -2.6, 0, 2.6, 5.2];
  const AISLE_Z = [-1.6, 2.25, 5.6];
  const ROOM = Object.freeze({ w: 14, d: 12.4, h: 3.5, x0: -7, z0: -6.4 });
  const CEO = Object.freeze({ x: 0, z: -4.7 });
  const BRAIN = Object.freeze({ x: 0, z: -3.0 });
  const REVIEW = Object.freeze([{ x: -2.0, z: -3.1 }, { x: 2.0, z: -3.1 }, { x: -2.1, z: -2.1 }, { x: 2.1, z: -2.1 }, { x: -2.9, z: -3.1 }, { x: 2.9, z: -3.1 }]);

  const seatOf = (slot) => ({ x: slot.x, z: slot.z + 0.78 });
  const key = (x, z) => `${x}|${z}`;

  function graph() {
    const nodes = new Map();
    const add = (x, z) => { const k = key(x, z); if (!nodes.has(k)) nodes.set(k, { x, z, k, links: [] }); return nodes.get(k); };
    const link = (a, b) => { a.links.push(b); b.links.push(a); };
    for (const gx of GAPS) for (const az of AISLE_Z) add(gx, az);
    for (const az of AISLE_Z) {
      const row = GAPS.map((gx) => nodes.get(key(gx, az)));
      for (let i = 0; i < row.length - 1; i += 1) link(row[i], row[i + 1]);
    }
    for (const gx of GAPS) {
      for (let i = 0; i < AISLE_Z.length - 1; i += 1) link(nodes.get(key(gx, AISLE_Z[i])), nodes.get(key(gx, AISLE_Z[i + 1])));
    }
    return nodes;
  }

  const NODES = graph();

  function nearestNode(x, z) {
    let best = null;
    let bd = Infinity;
    for (const n of NODES.values()) {
      const d = Math.hypot(n.x - x, n.z - z) + (n.x === x ? 0 : 0.0001);
      if (d < bd) { bd = d; best = n; }
    }
    return best;
  }

  function standBeside(slot) {
    const side = slot.x < 0 ? 1 : -1;
    return { x: slot.x + side * 1.05, z: slot.z + 0.55, face: side > 0 ? -Math.PI / 2 : Math.PI / 2 };
  }

  function nodeBeside(slot) {
    const side = slot.x < 0 ? 1.3 : -1.3;
    const gx = GAPS.reduce((b, v) => (Math.abs(v - (slot.x + side)) < Math.abs(b - (slot.x + side)) ? v : b), GAPS[0]);
    const az = AISLE_Z.reduce((b, v) => (Math.abs(v - (slot.z + 0.78)) < Math.abs(b - (slot.z + 0.78)) ? v : b), AISLE_Z[0]);
    return NODES.get(key(gx, az));
  }

  function route(fromNode, toNode) {
    if (fromNode === toNode) return [fromNode];
    const dist = new Map([[fromNode, 0]]);
    const prev = new Map();
    const open = new Set([fromNode]);
    while (open.size) {
      let cur = null;
      for (const n of open) if (cur === null || dist.get(n) < dist.get(cur)) cur = n;
      open.delete(cur);
      if (cur === toNode) break;
      for (const n of cur.links) {
        const nd = dist.get(cur) + Math.hypot(n.x - cur.x, n.z - cur.z);
        if (nd < (dist.has(n) ? dist.get(n) : Infinity)) { dist.set(n, nd); prev.set(n, cur); open.add(n); }
      }
    }
    const path = [];
    for (let n = toNode; n; n = prev.get(n)) path.unshift(n);
    return path;
  }

  function pathBetween(from, to) {
    const a = from.node || nearestNode(from.x, from.z);
    const b = to.node || nearestNode(to.x, to.z);
    const points = [{ x: from.x, z: from.z }];
    if (from.exit) points.push(from.exit);
    route(a, b).forEach((n) => points.push({ x: n.x, z: n.z }));
    if (to.entry) points.push(to.entry);
    points.push({ x: to.x, z: to.z });
    return points;
  }

  LAB.layout = Object.freeze({ SLOTS, GAPS, AISLE_Z, ROOM, CEO, BRAIN, REVIEW, seatOf, standBeside, nodeBeside, nearestNode, pathBetween, NODES });
})();
