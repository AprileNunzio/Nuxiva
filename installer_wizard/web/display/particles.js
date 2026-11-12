(() => {
  const HEADER = 12;
  const MAX_POINTS = 65536;
  const DIGEST = /^[0-9a-f]{64}$/;
  const MORPH_MS = 1800;
  const FADE_MS = 1600;
  const TINT = [0.61, 0.9, 1];
  const reduced = () => window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const VERT = `#version 300 es
precision highp float;
in vec3 aFrom;
in vec3 aTo;
in vec3 aColFrom;
in vec3 aColTo;
in float aSeed;
uniform float uMix;
uniform float uTime;
uniform float uYaw;
uniform float uAspect;
uniform float uScale;
uniform float uBurst;
uniform float uSize;
uniform float uDrift;
out vec3 vCol;
out float vFade;
vec3 dir(float s) {
  float a = fract(sin(s * 91.7) * 43758.5453) * 6.2831853;
  float b = fract(sin(s * 37.3) * 24634.6345) * 2.0 - 1.0;
  float r = sqrt(1.0 - b * b);
  return vec3(r * cos(a), b, r * sin(a));
}
void main() {
  float local = clamp(uMix * 1.35 - aSeed * 0.35, 0.0, 1.0);
  float k = local * local * (3.0 - 2.0 * local);
  vec3 p = mix(aFrom, aTo, k);
  p += dir(aSeed) * (sin(local * 3.14159265) * 0.35 + uBurst * (1.2 + aSeed * 1.8));
  p += uDrift * 0.012 * vec3(sin(uTime * 1.3 + aSeed * 40.0), cos(uTime * 1.1 + aSeed * 23.0), sin(uTime * 0.9 + aSeed * 61.0));
  float c = cos(uYaw), s = sin(uYaw);
  p = vec3(c * p.x + s * p.z, p.y, -s * p.x + c * p.z);
  float t = 0.28;
  p = vec3(p.x, cos(t) * p.y - sin(t) * p.z, sin(t) * p.y + cos(t) * p.z);
  float depth = max(0.6, p.z + 3.2);
  gl_Position = vec4(p.x * uScale / uAspect, p.y * uScale, 0.0, depth * 0.5);
  gl_PointSize = uSize * (3.2 / depth);
  vCol = mix(aColFrom, aColTo, k);
  vFade = (1.0 - uBurst) * clamp(1.4 - depth * 0.25, 0.25, 1.0);
}`;

  const FRAG = `#version 300 es
precision mediump float;
in vec3 vCol;
in float vFade;
uniform float uAlpha;
out vec4 outColor;
void main() {
  vec2 d = gl_PointCoord * 2.0 - 1.0;
  float r = dot(d, d);
  if (r > 1.0) discard;
  float glow = exp(-r * 3.2);
  outColor = vec4(vCol * glow, glow * uAlpha * vFade);
}`;

  function decode(buffer) {
    if (!(buffer instanceof ArrayBuffer) || buffer.byteLength < HEADER) throw new TypeError("blob corto");
    const v = new DataView(buffer);
    if (v.getUint32(0, false) !== 0x4e585043 || v.getUint8(4) !== 1) throw new TypeError("intestazione");
    const flags = v.getUint8(5);
    if ((flags & ~1) !== 0 || v.getUint16(6, true) !== 0) throw new TypeError("flag");
    const n = v.getUint32(8, true);
    if (n === 0 || n > MAX_POINTS) throw new RangeError("punti");
    const colored = (flags & 1) === 1;
    if (buffer.byteLength !== HEADER + n * (colored ? 9 : 6)) throw new RangeError("lunghezza");
    const pos = new Float32Array(n * 3);
    const raw = new Int16Array(buffer.slice(HEADER, HEADER + n * 6));
    for (let i = 0; i < raw.length; i += 1) pos[i] = raw[i] / 32767;
    const col = new Float32Array(n * 3);
    if (colored) {
      const bytes = new Uint8Array(buffer, HEADER + n * 6, n * 3);
      for (let i = 0; i < bytes.length; i += 1) col[i] = bytes[i] / 255;
    } else {
      for (let i = 0; i < n; i += 1) col.set(TINT, i * 3);
    }
    return Object.freeze({ n, pos, col });
  }

  function dust(n) {
    const pos = new Float32Array(n * 3), col = new Float32Array(n * 3);
    const rnd = new Uint32Array(n * 3);
    for (let i = 0; i < rnd.length; i += 16384) crypto.getRandomValues(rnd.subarray(i, i + 16384));
    for (let i = 0; i < n; i += 1) {
      const a = (rnd[i * 3] / 4294967296) * Math.PI * 2;
      const b = (rnd[i * 3 + 1] / 4294967296) * 2 - 1;
      const r = 1.6 + (rnd[i * 3 + 2] / 4294967296) * 1.4;
      const q = Math.sqrt(1 - b * b);
      pos.set([r * q * Math.cos(a), r * b, r * q * Math.sin(a)], i * 3);
      col.set(TINT, i * 3);
    }
    return { n, pos, col };
  }

  function padded(cloud, n) {
    if (cloud.n === n) return cloud;
    const pos = new Float32Array(n * 3), col = new Float32Array(n * 3);
    for (let i = 0; i < n; i += 1) {
      const j = (i % cloud.n) * 3;
      pos.set(cloud.pos.subarray(j, j + 3), i * 3);
      col.set(cloud.col.subarray(j, j + 3), i * 3);
    }
    return { n, pos, col };
  }

  class Renderer {
    constructor(canvas) {
      this.canvas = canvas;
      this.gl = null;
      this.raf = 0;
      this.from = null;
      this.to = null;
      this.count = 0;
      this.morphAt = 0;
      this.fadeAt = 0;
      this.onDone = null;
      this.lost = false;
      canvas.addEventListener("webglcontextlost", (ev) => { ev.preventDefault(); this.lost = true; this.stop(); }, false);
      canvas.addEventListener("webglcontextrestored", () => { this.lost = false; this.gl = null; if (this.to) { this.init(); this.upload(); this.play(); } }, false);
    }

    init() {
      if (this.gl) return true;
      const gl = this.canvas.getContext("webgl2", { alpha: true, antialias: false, premultipliedAlpha: true, powerPreference: "low-power" });
      if (!gl) return false;
      const shader = (type, src) => {
        const s = gl.createShader(type);
        gl.shaderSource(s, src);
        gl.compileShader(s);
        if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s) || "shader");
        return s;
      };
      const prog = gl.createProgram();
      gl.attachShader(prog, shader(gl.VERTEX_SHADER, VERT));
      gl.attachShader(prog, shader(gl.FRAGMENT_SHADER, FRAG));
      gl.linkProgram(prog);
      if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(prog) || "link");
      this.gl = gl;
      this.prog = prog;
      this.vao = gl.createVertexArray();
      this.buffers = {};
      this.attrs = Object.fromEntries(["aFrom", "aTo", "aColFrom", "aColTo", "aSeed"].map((a) => [a, gl.getAttribLocation(prog, a)]));
      this.uniforms = Object.fromEntries(["uMix", "uTime", "uYaw", "uAspect", "uScale", "uBurst", "uSize", "uDrift", "uAlpha"].map((u) => [u, gl.getUniformLocation(prog, u)]));
      return true;
    }

    bind(name, data, size) {
      const gl = this.gl, loc = this.attrs[name];
      if (loc < 0) return;
      const buf = this.buffers[name] || (this.buffers[name] = gl.createBuffer());
      gl.bindBuffer(gl.ARRAY_BUFFER, buf);
      gl.bufferData(gl.ARRAY_BUFFER, data, gl.STATIC_DRAW);
      gl.enableVertexAttribArray(loc);
      gl.vertexAttribPointer(loc, size, gl.FLOAT, false, 0, 0);
    }

    upload() {
      const gl = this.gl, n = this.count;
      const from = padded(this.from, n), to = padded(this.to, n);
      const seed = new Float32Array(n);
      for (let i = 0; i < n; i += 1) seed[i] = ((i * 2654435761) >>> 0) / 4294967296;
      gl.bindVertexArray(this.vao);
      this.bind("aFrom", from.pos, 3);
      this.bind("aTo", to.pos, 3);
      this.bind("aColFrom", from.col, 3);
      this.bind("aColTo", to.col, 3);
      this.bind("aSeed", seed, 1);
      gl.bindVertexArray(null);
    }

    show(cloud) {
      if (this.lost || !this.init()) return false;
      const start = this.to ? this.current() : dust(cloud.n);
      this.from = start;
      this.to = cloud;
      this.count = Math.max(start.n, cloud.n);
      this.morphAt = reduced() ? performance.now() - MORPH_MS : performance.now();
      this.fadeAt = 0;
      this.onDone = null;
      this.upload();
      this.play();
      return true;
    }

    current() {
      return this.to;
    }

    dissolve(done) {
      if (!this.to || this.fadeAt) { if (!this.to && done) done(); return; }
      this.fadeAt = performance.now();
      this.onDone = done || null;
      if (reduced()) this.finish();
    }

    finish() {
      this.stop();
      this.to = null;
      this.from = null;
      this.fadeAt = 0;
      if (this.gl) this.gl.clear(this.gl.COLOR_BUFFER_BIT);
      const done = this.onDone;
      this.onDone = null;
      if (done) done();
    }

    play() {
      if (!this.raf && !document.hidden) this.raf = requestAnimationFrame((t) => this.frame(t));
    }

    stop() {
      cancelAnimationFrame(this.raf);
      this.raf = 0;
    }

    frame(now) {
      this.raf = 0;
      const gl = this.gl;
      if (!gl || !this.to || this.lost) return;
      const dpr = Math.min(2, window.devicePixelRatio || 1);
      const w = Math.round(this.canvas.clientWidth * dpr), h = Math.round(this.canvas.clientHeight * dpr);
      if (this.canvas.width !== w || this.canvas.height !== h) { this.canvas.width = w; this.canvas.height = h; }
      const still = reduced();
      const burst = this.fadeAt ? Math.min(1, (now - this.fadeAt) / FADE_MS) : 0;
      gl.viewport(0, 0, w, h);
      gl.clearColor(0, 0, 0, 0);
      gl.clear(gl.COLOR_BUFFER_BIT);
      gl.enable(gl.BLEND);
      gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
      gl.useProgram(this.prog);
      const u = this.uniforms;
      gl.uniform1f(u.uMix, Math.min(1, (now - this.morphAt) / MORPH_MS));
      gl.uniform1f(u.uTime, now / 1000);
      gl.uniform1f(u.uYaw, still ? 0.6 : now / 9000);
      gl.uniform1f(u.uAspect, w / Math.max(1, h));
      gl.uniform1f(u.uScale, 0.85);
      gl.uniform1f(u.uBurst, burst * burst);
      gl.uniform1f(u.uSize, Math.max(1.5, Math.min(5, 2.2 * dpr * (h / (1080 * dpr)) * 1.4)));
      gl.uniform1f(u.uDrift, still ? 0 : 1);
      gl.uniform1f(u.uAlpha, 0.9 * (1 - burst));
      gl.bindVertexArray(this.vao);
      gl.drawArrays(gl.POINTS, 0, this.count);
      gl.bindVertexArray(null);
      if (burst >= 1) { this.finish(); return; }
      this.play();
    }
  }

  const cache = new Map();
  let renderer = null;
  let showing = "";
  let wanted = "";
  let expireTimer = 0;
  let screen = 0;

  async function load(digest) {
    if (cache.has(digest)) return cache.get(digest);
    const r = await fetch(`/api/particles/blob/${digest}`, { credentials: "same-origin" });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const cloud = decode(await r.arrayBuffer());
    cache.set(digest, cloud);
    while (cache.size > 8) cache.delete(cache.keys().next().value);
    return cloud;
  }

  function setOn(on) {
    document.body.classList.toggle("particles-on", on);
  }

  function hide() {
    clearTimeout(expireTimer);
    wanted = "";
    if (!showing || !renderer) return;
    showing = "";
    renderer.dissolve(() => { if (!showing) setOn(false); });
  }

  async function update(p, myScreen = screen) {
    screen = myScreen;
    const valid = p && typeof p === "object" && typeof p.id === "string" && DIGEST.test(String(p.digest || ""));
    if (!valid || Number(p.screen) !== screen || !(Number(p.remaining) > 0)) { hide(); return; }
    if (p.id === showing || p.id === wanted) return;
    wanted = p.id;
    const canvas = document.getElementById("particles");
    if (!canvas) return;
    try {
      const cloud = await load(p.digest);
      if (wanted !== p.id) return;
      renderer = renderer || new Renderer(canvas);
      if (!renderer.show(cloud)) return;
      showing = p.id;
      setOn(true);
      clearTimeout(expireTimer);
      expireTimer = setTimeout(hide, Math.min(600, Number(p.remaining)) * 1000);
    } catch (err) {
      wanted = "";
      console.info("Animazione a particelle non mostrata:", err.message);
    }
  }

  document.addEventListener("visibilitychange", () => { if (!document.hidden && renderer && showing) renderer.play(); });
  window.NuxivaParticles = Object.freeze({ update, hide, decode, get showing() { return showing; } });
})();
