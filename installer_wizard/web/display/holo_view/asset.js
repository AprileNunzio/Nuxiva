(() => {
  const GENERIC = /^(mesh|object|node|group|scene|root|geometry|polysurface|default|material)?[\s_.-]*\d*$/i;
  const OUTER_SHARE = 0.3;

  function loader(THREE) {
    return new Promise((ok, ko) => {
      if (THREE.GLTFLoader) { ok(new THREE.GLTFLoader()); return; }
      const s = document.createElement("script");
      s.src = `/vendor/GLTFLoader.js${window.NUXIVA_ASSET_V ? `?v=${window.NUXIVA_ASSET_V}` : ""}`;
      s.onload = () => ok(new THREE.GLTFLoader());
      s.onerror = () => ko(new Error("vendor GLTFLoader.js"));
      document.head.appendChild(s);
    });
  }

  function fit(THREE, object) {
    const box = new THREE.Box3().setFromObject(object);
    const size = box.getSize(new THREE.Vector3());
    const center = box.getCenter(new THREE.Vector3());
    const scale = 2 / Math.max(1e-6, size.x, size.y, size.z);
    object.position.sub(center.multiplyScalar(scale));
    object.scale.multiplyScalar(scale);
  }

  function pieces(THREE, root) {
    const list = [];
    root.updateMatrixWorld(true);
    root.traverse((node) => {
      if (!node.isMesh) return;
      node.castShadow = true;
      node.receiveShadow = true;
      const box = new THREE.Box3().setFromObject(node);
      const size = box.getSize(new THREE.Vector3());
      const center = box.getCenter(new THREE.Vector3());
      const dir = center.lengthSq() > 1e-4 ? center.clone().normalize() : new THREE.Vector3(0, 1, 0);
      const label = String(node.name || "").replace(/[_.]+/g, " ").trim();
      list.push({ mesh: node, base: node.position.clone(), dir, volume: size.x * size.y * size.z,
                  label: GENERIC.test(label) ? "" : label.slice(0, 48), materials: [].concat(node.material) });
    });
    const sorted = [...list].sort((a, b) => b.volume - a.volume);
    const outer = new Set(sorted.slice(0, Math.max(1, Math.floor(sorted.length * OUTER_SHARE))).filter(() => sorted.length > 2));
    list.forEach((p) => { p.outer = outer.has(p); });
    return list;
  }

  async function load(THREE, url) {
    const gltf = await (await loader(THREE)).loadAsync(url);
    const root = gltf.scene;
    fit(THREE, root);
    const mixer = gltf.animations && gltf.animations.length ? new THREE.AnimationMixer(root) : null;
    if (mixer) gltf.animations.forEach((clip) => mixer.clipAction(clip).play());
    return { root, mixer, pieces: pieces(THREE, root), clips: (gltf.animations || []).length };
  }

  function style(asset, anatomy) {
    for (const p of asset.pieces) {
      const ghost = anatomy && p.outer;
      for (const m of p.materials) {
        if (!m) continue;
        if (m.userData.holoOpacity === undefined) m.userData.holoOpacity = { t: m.transparent, o: m.opacity, d: m.depthWrite };
        const saved = m.userData.holoOpacity;
        m.transparent = ghost || saved.t;
        m.opacity = ghost ? 0.22 : saved.o;
        m.depthWrite = ghost ? false : saved.d;
        m.needsUpdate = true;
      }
    }
  }

  function explode(asset, amount) {
    for (const p of asset.pieces) {
      if (!p.mesh.parent) continue;
      const push = p.dir.clone().multiplyScalar(amount * 0.6);
      p.mesh.parent.worldToLocal(push.add(p.mesh.parent.localToWorld(p.base.clone())));
      p.mesh.position.copy(push);
    }
  }

  window.NuxivaHoloAsset = Object.freeze({ load, style, explode });
})();
