(function (global) {
  "use strict";
  const THREE = global.THREE;

  const REGIONS = {
    CONCEPT:  { color: "#3d9bff" },
    MEMORY:   { color: "#ffc53d" },
    USER:     { color: "#ff8a3d" },
    AGENT:    { color: "#b36bff" },
    SKILL:    { color: "#3dffa8" },
    DEVICE:   { color: "#ff4dd2" },
    LOCATION: { color: "#ff4d6a" },
  };

  const damp = (a, b, k, dt) => a + (b - a) * (1 - Math.exp(-k * dt));
  function hash(str) {
    let h = 2166136261;
    for (let i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 16777619); }
    return h >>> 0;
  }
  function rng(seed) {
    return () => { seed = (seed + 0x6d2b79f5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  }
  function quad(a, m, b, t, out) {
    const u = 1 - t;
    return out.set(u * u * a.x + 2 * u * t * m.x + t * t * b.x, u * u * a.y + 2 * u * t * m.y + t * t * b.y, u * u * a.z + 2 * u * t * m.z + t * t * b.z);
  }

  global.Nuxiva3D = { THREE, REGIONS, damp, hash, rng, quad };
})(window);
