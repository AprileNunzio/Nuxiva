(() => {
  const SCOPE = "web/display/xr", POLL_MS = 5000, DEVICE_KEY = "nuxiva_xr_device";
  const $ = (id) => document.getElementById(id);
  const t = (key, params) => (window.PageText ? PageText.t(SCOPE, key, params) : "") || key;
  const params = new URLSearchParams(location.search);
  const kind = ["holo_quilt", "holo_pyramid"].includes(params.get("kind")) ? params.get("kind") : "xr_headset";
  const state = { paired: false, nucleusOnly: true, molecule: "", panelsSig: "", session: null };

  function status(key, warn) {
    const el = $("xr-status");
    if (window.PageText) PageText.bind(el, key); else el.textContent = key;
    el.textContent = t(key);
    el.classList.toggle("warn", !!warn);
  }

  function deviceId() {
    let id = "";
    try { id = localStorage.getItem(DEVICE_KEY) || ""; } catch (err) { console.warn("Memoria locale non disponibile", err); }
    if (/^[A-Za-z0-9_-]{8,64}$/.test(id)) return id;
    const bytes = crypto.getRandomValues(new Uint8Array(24));
    id = btoa(String.fromCharCode(...bytes)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
    try { localStorage.setItem(DEVICE_KEY, id); } catch (err) { console.warn("Identità del visore non salvata", err); }
    return id;
  }

  async function redeem(code) {
    const res = await fetch("/api/xr/redeem", { method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-Nuxiva-Request": "1" },
      body: JSON.stringify({ code, device: deviceId(), name: navigator.userAgent.includes("Quest") ? "Meta Quest" : "Visore" }) });
    history.replaceState(null, "", location.pathname + (kind !== "xr_headset" ? `?kind=${kind}` : ""));
    if (!res.ok) throw new Error(res.status === 403 ? "status_code_refused" : "status_pair_failed");
  }

  const THREE = window.THREE;
  const canvas = $("xr-canvas");
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
  renderer.xr.enabled = kind === "xr_headset";
  const scene = new THREE.Scene(), camera = new THREE.PerspectiveCamera(50, 1, 0.01, 100);
  camera.position.set(0, 0, 4);
  const controls = new THREE.OrbitControls(camera, canvas);
  controls.enableDamping = true;
  const nucleus = new THREE.Mesh(new THREE.SphereBufferGeometry(0.18, 48, 32),
    new THREE.MeshBasicMaterial({ color: 0x29e0ff, transparent: true, opacity: 0.85 }));
  const halo = new THREE.Mesh(new THREE.SphereBufferGeometry(0.3, 32, 24),
    new THREE.MeshBasicMaterial({ color: 0x29e0ff, transparent: true, opacity: 0.15, blending: THREE.AdditiveBlending, depthWrite: false }));
  nucleus.add(halo);
  const stage = new THREE.Group(), panels = new THREE.Group(), molecule = new THREE.Group();
  stage.add(nucleus, panels, molecule);
  scene.add(stage);
  const hands = renderer.xr.enabled ? NuxivaXrHands.create(renderer, molecule) : null;
  const holo = NuxivaMultiview.create(THREE, renderer, kind, null);
  if (holo) document.body.classList.add("holo");

  function place(immersive) {
    nucleus.position.set(0, immersive ? 1.5 : 1.25, immersive ? -1.2 : 0);
    molecule.position.set(0, immersive ? 1.3 : 0, immersive ? -0.9 : 0);
  }
  place(false);

  async function showMolecule(id) {
    if (id === state.molecule) return;
    state.molecule = id;
    molecule.children.slice().forEach((child) => { molecule.remove(child); NuxivaMolecule.release(child); });
    if (!id) return;
    try {
      const data = await NuxivaMolecule.fetchScene(id, "atoms", "chain");
      if (state.molecule !== id) return;
      const { group, radius } = NuxivaMolecule.build(data, THREE);
      const scale = (state.session ? 0.35 : 1.2) / radius;
      group.scale.setScalar(scale);
      group.children[0].material.uniforms.uScale.value = scale;
      molecule.add(group);
    } catch (err) {
      console.warn("Molecola non disponibile nel visore", err);
      state.molecule = "";
    }
  }

  function list(items) {
    const ul = $("xr-panels");
    ul.replaceChildren(...items.map((p) => { const li = document.createElement("li"); li.textContent = `${p.icon || ""} ${p.name || p.id}`; return li; }));
  }

  async function poll() {
    try {
      const res = await fetch("/api/xr/scene", { credentials: "same-origin" });
      if (res.status === 401) { state.paired = false; status("status_unpaired", true); return; }
      if (!res.ok) throw new Error(String(res.status));
      const scene = await res.json();
      state.paired = true;
      state.nucleusOnly = !!scene.nucleus_only;
      status(state.nucleusOnly ? "status_nucleus_only" : "status_ready", false);
      const items = state.nucleusOnly ? [] : scene.panels || [];
      const sig = JSON.stringify(items.map((p) => [p.key, p.name]));
      if (sig !== state.panelsSig) {
        state.panelsSig = sig;
        NuxivaXrPanels.arrange(THREE, panels, items, !!state.session);
        list(items);
      }
      const mol = items.find((p) => p.molecule);
      showMolecule(mol ? mol.molecule : "");
    } catch (err) {
      console.warn("Scena del visore non aggiornata", err);
      status("status_offline", true);
    }
  }

  async function enter(mode) {
    const session = await navigator.xr.requestSession(mode, { optionalFeatures: ["local-floor", "hand-tracking"] });
    renderer.xr.setReferenceSpaceType("local-floor");
    await renderer.xr.setSession(session);
    state.session = session;
    place(true);
    state.panelsSig = "";
    session.addEventListener("end", () => { state.session = null; place(false); state.panelsSig = ""; poll(); });
    poll();
  }

  async function offerXr() {
    if (!renderer.xr.enabled || !navigator.xr) return;
    for (const [mode, id] of [["immersive-vr", "xr-vr"], ["immersive-ar", "xr-ar"]]) {
      const supported = await navigator.xr.isSessionSupported(mode).catch(() => false);
      const button = $(id);
      button.hidden = !supported;
      button.onclick = () => enter(mode).catch((err) => { console.warn("Sessione immersiva non avviata", err); status("status_xr_failed", true); });
    }
  }

  function resize() {
    const w = window.innerWidth, h = window.innerHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / Math.max(1, h);
    camera.updateProjectionMatrix();
  }

  renderer.setAnimationLoop((time) => {
    const pulse = 1 + Math.sin(time / 600) * 0.04;
    nucleus.scale.setScalar(pulse);
    if (!state.session) { molecule.rotation.y += 0.003; controls.update(); }
    if (hands && state.session) hands.update();
    if (holo && !state.session) holo.render(scene, camera); else renderer.render(scene, camera);
  });
  window.addEventListener("resize", resize);
  resize();

  (async () => {
    const code = params.get("pair");
    if (code && /^\d{8}$/.test(code)) {
      try { await redeem(code); } catch (err) { status(err.message, true); }
    }
    await poll();
    await offerXr();
    setInterval(poll, POLL_MS);
  })();
})();
