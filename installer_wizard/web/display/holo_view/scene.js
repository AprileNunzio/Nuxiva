(() => {
  const V = window.NUXIVA_ASSET_V ? `?v=${window.NUXIVA_ASSET_V}` : "";
  const loaded = {};
  const ZOOM = [0.35, 4.5];

  const script = (name) => loaded[name] || (loaded[name] = new Promise((ok, ko) => {
    const s = document.createElement("script");
    s.src = `/vendor/${name}${V}`;
    s.onload = ok;
    s.onerror = () => ko(new Error(`vendor ${name}`));
    document.head.appendChild(s);
  }));

  const POST = ["CopyShader.js", "LuminosityHighPassShader.js", "GammaCorrectionShader.js", "EffectComposer.js", "RenderPass.js",
    "ShaderPass.js", "UnrealBloomPass.js"];

  async function ensure() {
    if (!window.THREE) await script("three.min.js");
    if (!THREE.RoomEnvironment) await script("RoomEnvironment.js");
  }

  async function post(renderer, scene, camera) {
    try {
      for (const name of POST) await script(name);
    } catch (err) {
      console.info("Bloom non disponibile, rendering senza post-produzione:", err.message);
      return null;
    }
    const composer = new THREE.EffectComposer(renderer);
    composer.addPass(new THREE.RenderPass(scene, camera));
    composer.addPass(new THREE.UnrealBloomPass(new THREE.Vector2(512, 512), 0.32, 0.4, 0.92));
    composer.addPass(new THREE.ShaderPass(THREE.GammaCorrectionShader));
    return composer;
  }

  function lights(THREE, scene) {
    scene.add(new THREE.HemisphereLight(0xcfe9ff, 0x0b1020, 0.55));
    const key = new THREE.DirectionalLight(0xffffff, 2.4);
    key.position.set(2.6, 4.2, 3.1);
    key.castShadow = true;
    key.shadow.mapSize.set(2048, 2048);
    key.shadow.camera.left = -2.2;
    key.shadow.camera.right = 2.2;
    key.shadow.camera.top = 2.2;
    key.shadow.camera.bottom = -2.2;
    key.shadow.bias = -0.0004;
    scene.add(key);
    const rim = new THREE.DirectionalLight(0x5ef2ff, 1.3);
    rim.position.set(-3, 1.5, -2.5);
    scene.add(rim);
    const ground = new THREE.Mesh(new THREE.CircleGeometry(2.6, 96), new THREE.ShadowMaterial({ opacity: 0.32 }));
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = -1.15;
    ground.receiveShadow = true;
    scene.add(ground);
  }

  async function create(canvas, labelLayer) {
    await ensure();
    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: "high-performance" });
    renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
    renderer.outputEncoding = THREE.sRGBEncoding;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.15;
    renderer.physicallyCorrectLights = true;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x020409);
    const pmrem = new THREE.PMREMGenerator(renderer);
    scene.environment = pmrem.fromScene(new THREE.RoomEnvironment(), 0.04).texture;
    const camera = new THREE.PerspectiveCamera(38, 1, 0.05, 60);
    lights(THREE, scene);
    const composer = await post(renderer, scene, camera);
    const root = new THREE.Group();
    const pivot = new THREE.Group();
    pivot.add(root);
    scene.add(pivot);

    const st = { parts: [], layers: 1, anatomy: false, explode: 0, explodeTarget: 0, animate: true, yaw: 0.5, pitch: 0.22,
                 zoom: 1, pan: [0, 0], touched: 0, raf: 0, last: 0, labels: [], asset: null, ticket: 0 };

    function dispose() {
      for (const holder of st.parts) {
        holder.userData.mesh.geometry.dispose();
        holder.userData.mesh.material.dispose();
        root.remove(holder);
      }
      st.parts = [];
      if (st.asset) {
        root.remove(st.asset.root);
        st.asset.root.traverse((node) => {
          if (!node.isMesh) return;
          node.geometry.dispose();
          [].concat(node.material).forEach((m) => m && m.dispose());
        });
        st.asset = null;
      }
      labelLayer.textContent = "";
      st.labels = [];
    }

    function styleLayer(holder) {
      const { part, mesh } = holder.userData;
      const outer = st.anatomy && part.layer < st.layers - 1;
      mesh.material.transparent = outer || Boolean(part.soft);
      mesh.material.opacity = outer ? 0.16 + 0.08 * part.layer : (part.soft ? 0.38 : 1);
      mesh.material.depthWrite = !outer;
      mesh.material.emissiveIntensity = st.anatomy && !outer ? 1.5 : 1;
      mesh.castShadow = !outer && !part.soft;
      mesh.material.needsUpdate = true;
    }

    function labelsFor() {
      labelLayer.textContent = "";
      st.labels = [];
      if (!st.anatomy) return;
      const groups = new Map();
      for (const holder of st.parts) {
        const { part } = holder.userData;
        if (!part.label) continue;
        if (!groups.has(part.label)) groups.set(part.label, []);
        groups.get(part.label).push(holder);
      }
      const names = [...groups.keys()].slice(0, 14);
      names.forEach((label, k) => {
        const target = names.length > 1 ? -0.8 + (1.6 * k) / (names.length - 1) : 0;
        const holder = groups.get(label).reduce((best, h) => (Math.abs(h.userData.part.at[1] - target) < Math.abs(best.userData.part.at[1] - target) ? h : best));
        const { part } = holder.userData;
        const el = document.createElement("div");
        el.className = "holo-label";
        const name = document.createElement("b");
        name.textContent = part.label;
        el.appendChild(name);
        if (part.info) {
          const info = document.createElement("span");
          info.textContent = part.info;
          el.appendChild(info);
        }
        labelLayer.appendChild(el);
        st.labels.push({ el, holder });
      });
    }

    async function load(data) {
      dispose();
      const ticket = ++st.ticket;
      if (data.asset && data.asset.url) {
        const asset = await window.NuxivaHoloAsset.load(THREE, data.asset.url);
        if (ticket !== st.ticket) return;
        st.asset = asset;
        root.add(asset.root);
        window.NuxivaHoloAsset.style(asset, st.anatomy);
        play();
        return;
      }
      st.layers = Math.max(1, Number(data.layers) || 1);
      for (const part of data.parts || []) {
        const holder = window.NuxivaHoloGeometry.build(THREE, part, data.euler);
        root.add(holder);
        st.parts.push(holder);
      }
      st.parts.forEach(styleLayer);
      labelsFor();
      play();
    }

    function setAnatomy(on) {
      st.anatomy = Boolean(on);
      st.explodeTarget = st.anatomy ? Math.max(st.explodeTarget, 0.55) : 0;
      st.parts.forEach(styleLayer);
      if (st.asset) window.NuxivaHoloAsset.style(st.asset, st.anatomy);
      labelsFor();
    }

    function adjust(d) {
      st.yaw += d.yaw || 0;
      st.pitch = Math.max(-1.35, Math.min(1.35, st.pitch + (d.pitch || 0)));
      st.zoom = Math.max(ZOOM[0], Math.min(ZOOM[1], st.zoom * (d.zoom || 1)));
      st.pan = [Math.max(-1.5, Math.min(1.5, st.pan[0] + (d.px || 0))), Math.max(-1.5, Math.min(1.5, st.pan[1] + (d.py || 0)))];
      if (typeof d.explode === "number") st.explodeTarget = Math.max(0, Math.min(1, d.explode));
      st.touched = performance.now();
    }

    function reset() {
      Object.assign(st, { yaw: 0.5, pitch: 0.22, zoom: 1, pan: [0, 0], touched: 0 });
    }

    function animateParts(t) {
      st.explode += (st.explodeTarget - st.explode) * 0.12;
      for (const holder of st.parts) {
        const { part, mesh, base, baseScale, phase } = holder.userData;
        const e = part.explode || [0, 0, 0];
        let [x, y, z] = [base[0] + e[0] * st.explode, base[1] + e[1] * st.explode, base[2] + e[2] * st.explode];
        if (st.animate && part.motion === "orbit") {
          const a = t * 0.6 + phase;
          const r = Math.hypot(x, z);
          x = Math.cos(a) * r;
          z = Math.sin(a) * r;
        }
        holder.position.set(x, y, z);
        const pulse = st.animate && part.motion === "pulse" ? 1 + Math.sin(t * Math.PI * 2 * 1.15 + phase) * 0.055 : 1;
        mesh.scale.set(baseScale[0] * pulse, baseScale[1] * pulse, baseScale[2] * pulse);
        if (st.animate && part.motion === "spin") mesh.rotation.y = t * 1.6 + phase;
        if (st.animate && part.motion === "sway") mesh.rotation.z = Math.sin(t * 1.3 + phase) * 0.12;
      }
    }

    function placeLabels(w, h) {
      const v = new THREE.Vector3();
      for (const { el, holder } of st.labels) {
        holder.getWorldPosition(v);
        v.project(camera);
        const hidden = v.z > 1;
        el.style.display = hidden ? "none" : "";
        el.style.transform = `translate(${((v.x + 1) / 2) * w}px, ${((1 - v.y) / 2) * h}px)`;
      }
    }

    function frame(now) {
      st.raf = 0;
      const w = canvas.clientWidth || window.innerWidth;
      const h = canvas.clientHeight || window.innerHeight;
      if (canvas.width !== Math.round(w * renderer.getPixelRatio()) || canvas.height !== Math.round(h * renderer.getPixelRatio())) {
        renderer.setSize(w, h, false);
        if (composer) composer.setSize(w, h);
        camera.aspect = w / Math.max(1, h);
        camera.updateProjectionMatrix();
      }
      const t = now / 1000;
      const dt = st.last ? Math.min(0.05, t - st.last) : 0;
      st.last = t;
      if (st.animate && now - st.touched > 4000) st.yaw += dt * 0.25;
      pivot.rotation.set(st.pitch, st.yaw, 0, "XYZ");
      pivot.position.set(st.pan[0], st.pan[1], 0);
      camera.position.set(0, 0.3, 4.4 / st.zoom);
      camera.lookAt(st.pan[0] * 0.2, st.pan[1] * 0.2, 0);
      animateParts(t);
      if (st.asset) {
        if (st.asset.mixer && st.animate) st.asset.mixer.update(dt);
        if (Math.abs(st.explode - (st.asset.spread || 0)) > 1e-3) {
          st.asset.spread = st.explode;
          window.NuxivaHoloAsset.explode(st.asset, st.explode);
        }
      }
      if (composer) composer.render();
      else renderer.render(scene, camera);
      placeLabels(w, h);
      play();
    }

    function play() {
      if (!st.raf && !document.hidden && (st.parts.length || st.asset)) st.raf = requestAnimationFrame(frame);
    }

    function stop() {
      cancelAnimationFrame(st.raf);
      st.raf = 0;
    }

    return {
      load, setAnatomy, adjust, reset, play, stop, dispose,
      toggleExplode: () => { st.explodeTarget = st.explodeTarget > 0.25 ? 0 : 0.65; st.touched = performance.now(); },
      setExplode: (v) => { st.explodeTarget = Math.max(0, Math.min(1, v)); },
      setAnimate: (on) => { st.animate = Boolean(on); },
    };
  }

  window.NuxivaHoloScene = Object.freeze({ create });
})();
