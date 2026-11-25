(() => {
  const SEG = 64;

  function curve(THREE, kind) {
    const C = class extends THREE.Curve {
      getPoint(t, target = new THREE.Vector3()) {
        if (kind === "helix") {
          const a = t * Math.PI * 2 * 3;
          return target.set(Math.cos(a), t * 2 - 1, Math.sin(a));
        }
        const a = t * 5.2;
        return target.set(t * Math.cos(a), 0, t * Math.sin(a));
      }
    };
    return new C();
  }

  function capsule(THREE, r, half) {
    const body = Math.max(0, half - r);
    const pts = [];
    for (let i = 0; i <= 16; i += 1) {
      const a = -Math.PI / 2 + (i / 16) * (Math.PI / 2);
      pts.push(new THREE.Vector2(Math.cos(a) * r, Math.sin(a) * r - body));
    }
    for (let i = 0; i <= 16; i += 1) {
      const a = (i / 16) * (Math.PI / 2);
      pts.push(new THREE.Vector2(Math.cos(a) * r, Math.sin(a) * r + body));
    }
    return new THREE.LatheGeometry(pts, SEG);
  }

  function wedge(THREE) {
    const shape = new THREE.Shape();
    shape.moveTo(-1, -1);
    shape.lineTo(1, -1);
    shape.lineTo(-1, 1);
    shape.lineTo(-1, -1);
    const g = new THREE.ExtrudeGeometry(shape, { depth: 2, bevelEnabled: false });
    g.translate(0, 0, -1);
    return g;
  }

  function geometry(THREE, part) {
    const [hx, hy, hz] = part.half;
    const tube = Math.max(0.02, Math.min(0.9, part.tube || 0.25));
    switch (part.shape) {
      case "box": return { g: new THREE.BoxGeometry(2, 2, 2, 2, 2, 2), s: [hx, hy, hz] };
      case "wedge": return { g: wedge(THREE), s: [hx, hy, hz] };
      case "cylinder": return { g: new THREE.CylinderGeometry(1, 1, 2, SEG, 1), s: [hx, hy, hz] };
      case "cone": return { g: new THREE.ConeGeometry(1, 2, SEG, 1), s: [hx, hy, hz] };
      case "capsule": return { g: capsule(THREE, hx, hy), s: [1, 1, hz / Math.max(1e-4, hx)] };
      case "torus": {
        const g = new THREE.TorusGeometry(1 - tube, tube, 32, SEG * 2);
        g.rotateX(Math.PI / 2);
        return { g, s: [hx, hy / tube, hz] };
      }
      case "helix": return { g: new THREE.TubeGeometry(curve(THREE, "helix"), 360, tube, 12, false), s: [hx, hy, hz] };
      case "spiral": return { g: new THREE.TubeGeometry(curve(THREE, "spiral"), 240, tube, 10, false), s: [hx, hy / Math.max(tube, 0.01), hz] };
      default: return { g: new THREE.SphereGeometry(1, SEG, SEG / 2), s: [hx, hy, hz] };
    }
  }

  function material(THREE, part) {
    const color = new THREE.Color(part.color || "#5ef2ff").convertSRGBToLinear();
    const metal = Math.max(0, Math.min(1, Number(part.metal) || 0));
    return new THREE.MeshPhysicalMaterial({
      color,
      metalness: metal,
      roughness: Math.max(0.04, Math.min(1, Number(part.rough) || 0.5)),
      clearcoat: metal > 0.5 ? 0.85 : 0.35,
      clearcoatRoughness: 0.18,
      emissive: color.clone().multiplyScalar(0.06),
      transparent: Boolean(part.soft),
      opacity: part.soft ? 0.38 : 1,
      side: part.soft ? THREE.DoubleSide : THREE.FrontSide,
    });
  }

  function build(THREE, part, euler) {
    const { g, s } = geometry(THREE, part);
    const mesh = new THREE.Mesh(g, material(THREE, part));
    const holder = new THREE.Group();
    mesh.scale.set(s[0], s[1], s[2]);
    mesh.castShadow = !part.soft;
    mesh.receiveShadow = true;
    holder.add(mesh);
    const [x, y, z] = part.at;
    holder.position.set(x, y, z);
    const rad = (part.rot || [0, 0, 0]).map((d) => (Number(d) || 0) * Math.PI / 180);
    holder.rotation.set(rad[0], rad[1], rad[2], euler === "ZYX" ? "ZYX" : "XYZ");
    holder.userData = { part, mesh, base: [x, y, z], baseScale: s.slice(), phase: Math.random() * Math.PI * 2 };
    return holder;
  }

  window.NuxivaHoloGeometry = Object.freeze({ build });
})();
