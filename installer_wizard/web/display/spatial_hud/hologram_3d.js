(() => {
  const SHAPES = ["dispersed", "sphere", "torus", "cube", "helix"];

  function detectPointBudget() {
    const gpu = (window.nuxivaPerf && window.nuxivaPerf.gpu) || "";
    if (/swiftshader|llvmpipe|software|nessuna/i.test(gpu)) {
      return { count: 420, tier: "cpu-fallback" };
    }
    return { count: 1400, tier: "webgl-gpu" };
  }

  function buildTarget(shape, count) {
    const out = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const u = (i + 0.5) / count;
      const phi = Math.acos(1 - 2 * u);
      const theta = Math.PI * (1 + Math.sqrt(5)) * i;
      let x = 0;
      let y = 0;
      let z = 0;
      if (shape === "dispersed") {
        const r = 1.65 + (i % 17) * 0.08;
        x = r * Math.sin(phi) * Math.cos(theta);
        y = r * Math.sin(phi) * Math.sin(theta);
        z = r * Math.cos(phi);
      } else if (shape === "torus") {
        const major = 1.05;
        const minor = 0.38;
        const a = u * Math.PI * 2 * 13;
        const b = u * Math.PI * 2;
        x = (major + minor * Math.cos(a)) * Math.cos(b);
        y = (major + minor * Math.cos(a)) * Math.sin(b);
        z = minor * Math.sin(a);
      } else if (shape === "cube") {
        const face = i % 6;
        const s1 = ((i * 37) % 100) / 50 - 1;
        const s2 = ((i * 73) % 100) / 50 - 1;
        const h = 0.85;
        if (face === 0) { x = h; y = s1 * h; z = s2 * h; }
        else if (face === 1) { x = -h; y = s1 * h; z = s2 * h; }
        else if (face === 2) { x = s1 * h; y = h; z = s2 * h; }
        else if (face === 3) { x = s1 * h; y = -h; z = s2 * h; }
        else if (face === 4) { x = s1 * h; y = s2 * h; z = h; }
        else { x = s1 * h; y = s2 * h; z = -h; }
      } else if (shape === "helix") {
        const turns = u * Math.PI * 10;
        const strand = i % 2 === 0 ? 0 : Math.PI;
        const radius = 0.72;
        x = radius * Math.cos(turns + strand);
        z = radius * Math.sin(turns + strand);
        y = (u - 0.5) * 2.2;
      } else {
        const r = 1.0;
        x = r * Math.sin(phi) * Math.cos(theta);
        y = r * Math.sin(phi) * Math.sin(theta);
        z = r * Math.cos(phi);
      }
      const idx = i * 3;
      out[idx] = x;
      out[idx + 1] = y;
      out[idx + 2] = z;
    }
    return out;
  }

  function createEngine(canvas) {
    const budget = detectPointBudget();
    const count = budget.count;
    const targets = {};
    SHAPES.forEach((s) => { targets[s] = buildTarget(s, count); });
    const current = new Float32Array(targets.sphere);
    let activeShape = "sphere";
    let transform = { yaw: 0, pitch: 0, roll: 0, tx: 0, ty: 0, scale: 1 };
    let spin = 0;

    const gl = canvas.getContext("webgl", { alpha: true, antialias: true });
    let prog = null;
    let buf = null;
    const projected = new Float32Array(count * 3);

    if (gl) {
      const vs = gl.createShader(gl.VERTEX_SHADER);
      gl.shaderSource(vs, "attribute vec3 p; void main(){ gl_Position = vec4(p.xy, 0.0, 1.0); gl_PointSize = max(1.8, (p.z + 2.5) * 2.1); }");
      gl.compileShader(vs);
      const fs = gl.createShader(gl.FRAGMENT_SHADER);
      gl.shaderSource(fs, "precision mediump float; void main(){ vec2 c = gl_PointCoord - vec2(0.5); if(dot(c,c)>0.25) discard; gl_FragColor = vec4(0.18, 0.92, 0.98, 0.86); }");
      gl.compileShader(fs);
      prog = gl.createProgram();
      gl.attachShader(prog, vs);
      gl.attachShader(prog, fs);
      gl.linkProgram(prog);
      buf = gl.createBuffer();
    }

    function setShape(shape) {
      if (targets[shape]) activeShape = shape;
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
      const tgt = targets[activeShape] || targets.sphere;
      spin += 0.012;
      const yaw = transform.yaw + spin;
      const pitch = transform.pitch;
      const cy = Math.cos(yaw), sy = Math.sin(yaw);
      const cp = Math.cos(pitch), sp = Math.sin(pitch);
      const aspect = h > 0 ? h / w : 1;
      const sc = Math.max(0.4, Math.min(2.6, transform.scale || 1)) * 0.42;

      for (let i = 0; i < count * 3; i += 3) {
        current[i] += (tgt[i] - current[i]) * 0.12;
        current[i + 1] += (tgt[i + 1] - current[i + 1]) * 0.12;
        current[i + 2] += (tgt[i + 2] - current[i + 2]) * 0.12;

        const x0 = current[i];
        const y0 = current[i + 1];
        const z0 = current[i + 2];

        const x1 = x0 * cy - z0 * sy;
        const z1 = x0 * sy + z0 * cy;
        const y2 = y0 * cp - z1 * sp;
        const z2 = y0 * sp + z1 * cp;

        const persp = 2.4 / Math.max(0.8, 2.6 - z2);
        projected[i] = (x1 * sc * persp * aspect) + (transform.tx || 0) * 0.65;
        projected[i + 1] = (y2 * sc * persp) - (transform.ty || 0) * 0.65;
        projected[i + 2] = z2;
      }

      if (gl && prog && buf) {
        gl.viewport(0, 0, canvas.width, canvas.height);
        gl.clearColor(0, 0, 0, 0);
        gl.clear(gl.COLOR_BUFFER_BIT);
        gl.useProgram(prog);
        gl.bindBuffer(gl.ARRAY_BUFFER, buf);
        gl.bufferData(gl.ARRAY_BUFFER, projected, gl.DYNAMIC_DRAW);
        const loc = gl.getAttribLocation(prog, "p");
        gl.enableVertexAttribArray(loc);
        gl.vertexAttribPointer(loc, 3, gl.FLOAT, false, 0, 0);
        gl.drawArrays(gl.POINTS, 0, count);
      } else {
        const ctx = canvas.getContext("2d");
        if (!ctx) return;
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = "rgba(34, 211, 238, 0.85)";
        const hw = canvas.width * 0.5;
        const hh = canvas.height * 0.5;
        for (let i = 0; i < count * 3; i += 3) {
          const px = hw + projected[i] * hw;
          const py = hh - projected[i + 1] * hh;
          ctx.fillRect(px, py, 2.2, 2.2);
        }
      }
    }

    return {
      setShape,
      setTransform,
      stepAndRender,
      getShape: () => activeShape,
      getTier: () => budget.tier,
    };
  }

  window.NuxivaSpatialHologram = { createEngine, SHAPES };
})();
