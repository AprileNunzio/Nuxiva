(() => {
  const LAB = (window.NuxivaLab = window.NuxivaLab || {});
  const F = () => LAB.furniture;

  function skyTexture() {
    const c = document.createElement("canvas");
    c.width = 256;
    c.height = 128;
    const x = c.getContext("2d");
    const g = x.createLinearGradient(0, 0, 0, 128);
    g.addColorStop(0, "#1b3d6e");
    g.addColorStop(0.6, "#4f86c6");
    g.addColorStop(1, "#d7e8f7");
    x.fillStyle = g;
    x.fillRect(0, 0, 256, 128);
    x.fillStyle = "rgba(20,35,60,0.9)";
    let px = 0;
    const r = LAB.textures.rng(5);
    while (px < 256) {
      const w = 10 + r() * 22;
      const h = 22 + r() * 56;
      x.fillRect(px, 128 - h, w, h);
      px += w + 2;
    }
    const t = new THREE.CanvasTexture(c);
    t.encoding = THREE.sRGBEncoding;
    return t;
  }

  function shell(M, spec, R) {
    const g = new THREE.Group();
    const { w, d, h, x0, z0 } = R;
    const floor = new THREE.Mesh(new THREE.PlaneGeometry(w, d), M.floor);
    floor.rotation.x = -Math.PI / 2;
    floor.position.set(x0 + w / 2, 0, z0 + d / 2);
    floor.receiveShadow = true;
    g.add(floor);

    const back = new THREE.Group();
    back.position.set(0, 0, z0);
    const wallBack = F().box(w, h, 0.18, M.wall, x0 + w / 2, h / 2, -0.09);
    back.add(wallBack);
    back.add(F().box(w, 0.12, 0.2, M.base, x0 + w / 2, 0.06, -0.09));
    const sky = skyTexture();
    const skyMat = new THREE.MeshBasicMaterial({ map: sky });
    [-3.9, 3.9].forEach((wx) => {
      const pane = new THREE.Mesh(new THREE.PlaneGeometry(3.2, 1.9), skyMat);
      pane.position.set(wx, 1.95, 0.011);
      back.add(pane);
      back.add(F().box(3.36, 0.08, 0.1, M.steelDark, wx, 2.94, 0.03));
      back.add(F().box(3.36, 0.08, 0.1, M.steelDark, wx, 0.99, 0.03));
      for (const s of [-1.64, 0, 1.64]) back.add(F().box(0.06, 1.98, 0.1, M.steelDark, wx + s, 1.95, 0.03));
      const glass = new THREE.Mesh(new THREE.PlaneGeometry(3.2, 1.9), M.glass);
      glass.position.set(wx, 1.95, 0.05);
      back.add(glass);
    });
    g.add(back);

    const left = new THREE.Group();
    left.position.set(x0, 0, 0);
    left.add(F().box(0.18, h, d, M.wall, -0.09, h / 2, z0 + d / 2));
    left.add(F().box(0.2, 0.12, d, M.base, -0.09, 0.06, z0 + d / 2));
    g.add(left);

    const trim = F().box(w, 0.06, 0.06, M.steelDark, x0 + w / 2, h, z0 + 0.02);
    g.add(trim);
    return { group: g, skyMat, sky };
  }

  function pendants(M, spec, R, lights) {
    const g = new THREE.Group();
    const spots = [[-3.9, 0.5], [3.9, 0.5], [-3.9, 3.9], [3.9, 3.9], [0, -3.0]];
    spots.forEach(([x, z], i) => {
      const rect = i < 2 + spec.rank;
      if (rect) {
        const p = new THREE.PointLight(0xdfeaff, 0.42, 9, 1.8);
        p.position.set(x, 3.0, z);
        lights.push(p);
        g.add(p);
      }
    });
    return g;
  }

  function racks(M, spec) {
    const g = new THREE.Group();
    const leds = [];
    const count = spec.leds;
    const mesh = new THREE.InstancedMesh(new THREE.BoxGeometry(0.03, 0.012, 0.012), new THREE.MeshBasicMaterial({ color: 0xffffff }), count * 2);
    const dummy = new THREE.Object3D();
    const col = new THREE.Color();
    [0, 1].forEach((r) => {
      const rack = new THREE.Group();
      rack.position.set(5.0 + r * 0.8, 0, -5.9);
      rack.add(F().box(0.72, 2.1, 0.9, M.steelDark, 0, 1.05, 0));
      for (let i = 0; i < 10; i += 1) {
        rack.add(F().box(0.62, 0.11, 0.02, i % 2 ? M.steel : M.plastic, 0, 0.3 + i * 0.17, 0.46));
      }
      g.add(rack);
      for (let i = 0; i < count; i += 1) {
        dummy.position.set(5.0 + r * 0.8 - 0.22 + (i % 4) * 0.06, 0.3 + Math.floor(i / 4) * 0.17, -5.9 + 0.472);
        dummy.updateMatrix();
        const idx = r * count + i;
        mesh.setMatrixAt(idx, dummy.matrix);
        mesh.setColorAt(idx, col.set(0x1d3b2c));
        leds.push(idx);
      }
    });
    mesh.instanceMatrix.needsUpdate = true;
    g.add(mesh);
    return { group: g, mesh, leds };
  }

  function holo(M, spec) {
    const g = new THREE.Group();
    g.add(F().cyl(0.95, 1.05, 0.12, 40, M.steelDark, 0, 0.06, 0));
    g.add(F().cyl(0.82, 0.9, 0.7, 40, M.steel, 0, 0.47, 0));
    const ring = new THREE.Mesh(new THREE.TorusGeometry(0.88, 0.014, 8, 64), M.glowCyan);
    ring.rotation.x = Math.PI / 2;
    ring.position.y = 0.83;
    g.add(ring);
    const top = F().cyl(0.86, 0.86, 0.04, 40, M.steelDark, 0, 0.84, 0);
    g.add(top);
    const field = new THREE.Group();
    field.position.y = 1.5;
    field.add(new THREE.Mesh(new THREE.IcosahedronGeometry(0.42, 2), M.holo));
    field.add(new THREE.Mesh(new THREE.SphereGeometry(0.34, 18, 14), M.holoCore));
    const rings = [];
    for (let i = 0; i < 3; i += 1) {
      const r = new THREE.Mesh(new THREE.TorusGeometry(0.58 + i * 0.1, 0.006, 6, 56), M.glowCyan);
      r.rotation.set(Math.PI / 2 + i * 0.5, i * 0.8, 0);
      field.add(r);
      rings.push(r);
    }
    const pts = new Float32Array(spec.rank >= 2 ? 240 : 90);
    for (let i = 0; i < pts.length; i += 3) {
      const a = Math.random() * Math.PI * 2;
      const rr = 0.5 + Math.random() * 0.45;
      pts[i] = Math.cos(a) * rr;
      pts[i + 1] = (Math.random() - 0.5) * 0.9;
      pts[i + 2] = Math.sin(a) * rr;
    }
    const pg = new THREE.BufferGeometry();
    pg.setAttribute("position", new THREE.BufferAttribute(pts, 3));
    const points = new THREE.Points(pg, new THREE.PointsMaterial({ color: 0x7dd3fc, size: 0.025, transparent: true, opacity: 0.85, depthWrite: false }));
    field.add(points);
    g.add(field);
    const beam = new THREE.Mesh(new THREE.CylinderGeometry(0.4, 0.8, 0.66, 32, 1, true), new THREE.MeshBasicMaterial({ color: 0x29e0ff, transparent: true, opacity: 0.07, depthWrite: false, side: THREE.DoubleSide }));
    beam.position.y = 1.18;
    g.add(beam);
    return { group: g, field, rings, points, ring };
  }

  function display(canvas, w, h, M) {
    const g = new THREE.Group();
    const tex = new THREE.CanvasTexture(canvas);
    tex.encoding = THREE.sRGBEncoding;
    tex.anisotropy = 4;
    const plane = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ map: tex, toneMapped: false }));
    plane.position.z = 0.04;
    g.add(F().box(w + 0.14, h + 0.14, 0.06, M.plastic, 0, 0, 0), plane);
    return { group: g, tex, plane };
  }

  function corner(M) {
    const g = new THREE.Group();
    const p = F().tallPlant(M);
    g.add(p);
    return g;
  }

  LAB.room = Object.freeze({ shell, pendants, racks, holo, display, corner });
})();
