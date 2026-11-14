(() => {
  const LAB = (window.NuxivaLab = window.NuxivaLab || {});

  function create(textures, spec) {
    const std = (o) => new THREE.MeshStandardMaterial(o);
    const phys = (o) => new THREE.MeshPhysicalMaterial(o);
    const floor = textures.set("floor", [6, 5]);
    const wall = textures.set("wall", [4, 2]);
    const wood = textures.set("wood", [1, 1]);
    const metal = textures.set("metal", [1, 1]);
    const fabric = textures.set("fabric", [2, 2]);
    const hq = spec.rank >= 2;
    const m = {
      floor: (hq ? phys : std)({ ...floor, color: 0xffffff, roughness: 0.55, metalness: 0.05, normalScale: new THREE.Vector2(0.6, 0.6), ...(hq ? { clearcoat: 0.35, clearcoatRoughness: 0.25 } : {}) }),
      wall: std({ ...wall, color: 0xffffff, roughness: 0.9, metalness: 0, normalScale: new THREE.Vector2(0.35, 0.35) }),
      wallDark: std({ color: 0x2b3340, roughness: 0.85, metalness: 0.05 }),
      base: std({ color: 0x59606c, roughness: 0.6, metalness: 0.2 }),
      wood: std({ ...wood, color: 0xffffff, roughness: 0.62, metalness: 0, normalScale: new THREE.Vector2(0.5, 0.5) }),
      steel: std({ ...metal, color: 0xdfe5ec, roughness: 0.42, metalness: 0.85 }),
      steelDark: std({ color: 0x20262e, roughness: 0.45, metalness: 0.8 }),
      plastic: std({ color: 0x14181e, roughness: 0.5, metalness: 0.1 }),
      plasticLight: std({ color: 0xe8ecf1, roughness: 0.45, metalness: 0.05 }),
      fabric: std({ ...fabric, color: 0x3b4a63, roughness: 0.95, metalness: 0, normalScale: new THREE.Vector2(0.8, 0.8) }),
      fabricAlt: std({ ...fabric, color: 0x2b5d57, roughness: 0.95, metalness: 0, normalScale: new THREE.Vector2(0.8, 0.8) }),
      rubber: std({ color: 0x0b0d10, roughness: 0.85, metalness: 0 }),
      ceramic: std({ color: 0xf4f1ea, roughness: 0.25, metalness: 0 }),
      leaf: std({ color: 0x2f9d62, roughness: 0.7, metalness: 0 }),
      leafLight: std({ color: 0x57c98a, roughness: 0.7, metalness: 0 }),
      soil: std({ color: 0x3a2a1e, roughness: 1, metalness: 0 }),
      pot: std({ color: 0xd9d4c8, roughness: 0.55, metalness: 0 }),
      glass: (hq ? phys : std)({ color: 0x9fd8ff, roughness: 0.05, metalness: 0, transparent: true, opacity: 0.18, depthWrite: false, side: THREE.DoubleSide }),
      rug: std({ ...fabric, color: 0x1d3a5c, roughness: 1, metalness: 0 }),
      glowCyan: new THREE.MeshBasicMaterial({ color: 0x29e0ff, transparent: true, opacity: 0.85 }),
      holo: new THREE.MeshBasicMaterial({ color: 0x38bdf8, wireframe: true, transparent: true, opacity: 0.7 }),
      holoCore: new THREE.MeshBasicMaterial({ color: 0x0ea5e9, transparent: true, opacity: 0.18 }),
      bulb: std({ color: 0xfff1c9, emissive: 0xffe2a0, emissiveIntensity: 1.6, roughness: 0.4 }),
      panelLight: std({ color: 0xffffff, emissive: 0xf4f8ff, emissiveIntensity: 1.4, roughness: 0.6 }),
      alarmOff: std({ color: 0x5a1a22, emissive: 0x000000, roughness: 0.4 }),
      alarmOn: std({ color: 0xff2e4d, emissive: 0xff1a3c, emissiveIntensity: 2.2, roughness: 0.4 }),
    };
    return {
      m,
      dispose() { Object.values(m).forEach((x) => x.dispose()); },
    };
  }

  LAB.materials = Object.freeze({ create });
})();
