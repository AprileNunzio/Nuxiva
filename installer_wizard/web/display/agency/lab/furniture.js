(() => {
  const LAB = (window.NuxivaLab = window.NuxivaLab || {});
  const box = (w, h, d, mat, x = 0, y = 0, z = 0) => {
    const mesh = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);
    mesh.position.set(x, y, z);
    mesh.castShadow = mesh.receiveShadow = true;
    return mesh;
  };
  const cyl = (rt, rb, h, seg, mat, x = 0, y = 0, z = 0) => {
    const mesh = new THREE.Mesh(new THREE.CylinderGeometry(rt, rb, h, seg), mat);
    mesh.position.set(x, y, z);
    mesh.castShadow = mesh.receiveShadow = true;
    return mesh;
  };

  function desk(M, width = 1.6, depth = 0.8) {
    const g = new THREE.Group();
    const top = 0.73;
    g.add(box(width, 0.04, depth, M.wood, 0, top, 0));
    g.add(box(width + 0.01, 0.012, depth + 0.01, M.steelDark, 0, top - 0.026, 0));
    for (const s of [-1, 1]) {
      g.add(box(0.05, top - 0.02, depth - 0.12, M.steel, s * (width / 2 - 0.07), (top - 0.02) / 2, 0));
      g.add(box(0.12, 0.03, depth - 0.08, M.steelDark, s * (width / 2 - 0.07), 0.015, 0));
    }
    g.add(box(width - 0.2, 0.34, 0.02, M.steelDark, 0, 0.52, -depth / 2 + 0.1));
    const unit = new THREE.Group();
    unit.position.set(width / 2 - 0.34, 0, 0.02);
    unit.add(box(0.42, 0.56, depth - 0.14, M.plasticLight, 0, 0.3, 0));
    for (let i = 0; i < 3; i += 1) {
      unit.add(box(0.38, 0.16, 0.012, M.steel, 0, 0.12 + i * 0.18, (depth - 0.14) / 2 + 0.004));
      unit.add(box(0.14, 0.014, 0.014, M.steelDark, 0, 0.16 + i * 0.18, (depth - 0.14) / 2 + 0.016));
    }
    g.add(unit);
    return g;
  }

  function chair(M, alt) {
    const g = new THREE.Group();
    const seatY = 0.46;
    const base = new THREE.Group();
    for (let i = 0; i < 5; i += 1) {
      const arm = new THREE.Group();
      arm.rotation.y = (i / 5) * Math.PI * 2;
      arm.add(box(0.3, 0.025, 0.045, M.steelDark, 0.15, 0.07, 0));
      const wheel = new THREE.Mesh(new THREE.SphereGeometry(0.03, 10, 8), M.rubber);
      wheel.position.set(0.29, 0.035, 0);
      wheel.castShadow = true;
      arm.add(wheel);
      base.add(arm);
    }
    g.add(base);
    g.add(cyl(0.025, 0.03, seatY - 0.1, 12, M.steel, 0, (seatY - 0.1) / 2 + 0.07, 0));
    const seat = new THREE.Group();
    seat.position.y = seatY;
    const fab = alt ? M.fabricAlt : M.fabric;
    seat.add(box(0.5, 0.07, 0.48, fab, 0, 0, 0));
    seat.add(box(0.46, 0.02, 0.44, M.plastic, 0, -0.045, 0));
    const back = new THREE.Group();
    back.position.set(0, 0.04, 0.23);
    back.rotation.x = 0.1;
    back.add(box(0.46, 0.5, 0.06, fab, 0, 0.3, 0));
    back.add(box(0.05, 0.4, 0.04, M.steelDark, 0, 0.12, 0.02));
    back.add(box(0.28, 0.14, 0.05, fab, 0, 0.62, 0));
    seat.add(back);
    for (const s of [-1, 1]) {
      seat.add(box(0.04, 0.2, 0.04, M.steelDark, s * 0.27, 0.12, 0.08));
      seat.add(box(0.07, 0.03, 0.26, M.plastic, s * 0.27, 0.23, -0.02));
    }
    g.add(seat);
    return g;
  }

  function keyboard(M) {
    const g = new THREE.Group();
    g.add(box(0.44, 0.016, 0.15, M.plastic, 0, 0.008, 0));
    const keys = new THREE.InstancedMesh(new THREE.BoxGeometry(0.027, 0.008, 0.027), M.plasticLight, 66);
    const dummy = new THREE.Object3D();
    let i = 0;
    for (let row = 0; row < 5; row += 1) {
      const count = row === 4 ? 6 : 14;
      for (let col = 0; col < count && i < 66; col += 1) {
        const w = row === 4 && col === 2 ? 6 : 1;
        dummy.position.set(-0.2 + col * 0.0295 + (row === 4 ? 0.04 : 0), 0.019, -0.054 + row * 0.03);
        dummy.scale.set(w === 6 ? 5 : 1, 1, 1);
        dummy.updateMatrix();
        keys.setMatrixAt(i, dummy.matrix);
        i += 1;
      }
    }
    keys.count = i;
    keys.castShadow = true;
    g.add(keys);
    return g;
  }

  function mouse(M) {
    const g = new THREE.Group();
    const pad = box(0.24, 0.004, 0.2, M.rubber, 0, 0.002, 0);
    const body = new THREE.Mesh(new THREE.SphereGeometry(0.03, 14, 10), M.plastic);
    body.scale.set(0.9, 0.55, 1.4);
    body.position.y = 0.018;
    body.castShadow = true;
    g.add(pad, body);
    return g;
  }

  function mug(M) {
    const g = new THREE.Group();
    g.add(cyl(0.038, 0.034, 0.09, 20, M.ceramic, 0, 0.045, 0));
    const handle = new THREE.Mesh(new THREE.TorusGeometry(0.026, 0.006, 8, 14, Math.PI), M.ceramic);
    handle.rotation.z = -Math.PI / 2;
    handle.position.set(0.04, 0.045, 0);
    g.add(handle);
    return g;
  }

  function lamp(M) {
    const g = new THREE.Group();
    g.add(cyl(0.07, 0.08, 0.02, 20, M.steelDark, 0, 0.01, 0));
    const lower = box(0.014, 0.3, 0.014, M.steel, 0, 0.17, 0);
    lower.rotation.z = 0.25;
    const upper = box(0.014, 0.28, 0.014, M.steel, 0.08, 0.38, 0);
    upper.rotation.z = -0.7;
    const head = new THREE.Mesh(new THREE.ConeGeometry(0.07, 0.1, 18, 1, true), M.steelDark);
    head.position.set(0.19, 0.46, 0);
    head.rotation.z = Math.PI / 2 + 0.5;
    head.material.side = THREE.DoubleSide;
    head.castShadow = true;
    const bulb = new THREE.Mesh(new THREE.SphereGeometry(0.022, 12, 10), M.bulb);
    bulb.position.set(0.185, 0.445, 0);
    g.add(lower, upper, head, bulb);
    return g;
  }

  function plant(M, scale = 1) {
    const g = new THREE.Group();
    g.add(cyl(0.12 * scale, 0.09 * scale, 0.22 * scale, 18, M.pot, 0, 0.11 * scale, 0));
    g.add(cyl(0.11 * scale, 0.11 * scale, 0.02 * scale, 18, M.soil, 0, 0.22 * scale, 0));
    const leaves = new THREE.Group();
    for (let i = 0; i < 9; i += 1) {
      const leaf = new THREE.Mesh(new THREE.SphereGeometry(0.1 * scale, 10, 8), i % 2 ? M.leaf : M.leafLight);
      leaf.scale.set(0.45, 1.5, 0.18);
      const a = (i / 9) * Math.PI * 2;
      leaf.position.set(Math.cos(a) * 0.07 * scale, 0.38 * scale, Math.sin(a) * 0.07 * scale);
      leaf.rotation.set(Math.sin(a) * 0.5, -a, Math.cos(a) * 0.5);
      leaf.castShadow = true;
      leaves.add(leaf);
    }
    leaves.name = "leaves";
    g.add(leaves);
    return g;
  }

  function tallPlant(M) {
    const g = plant(M, 3.2);
    g.scale.setScalar(1);
    return g;
  }

  function headphones(M) {
    const g = new THREE.Group();
    const band = new THREE.Mesh(new THREE.TorusGeometry(0.075, 0.008, 8, 20, Math.PI), M.plastic);
    band.position.y = 0.09;
    g.add(band);
    for (const s of [-1, 1]) g.add(cyl(0.035, 0.035, 0.03, 16, M.plastic, s * 0.075, 0.09, 0)).rotation.z = Math.PI / 2;
    g.add(cyl(0.008, 0.008, 0.14, 8, M.steelDark, 0, 0.07, -0.01));
    g.add(cyl(0.05, 0.05, 0.012, 16, M.steelDark, 0, 0.006, -0.01));
    return g;
  }

  function notepad(M) {
    const g = new THREE.Group();
    g.add(box(0.15, 0.012, 0.21, M.plasticLight, 0, 0.006, 0));
    const pen = cyl(0.004, 0.004, 0.14, 8, M.steelDark, 0.04, 0.016, 0.03);
    pen.rotation.z = Math.PI / 2;
    pen.rotation.y = 0.5;
    g.add(pen);
    return g;
  }

  LAB.furniture = Object.freeze({ box, cyl, desk, chair, keyboard, mouse, mug, lamp, plant, tallPlant, headphones, notepad });
})();
