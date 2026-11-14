(() => {
  const LAB = (window.NuxivaLab = window.NuxivaLab || {});
  const MON_W = 0.82;
  const MON_H = 0.35;
  const CANVAS = { w: 640, h: 272 };

  function build(M, spec, slot, index) {
    const F = LAB.furniture;
    const g = new THREE.Group();
    g.position.set(slot.x, 0, slot.z);
    g.add(F.desk(M));
    const top = 0.75;

    const stand = new THREE.Group();
    stand.position.set(0, top, -0.2);
    stand.add(F.box(0.3, 0.014, 0.2, M.steelDark, 0, 0.007, 0));
    stand.add(F.cyl(0.018, 0.022, 0.2, 12, M.steel, 0, 0.11, -0.02));
    const panel = new THREE.Group();
    panel.position.set(0, 0.2 + MON_H / 2, 0);
    panel.add(F.box(MON_W + 0.03, MON_H + 0.03, 0.03, M.plastic, 0, 0, -0.012));
    const canvas = document.createElement("canvas");
    canvas.width = CANVAS.w;
    canvas.height = CANVAS.h;
    const tex = new THREE.CanvasTexture(canvas);
    tex.encoding = THREE.sRGBEncoding;
    tex.anisotropy = 4;
    const screenMat = new THREE.MeshBasicMaterial({ map: tex, toneMapped: false });
    const screen = new THREE.Mesh(new THREE.PlaneGeometry(MON_W, MON_H), screenMat);
    screen.position.z = 0.006;
    panel.add(screen);
    stand.add(panel);
    g.add(stand);

    const kb = F.keyboard(M);
    kb.position.set(0, top, 0.14);
    g.add(kb);
    const mouse = F.mouse(M);
    mouse.position.set(0.36, top, 0.14);
    g.add(mouse);
    const mug = F.mug(M);
    mug.position.set(-0.55, top, 0.02);
    g.add(mug);
    const lamp = F.lamp(M);
    lamp.position.set(-0.68, top, -0.24);
    lamp.rotation.y = 0.5;
    g.add(lamp);
    const note = F.notepad(M);
    note.position.set(0.58, top, 0.05);
    note.rotation.y = -0.3;
    g.add(note);
    const plant = F.plant(M, 0.7);
    plant.position.set(0.7, top, -0.28);
    g.add(plant);
    const phones = F.headphones(M);
    phones.position.set(-0.4, top, -0.3);
    g.add(phones);

    const alarm = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.035, 0.07, 14), M.alarmOff);
    alarm.position.set(0.58, top + 0.035, -0.3);
    alarm.material = M.alarmOff.clone();
    g.add(alarm);

    const plate = document.createElement("canvas");
    plate.width = 256;
    plate.height = 64;
    const plateTex = new THREE.CanvasTexture(plate);
    plateTex.encoding = THREE.sRGBEncoding;
    const nameplate = new THREE.Mesh(new THREE.PlaneGeometry(0.2, 0.05), new THREE.MeshBasicMaterial({ map: plateTex, toneMapped: false }));
    nameplate.position.set(-0.25, top + 0.03, 0.34);
    nameplate.rotation.x = -0.9;
    g.add(nameplate);

    const chair = F.chair(M, index % 2 === 1);
    const seat = LAB.layout.seatOf(slot);
    chair.position.set(seat.x - slot.x, 0, seat.z - slot.z);
    g.add(chair);

    let steam = null;
    if (spec.steam) {
      steam = new THREE.Mesh(new THREE.PlaneGeometry(0.06, 0.12), new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.14, depthWrite: false }));
      steam.position.set(-0.55, top + 0.18, 0.02);
      g.add(steam);
    }

    let glow = null;
    if (spec.glow) {
      glow = new THREE.PointLight(0x29e0ff, 0.0, 2.2, 2);
      glow.position.set(0, top + 0.35, 0.1);
      g.add(glow);
    }

    return { group: g, canvas, ctx: canvas.getContext("2d"), tex, screenMat, plate, plateTex, alarm, chair, steam, glow, slot, painted: 0, key: "" };
  }

  function dispose(st) {
    st.tex.dispose();
    st.plateTex.dispose();
    st.group.traverse((o) => {
      if (o.geometry) o.geometry.dispose();
    });
  }

  LAB.station = Object.freeze({ build, dispose, CANVAS });
})();
