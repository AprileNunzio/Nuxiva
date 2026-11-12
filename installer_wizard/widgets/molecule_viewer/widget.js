(() => {
  const VER = window.NUXIVA_ASSET_V ? `?v=${window.NUXIVA_ASSET_V}` : "";
  const SCHEMES = ["element", "chain", "secondary"];
  const loaded = {};
  const load = (src) => loaded[src] || (loaded[src] = new Promise((ok, ko) => {
    const s = document.createElement("script");
    s.src = `${src}${VER}`; s.onload = ok; s.onerror = () => ko(new Error("library"));
    document.head.appendChild(s);
  }));

  async function ensure() {
    if (!window.THREE) await load("/vendor/three.min.js");
    if (!THREE.OrbitControls) await load("/vendor/OrbitControls.js");
    if (!window.NuxivaMolecule) await load("/static/display/kernel/molecule/impostor.js");
  }

  function dispose(st) {
    st.alive = false;
    cancelAnimationFrame(st.raf);
    if (st.scene) st.scene.traverse((o) => { if (o.geometry) o.geometry.dispose(); if (o.material) o.material.dispose(); });
    if (st.controls) st.controls.dispose();
    if (st.renderer) st.renderer.dispose();
  }

  async function draw(st, ctx) {
    const data = await NuxivaMolecule.fetchScene(st.id, st.lod, st.scheme);
    if (!st.alive) return;
    if (st.model) { st.pivot.remove(st.model); NuxivaMolecule.release(st.model); }
    const { group, radius } = NuxivaMolecule.build(data, THREE);
    st.model = group;
    st.pivot.add(group);
    const scale = 1.6 / radius;
    st.pivot.scale.setScalar(scale);
    group.children[0].material.uniforms.uScale.value = scale;
    st.stats.textContent = `${ctx.count("atoms", data.atoms)} · ${ctx.count("bonds", data.bonds)}`;
  }

  function mount(el, raw, ctx) {
    if (el._mol) dispose(el._mol);
    const d = raw && typeof raw === "object" ? raw : {};
    const id = /^[0-9a-f]{16}$/.test(String(d.id || "")) ? d.id : "";
    el.innerHTML = `${ctx.head({ icon: "cube", label: ctx.t("label"), title: String(d.title || "").slice(0, 80) })}
      <div class="mol-stage"><canvas></canvas><div class="mol-msg">${ctx.esc(ctx.t("loading"))}</div>
        <div class="mol-tools">${SCHEMES.map((s) => `<button class="wk-btn" type="button" data-scheme="${s}" aria-pressed="false">${ctx.esc(ctx.t(`scheme_${s}`))}</button>`).join("")}
          <button class="wk-btn" type="button" data-a="lod" aria-pressed="false">${ctx.esc(ctx.t("backbone"))}</button>
          <button class="wk-btn icon on" type="button" data-a="spin" aria-pressed="true" title="${ctx.esc(ctx.t("spin"))}">${ctx.icon("refresh")}</button></div></div>
      <div class="mol-info"><span class="mol-stats"></span></div>`;
    const st = { el, id, alive: true, scheme: "element", lod: d.lod === "backbone" ? "backbone" : "atoms", spin: true, stats: el.querySelector(".mol-stats") };
    el._mol = st;
    const fail = (err) => {
      const m = el.querySelector(".mol-msg");
      if (!m) return;
      m.textContent = ctx.t(["engine", "library", "data"].includes(err.message) ? `error_${err.message}` : "error_data");
      m.classList.add("err");
    };
    if (!id) { fail(new Error("data")); return; }
    start(st, ctx).catch(fail);
  }

  async function start(st, ctx) {
    await ensure();
    if (!st.alive) return;
    const stage = st.el.querySelector(".mol-stage"), canvas = stage.querySelector("canvas");
    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
    const scene = new THREE.Scene(), camera = new THREE.PerspectiveCamera(40, 1, 0.01, 100);
    st.pivot = new THREE.Group();
    scene.add(st.pivot);
    const controls = new THREE.OrbitControls(camera, canvas);
    controls.enableDamping = true; controls.autoRotate = true; controls.autoRotateSpeed = 1.2;
    camera.position.set(0, 0, 4.4); controls.update();
    Object.assign(st, { renderer, scene, controls });
    const tools = stage.querySelector(".mol-tools");
    const mark = () => {
      tools.querySelectorAll("[data-scheme]").forEach((b) => { const on = b.dataset.scheme === st.scheme; b.classList.toggle("on", on); b.setAttribute("aria-pressed", String(on)); });
      const lod = tools.querySelector('[data-a="lod"]'); lod.classList.toggle("on", st.lod === "backbone"); lod.setAttribute("aria-pressed", String(st.lod === "backbone"));
      const spin = tools.querySelector('[data-a="spin"]'); spin.classList.toggle("on", st.spin); spin.setAttribute("aria-pressed", String(st.spin));
    };
    const redraw = () => draw(st, ctx).catch((err) => console.warn("Molecola non aggiornata", err));
    controls.addEventListener("start", () => { controls.autoRotate = st.spin = false; mark(); });
    tools.onclick = (e) => {
      const b = e.target.closest("button");
      if (!b) return;
      if (b.dataset.scheme) { st.scheme = b.dataset.scheme; redraw(); }
      if (b.dataset.a === "lod") { st.lod = st.lod === "backbone" ? "atoms" : "backbone"; redraw(); }
      if (b.dataset.a === "spin") controls.autoRotate = st.spin = !st.spin;
      mark();
    };
    mark();
    await draw(st, ctx);
    const msg = st.el.querySelector(".mol-msg");
    if (msg) msg.remove();
    const frame = () => {
      if (!st.alive || !st.el.isConnected) { dispose(st); return; }
      st.raf = requestAnimationFrame(frame);
      if (document.hidden) return;
      const w = stage.clientWidth, h = stage.clientHeight, ratio = renderer.getPixelRatio();
      if (canvas.width !== Math.floor(w * ratio) || canvas.height !== Math.floor(h * ratio)) {
        renderer.setSize(w, h, false); camera.aspect = w / Math.max(1, h); camera.updateProjectionMatrix();
      }
      controls.update();
      renderer.render(scene, camera);
    };
    frame();
  }

  NuxivaDesk.register("molecule_viewer", {
    render(el, d, ctx) { mount(el, d, ctx); },
    update(el, d, ctx) { if (el._mol && el._mol.alive && d && el._mol.id === d.id) return; mount(el, d, ctx); },
    destroy(el) { if (el._mol) { dispose(el._mol); el._mol = null; } },
  });
})();
