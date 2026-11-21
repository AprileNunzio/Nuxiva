(() => {
  const SHAPES = ["dispersed", "sphere", "torus", "cube", "helix", "procedural"];
  const FIDELITIES = ["particles", "mesh_3d", "photoreal_pbr"];

  function detectPointBudget() {
    const gpu = (window.nuxivaPerf && window.nuxivaPerf.gpu) || "";
    if (/swiftshader|llvmpipe|software|nessuna/i.test(gpu)) {
      return { count: 480, tier: "cpu-fallback" };
    }
    return { count: 1600, tier: "webgl-pbr" };
  }

  function hexToRgb(hex) {
    const clean = String(hex || "#22d3ee").replace("#", "");
    const n = parseInt(clean.length === 3 ? clean.replace(/(.)/g, "$1$1") : clean, 16);
    if (Number.isNaN(n)) return [34, 211, 238];
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  }

  function defaultCarNodes() {
    return [
      { name: "chassis", shape: "box", size: [1.92, 0.36, 4.35], position: [0, -0.12, 0], color: "#e11d48", metal: 0.88, roughness: 0.14, clearcoat: 0.96, emissive: 0 },
      { name: "hood", shape: "wedge", size: [1.86, 0.32, 1.45], position: [0, 0.08, 1.35], color: "#e11d48", metal: 0.88, roughness: 0.14, clearcoat: 0.96, emissive: 0 },
      { name: "cabin", shape: "capsule", size: [1.52, 0.48, 1.95], position: [0, 0.24, -0.15], color: "#0f172a", metal: 0.2, roughness: 0.05, clearcoat: 1.0, emissive: 0 },
      { name: "rear_deck", shape: "box", size: [1.90, 0.34, 1.25], position: [0, 0.08, -1.42], color: "#e11d48", metal: 0.88, roughness: 0.14, clearcoat: 0.96, emissive: 0 },
      { name: "spoiler", shape: "box", size: [1.84, 0.06, 0.32], position: [0, 0.38, -1.96], color: "#1e293b", metal: 0.5, roughness: 0.3, clearcoat: 0.4, emissive: 0 },
      { name: "wheel_fl", shape: "cylinder", size: [0.36, 0.26, 0.36], position: [-0.96, -0.24, 1.32], color: "#111827", metal: 0.1, roughness: 0.82, clearcoat: 0, emissive: 0 },
      { name: "wheel_fr", shape: "cylinder", size: [0.36, 0.26, 0.36], position: [0.96, -0.24, 1.32], color: "#111827", metal: 0.1, roughness: 0.82, clearcoat: 0, emissive: 0 },
      { name: "wheel_rl", shape: "cylinder", size: [0.38, 0.28, 0.38], position: [-0.98, -0.22, -1.32], color: "#111827", metal: 0.1, roughness: 0.82, clearcoat: 0, emissive: 0 },
      { name: "wheel_rr", shape: "cylinder", size: [0.38, 0.28, 0.38], position: [0.98, -0.22, -1.32], color: "#111827", metal: 0.1, roughness: 0.82, clearcoat: 0, emissive: 0 },
      { name: "head_l", shape: "box", size: [0.36, 0.08, 0.12], position: [-0.68, 0.02, 2.14], color: "#e0f2fe", metal: 0.1, roughness: 0.1, clearcoat: 0.6, emissive: 2.8 },
      { name: "head_r", shape: "box", size: [0.36, 0.08, 0.12], position: [0.68, 0.02, 2.14], color: "#e0f2fe", metal: 0.1, roughness: 0.1, clearcoat: 0.6, emissive: 2.8 },
      { name: "tail", shape: "box", size: [1.68, 0.07, 0.10], position: [0, 0.12, -2.14], color: "#ff1e42", metal: 0.1, roughness: 0.1, clearcoat: 0.6, emissive: 2.5 },
    ];
  }

  function sampleProceduralTarget(nodes, count) {
    const list = Array.isArray(nodes) && nodes.length ? nodes : defaultCarNodes();
    const out = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const n = list[i % list.length];
      const sz = n.size || [1, 1, 1];
      const pos = n.position || [0, 0, 0];
      const u1 = ((i * 37) % 100) / 50 - 1;
      const u2 = ((i * 73) % 100) / 50 - 1;
      const u3 = ((i * 19) % 100) / 50 - 1;
      out[i * 3] = (pos[0] + u1 * sz[0] * 0.5) * 0.45;
      out[i * 3 + 1] = (pos[1] + u2 * sz[1] * 0.5) * 0.45;
      out[i * 3 + 2] = (pos[2] + u3 * sz[2] * 0.5) * 0.45;
    }
    return out;
  }

  function buildTarget(shape, count, nodes) {
    if (shape === "procedural") return sampleProceduralTarget(nodes, count);
    const out = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const u = (i + 0.5) / count;
      const phi = Math.acos(1 - 2 * u);
      const theta = Math.PI * (1 + Math.sqrt(5)) * i;
      let x = 0, y = 0, z = 0;
      if (shape === "dispersed") {
        const r = 1.65 + (i % 17) * 0.08;
        x = r * Math.sin(phi) * Math.cos(theta);
        y = r * Math.sin(phi) * Math.sin(theta);
        z = r * Math.cos(phi);
      } else if (shape === "torus") {
        const major = 1.05, minor = 0.38;
        const a = u * Math.PI * 2 * 13, b = u * Math.PI * 2;
        x = (major + minor * Math.cos(a)) * Math.cos(b);
        y = (major + minor * Math.cos(a)) * Math.sin(b);
        z = minor * Math.sin(a);
      } else if (shape === "cube") {
        const face = i % 6;
        const s1 = ((i * 37) % 100) / 50 - 1, s2 = ((i * 73) % 100) / 50 - 1, h = 0.85;
        if (face === 0) { x = h; y = s1 * h; z = s2 * h; }
        else if (face === 1) { x = -h; y = s1 * h; z = s2 * h; }
        else if (face === 2) { x = s1 * h; y = h; z = s2 * h; }
        else if (face === 3) { x = s1 * h; y = -h; z = s2 * h; }
        else if (face === 4) { x = s1 * h; y = s2 * h; z = h; }
        else { x = s1 * h; y = s2 * h; z = -h; }
      } else if (shape === "helix") {
        const turns = u * Math.PI * 10, strand = i % 2 === 0 ? 0 : Math.PI, radius = 0.72;
        x = radius * Math.cos(turns + strand);
        z = radius * Math.sin(turns + strand);
        y = (u - 0.5) * 2.2;
      } else {
        x = Math.sin(phi) * Math.cos(theta);
        y = Math.sin(phi) * Math.sin(theta);
        z = Math.cos(phi);
      }
      out[i * 3] = x; out[i * 3 + 1] = y; out[i * 3 + 2] = z;
    }
    return out;
  }

  function boxFaces(node) {
    const [sx, sy, sz] = (node.size || [1, 1, 1]).map((v) => v * 0.22);
    const [px, py, pz] = (node.position || [0, 0, 0]).map((v) => v * 0.44);
    const v = [
      [px - sx, py - sy, pz + sz], [px + sx, py - sy, pz + sz],
      [px + sx, py + sy, pz + sz], [px - sx, py + sy, pz + sz],
      [px - sx, py - sy, pz - sz], [px + sx, py - sy, pz - sz],
      [px + sx, py + sy, pz - sz], [px - sx, py + sy, pz - sz],
    ];
    return [
      { verts: [v[0], v[1], v[2], v[3]], n: [0, 0, 1] },
      { verts: [v[5], v[4], v[7], v[6]], n: [0, 0, -1] },
      { verts: [v[3], v[2], v[6], v[7]], n: [0, 1, 0] },
      { verts: [v[4], v[5], v[1], v[0]], n: [0, -1, 0] },
      { verts: [v[1], v[5], v[6], v[2]], n: [1, 0, 0] },
      { verts: [v[4], v[0], v[3], v[7]], n: [-1, 0, 0] },
    ];
  }

  function renderSolidOrPbr(ctx, w, h, nodes, fidelity, yaw, pitch, tx, ty, scale) {
    ctx.clearRect(0, 0, w, h);
    const list = Array.isArray(nodes) && nodes.length ? nodes : defaultCarNodes();
    const cy = Math.cos(yaw), sy = Math.sin(yaw);
    const cp = Math.cos(pitch), sp = Math.sin(pitch);
    const hw = w * 0.5 + tx * w * 0.25;
    const hh = h * 0.52 + ty * h * 0.25;
    const sc = Math.min(w, h) * 0.42 * scale;
    const isPbr = fidelity === "photoreal_pbr";

    if (isPbr) {
      const bg = ctx.createRadialGradient(hw, hh, sc * 0.05, hw, hh, sc * 1.35);
      bg.addColorStop(0, "rgba(251, 113, 133, 0.16)");
      bg.addColorStop(0.45, "rgba(56, 189, 248, 0.12)");
      bg.addColorStop(1, "rgba(2, 6, 18, 0)");
      ctx.fillStyle = bg;
      ctx.fillRect(0, 0, w, h);
    }

    const rot = (pt) => {
      const x1 = pt[0] * cy - pt[2] * sy;
      const z1 = pt[0] * sy + pt[2] * cy;
      const y2 = pt[1] * cp - z1 * sp;
      const z2 = pt[1] * sp + z1 * cp;
      return [x1, y2, z2];
    };

    const drawFaces = [];
    for (const node of list) {
      for (const f of boxFaces(node)) {
        const rv = f.verts.map(rot);
        const rn = rot(f.n);
        const zAvg = (rv[0][2] + rv[1][2] + rv[2][2] + rv[3][2]) * 0.25;
        drawFaces.push({ rv, rn, zAvg, node });
      }
    }
    drawFaces.sort((a, b) => a.zAvg - b.zAvg);

    const light = [-0.45, 0.72, 0.52];
    for (const item of drawFaces) {
      const { rv, rn, node } = item;
      const pts = rv.map((p) => {
        const persp = 2.4 / Math.max(0.7, 2.7 - p[2]);
        return [hw + p[0] * sc * persp, hh - p[1] * sc * persp];
      });
      const ndotl = Math.max(0.08, rn[0] * light[0] + rn[1] * light[1] + rn[2] * light[2]);
      const fresnel = Math.pow(1 - Math.min(1, Math.abs(rn[2])), 2.4);
      const [r, g, b] = hexToRgb(node.color);

      ctx.beginPath();
      ctx.moveTo(pts[0][0], pts[0][1]);
      ctx.lineTo(pts[1][0], pts[1][1]);
      ctx.lineTo(pts[2][0], pts[2][1]);
      ctx.lineTo(pts[3][0], pts[3][1]);
      ctx.closePath();

      if (isPbr) {
        const spec = Math.pow(Math.max(0, ndotl), 14) * (node.clearcoat || 0.7) * 185;
        const sky = fresnel * (node.metal || 0.5) * 95;
        const em = (node.emissive || 0) * 65;
        const fr = Math.min(255, Math.round(r * (0.22 + ndotl * 0.85) + spec + sky * 0.4 + em));
        const fg = Math.min(255, Math.round(g * (0.22 + ndotl * 0.85) + spec + sky * 0.75 + em * 0.7));
        const fb = Math.min(255, Math.round(b * (0.22 + ndotl * 0.85) + spec + sky + em * 0.9));
        const grad = ctx.createLinearGradient(pts[0][0], pts[0][1], pts[2][0], pts[2][1]);
        grad.addColorStop(0, `rgba(${fr}, ${fg}, ${fb}, 0.96)`);
        grad.addColorStop(0.55, `rgba(${Math.min(255, fr + 28)}, ${Math.min(255, fg + 28)}, ${Math.min(255, fb + 34)}, 0.98)`);
        grad.addColorStop(1, `rgba(${Math.max(0, Math.round(fr * 0.62))}, ${Math.max(0, Math.round(fg * 0.62))}, ${Math.max(0, Math.round(fb * 0.68))}, 0.96)`);
        ctx.fillStyle = grad;
        if (node.emissive > 1) {
          ctx.shadowColor = node.color || "#38bdf8";
          ctx.shadowBlur = 18;
        } else {
          ctx.shadowBlur = 0;
        }
        ctx.fill();
        ctx.strokeStyle = "rgba(255, 255, 255, 0.14)";
        ctx.lineWidth = 0.75;
        ctx.stroke();
      } else {
        const mr = Math.min(255, Math.round(r * (0.3 + ndotl * 0.7)));
        const mg = Math.min(255, Math.round(g * (0.3 + ndotl * 0.7)));
        const mb = Math.min(255, Math.round(b * (0.3 + ndotl * 0.7)));
        ctx.shadowBlur = 0;
        ctx.fillStyle = `rgba(${mr}, ${mg}, ${mb}, 0.88)`;
        ctx.fill();
        ctx.strokeStyle = "rgba(56, 189, 248, 0.55)";
        ctx.lineWidth = 1.1;
        ctx.stroke();
      }
    }
    ctx.shadowBlur = 0;
  }

  function createEngine(canvas) {
    const budget = detectPointBudget();
    const count = budget.count;
    let csgNodes = defaultCarNodes();
    const targets = {};
    SHAPES.forEach((s) => { targets[s] = buildTarget(s, count, csgNodes); });
    const current = new Float32Array(targets.sphere);
    let activeShape = "sphere";
    let fidelity = "particles";
    let transform = { yaw: 0, pitch: 0, roll: 0, tx: 0, ty: 0, scale: 1 };
    let spin = 0;
    const projected = new Float32Array(count * 3);

    function setShape(shape) {
      if (targets[shape]) activeShape = shape;
    }

    function setFidelity(nextFidelity) {
      if (FIDELITIES.includes(nextFidelity)) fidelity = nextFidelity;
    }

    function setProceduralNodes(nodes) {
      if (Array.isArray(nodes) && nodes.length) {
        csgNodes = nodes;
        targets.procedural = sampleProceduralTarget(csgNodes, count);
        activeShape = "procedural";
      }
    }

    function setTransform(next) {
      transform = { ...transform, ...next };
    }

    function stepAndRender() {
      const w = canvas.clientWidth || window.innerWidth;
      const h = canvas.clientHeight || window.innerHeight;
      if (canvas.width !== w || canvas.height !== h) {
        canvas.width = w;
        canvas.height = h;
      }
      spin += 0.011;
      const yaw = (transform.yaw || 0) + spin;
      const pitch = transform.pitch || 0.18;
      const sc = Math.max(0.45, Math.min(2.6, transform.scale || 1));
      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      if (fidelity === "mesh_3d" || fidelity === "photoreal_pbr") {
        renderSolidOrPbr(ctx, w, h, csgNodes, fidelity, yaw, pitch, transform.tx || 0, transform.ty || 0, sc);
        return;
      }

      const tgt = targets[activeShape] || targets.sphere;
      const cy = Math.cos(yaw), sy = Math.sin(yaw);
      const cp = Math.cos(pitch), sp = Math.sin(pitch);
      const aspect = h > 0 ? h / w : 1;
      const pScale = sc * 0.42;

      for (let i = 0; i < count * 3; i += 3) {
        current[i] += (tgt[i] - current[i]) * 0.12;
        current[i + 1] += (tgt[i + 1] - current[i + 1]) * 0.12;
        current[i + 2] += (tgt[i + 2] - current[i + 2]) * 0.12;
        const x0 = current[i], y0 = current[i + 1], z0 = current[i + 2];
        const x1 = x0 * cy - z0 * sy;
        const z1 = x0 * sy + z0 * cy;
        const y2 = y0 * cp - z1 * sp;
        const z2 = y0 * sp + z1 * cp;
        const persp = 2.4 / Math.max(0.8, 2.6 - z2);
        projected[i] = (x1 * pScale * persp * aspect) + (transform.tx || 0) * 0.65;
        projected[i + 1] = (y2 * pScale * persp) - (transform.ty || 0) * 0.65;
        projected[i + 2] = z2;
      }

      ctx.clearRect(0, 0, w, h);
      const hw = w * 0.5, hh = h * 0.5;
      for (let i = 0; i < count * 3; i += 3) {
        const px = hw + projected[i] * hw;
        const py = hh - projected[i + 1] * hh;
        const depthAlpha = Math.max(0.28, Math.min(0.95, (projected[i + 2] + 1.6) * 0.35));
        ctx.fillStyle = `rgba(34, 211, 238, ${depthAlpha.toFixed(2)})`;
        ctx.fillRect(px, py, 2.3, 2.3);
      }
    }

    return {
      setShape,
      setFidelity,
      setProceduralNodes,
      setTransform,
      stepAndRender,
      getShape: () => activeShape,
      getFidelity: () => fidelity,
      getTier: () => budget.tier,
    };
  }

  window.NuxivaSpatialHologram = { createEngine, SHAPES, FIDELITIES };
})();
