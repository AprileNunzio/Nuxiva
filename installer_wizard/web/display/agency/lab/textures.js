(() => {
  const LAB = (window.NuxivaLab = window.NuxivaLab || {});

  function rng(seed) {
    let s = seed >>> 0;
    return () => {
      s = (s + 0x6d2b79f5) >>> 0;
      let t = s;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function canvas(size) {
    const c = document.createElement("canvas");
    c.width = c.height = size;
    return c;
  }

  function speckle(ctx, size, amount, alpha, seed, light = 255) {
    const r = rng(seed);
    const img = ctx.getImageData(0, 0, size, size);
    for (let i = 0; i < img.data.length; i += 4) {
      const n = (r() - 0.5) * amount;
      img.data[i] = Math.max(0, Math.min(255, img.data[i] + n * (light / 255)));
      img.data[i + 1] = Math.max(0, Math.min(255, img.data[i + 1] + n * (light / 255)));
      img.data[i + 2] = Math.max(0, Math.min(255, img.data[i + 2] + n * (light / 255)));
      img.data[i + 3] = alpha === undefined ? img.data[i + 3] : alpha;
    }
    ctx.putImageData(img, 0, 0);
  }

  function normalFrom(height, size, strength) {
    const src = height.getContext("2d").getImageData(0, 0, size, size).data;
    const out = canvas(size);
    const ctx = out.getContext("2d");
    const img = ctx.createImageData(size, size);
    const at = (x, y) => src[(((y + size) % size) * size + ((x + size) % size)) * 4] / 255;
    for (let y = 0; y < size; y += 1) {
      for (let x = 0; x < size; x += 1) {
        const dx = (at(x + 1, y) - at(x - 1, y)) * strength;
        const dy = (at(x, y + 1) - at(x, y - 1)) * strength;
        const len = Math.hypot(dx, dy, 1);
        const i = (y * size + x) * 4;
        img.data[i] = (-dx / len * 0.5 + 0.5) * 255;
        img.data[i + 1] = (dy / len * 0.5 + 0.5) * 255;
        img.data[i + 2] = (1 / len * 0.5 + 0.5) * 255;
        img.data[i + 3] = 255;
      }
    }
    ctx.putImageData(img, 0, 0);
    return out;
  }

  function grey(c, size) {
    const ctx = c.getContext("2d");
    const img = ctx.getImageData(0, 0, size, size);
    for (let i = 0; i < img.data.length; i += 4) {
      img.data[i + 1] = img.data[i];
      img.data[i + 2] = img.data[i];
      img.data[i + 3] = 255;
    }
    ctx.putImageData(img, 0, 0);
    return c;
  }

  function texture(c, repeat, color, aniso) {
    const t = new THREE.CanvasTexture(c);
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.repeat.set(repeat[0], repeat[1]);
    t.anisotropy = aniso;
    if (color) t.encoding = THREE.sRGBEncoding;
    return t;
  }

  function build(kind, size, aniso) {
    const albedo = canvas(size);
    const rough = canvas(size);
    const height = canvas(size);
    const a = albedo.getContext("2d");
    const r = rough.getContext("2d");
    const h = height.getContext("2d");
    const R = rng(kind.length * 7919);
    if (kind === "floor") {
      const n = 4;
      const cell = size / n;
      for (let y = 0; y < n; y += 1) {
        for (let x = 0; x < n; x += 1) {
          const v = 74 + Math.floor(R() * 16);
          a.fillStyle = `rgb(${v - 6},${v - 2},${v + 4})`;
          a.fillRect(x * cell, y * cell, cell, cell);
          r.fillStyle = `rgb(${70 + Math.floor(R() * 40)},0,0)`;
          r.fillRect(x * cell, y * cell, cell, cell);
          h.fillStyle = "#fff";
          h.fillRect(x * cell, y * cell, cell, cell);
        }
      }
      a.fillStyle = "rgba(150,165,180,0.85)";
      r.fillStyle = "#c8c8c8";
      h.fillStyle = "#000";
      const g = Math.max(2, size / 128);
      for (let i = 0; i <= n; i += 1) {
        for (const ctx of [a, r, h]) {
          ctx.fillRect(i * cell - g / 2, 0, g, size);
          ctx.fillRect(0, i * cell - g / 2, size, g);
        }
      }
      speckle(a, size, 10, 255, 11);
      speckle(h, size, 24, 255, 12);
    } else if (kind === "wall") {
      a.fillStyle = "#c4ccd6";
      a.fillRect(0, 0, size, size);
      r.fillStyle = "rgb(205,0,0)";
      r.fillRect(0, 0, size, size);
      h.fillStyle = "#808080";
      h.fillRect(0, 0, size, size);
      speckle(a, size, 12, 255, 21);
      speckle(h, size, 40, 255, 22);
    } else if (kind === "wood") {
      a.fillStyle = "#b98a5a";
      a.fillRect(0, 0, size, size);
      r.fillStyle = "rgb(150,0,0)";
      r.fillRect(0, 0, size, size);
      h.fillStyle = "#808080";
      h.fillRect(0, 0, size, size);
      for (let i = 0; i < size / 2; i += 1) {
        const y = R() * size;
        const w = 0.5 + R() * 1.6;
        const tone = R() > 0.5 ? "rgba(92,58,30,0.22)" : "rgba(235,200,150,0.16)";
        for (const [ctx, col] of [[a, tone], [h, R() > 0.5 ? "rgba(0,0,0,0.18)" : "rgba(255,255,255,0.14)"]]) {
          ctx.strokeStyle = col;
          ctx.lineWidth = w;
          ctx.beginPath();
          ctx.moveTo(0, y);
          ctx.bezierCurveTo(size * 0.3, y + (R() - 0.5) * 8, size * 0.7, y + (R() - 0.5) * 8, size, y + (R() - 0.5) * 6);
          ctx.stroke();
        }
      }
    } else if (kind === "metal") {
      a.fillStyle = "#aeb6c0";
      a.fillRect(0, 0, size, size);
      r.fillStyle = "rgb(95,0,0)";
      r.fillRect(0, 0, size, size);
      h.fillStyle = "#808080";
      h.fillRect(0, 0, size, size);
      for (let i = 0; i < size * 1.5; i += 1) {
        const y = R() * size;
        const tone = 128 + Math.floor((R() - 0.5) * 80);
        for (const ctx of [a, h, r]) {
          ctx.strokeStyle = `rgba(${tone},${tone},${tone},0.18)`;
          ctx.lineWidth = 0.6;
          ctx.beginPath();
          ctx.moveTo(0, y);
          ctx.lineTo(size, y);
          ctx.stroke();
        }
      }
    } else {
      a.fillStyle = "#4a5568";
      a.fillRect(0, 0, size, size);
      r.fillStyle = "rgb(235,0,0)";
      r.fillRect(0, 0, size, size);
      h.fillStyle = "#808080";
      h.fillRect(0, 0, size, size);
      const step = Math.max(2, size / 128);
      for (let y = 0; y < size; y += step) {
        for (let x = 0; x < size; x += step) {
          if ((x / step + y / step) % 2 === 0) {
            a.fillStyle = "rgba(255,255,255,0.05)";
            a.fillRect(x, y, step, step);
            h.fillStyle = "rgba(255,255,255,0.35)";
            h.fillRect(x, y, step, step);
          }
        }
      }
      speckle(a, size, 18, 255, 31);
    }
    return { albedo, rough: grey(rough, size), normal: normalFrom(height, size, kind === "floor" ? 2.2 : 1.4), aniso };
  }

  function create(spec, aniso) {
    const cache = new Map();
    const owned = [];
    function set(kind, repeat) {
      const key = `${kind}:${repeat.join("x")}:${spec.tex}`;
      if (cache.has(key)) return cache.get(key);
      const made = build(kind, spec.tex, aniso);
      const out = {
        map: texture(made.albedo, repeat, true, aniso),
        roughnessMap: texture(made.rough, repeat, false, aniso),
        normalMap: texture(made.normal, repeat, false, aniso),
      };
      owned.push(out.map, out.roughnessMap, out.normalMap);
      cache.set(key, out);
      return out;
    }
    return {
      set,
      dispose() { owned.forEach((t) => t.dispose()); owned.length = 0; cache.clear(); },
    };
  }

  LAB.textures = Object.freeze({ create, rng });
})();
