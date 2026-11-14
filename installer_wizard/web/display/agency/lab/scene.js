(() => {
  const LAB = (window.NuxivaLab = window.NuxivaLab || {});
  const T = (key, params) => LAB.screen.T(key, params);
  const MOTION = () => !window.matchMedia || !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const SEL = 0x29e0ff;

  function create(host, callbacks) {
    const canvas = document.createElement("canvas");
    canvas.className = "ag-office-canvas";
    const tip = document.createElement("div");
    tip.className = "ag-office-tip";
    tip.hidden = true;
    const tipName = document.createElement("b");
    const tipRole = document.createElement("span");
    const tipThought = document.createElement("p");
    tip.append(tipName, tipRole, tipThought);
    host.append(canvas, tip);

    const S = {
      ready: false, failed: false, raf: 0, active: false, last: 0, acc: 0, t: 0, data: null, meta: null,
      people: new Map(), ctrls: new Map(), stations: [], hits: [], selected: null, hover: null, drag: null,
      reviewQueue: [], slotOf: new Map(), seq: 0, visible: true, handle: null, disposed: false, focus: null,
    };
    const R = LAB.layout.ROOM;
    let renderer, scene, camera, controls, quality, textures, mats, sun, env, lights = [], rig = null, wallTex = null, wallCtx = null;
    let boardCanvas = null, holo = null, racks = null, plants = [], ring = null, links = [], pending = null, cap = 0;

    function shadows(on) {
      renderer.shadowMap.enabled = on;
      renderer.shadowMap.type = THREE.PCFSoftShadowMap;
      scene.traverse((o) => { if (o.material) o.material.needsUpdate = true; });
      sun.castShadow = on;
      lights.forEach((l) => { l.castShadow = false; });
    }

    function applyQuality(spec) {
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, spec.dpr));
      resize();
      shadows(spec.shadows);
      sun.shadow.mapSize.set(spec.shadowSize, spec.shadowSize);
      if (sun.shadow.map) { sun.shadow.map.dispose(); sun.shadow.map = null; }
      renderer.toneMappingExposure = 0.95;
      if (env) scene.environment = env;
      scene.traverse((o) => {
        if (o.material && o.material.envMapIntensity !== undefined && !o.userData.keepEnv) o.material.envMapIntensity = spec.reflect;
      });
      const aniso = Math.min(renderer.capabilities.getMaxAnisotropy(), spec.rank >= 2 ? 8 : 2);
      cap = aniso;
      S.stations.forEach((st) => { st.glow && (st.glow.visible = spec.glow); st.steam && (st.steam.visible = spec.steam); });
    }

    function resize() {
      if (!renderer) return;
      const rect = host.getBoundingClientRect();
      const w = Math.max(320, Math.floor(rect.width || window.innerWidth));
      const h = Math.max(260, Math.floor(rect.height || window.innerHeight));
      renderer.setSize(w, h, false);
      canvas.style.width = "100%";
      canvas.style.height = "100%";
      camera.aspect = w / h;
      const narrow = w / h < 1;
      camera.fov = narrow ? 52 : 38;
      camera.updateProjectionMatrix();
    }

    function build() {
      renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false, powerPreference: "high-performance" });
      renderer.outputEncoding = THREE.sRGBEncoding;
      renderer.toneMapping = THREE.ACESFilmicToneMapping;
      scene = new THREE.Scene();
      scene.background = new THREE.Color(0x0a1019);
      scene.fog = new THREE.Fog(0x0a1019, 26, 52);
      camera = new THREE.PerspectiveCamera(38, 1, 0.1, 80);
      camera.position.set(7.4, 6.9, 10.6);
      controls = new THREE.OrbitControls(camera, canvas);
      controls.target.set(0, 0.9, 0.4);
      controls.enableDamping = true;
      controls.dampingFactor = 0.08;
      controls.minDistance = 4;
      controls.maxDistance = 24;
      controls.minPolarAngle = 0.25;
      controls.maxPolarAngle = 1.35;
      controls.minAzimuthAngle = -0.9;
      controls.maxAzimuthAngle = 1.6;
      controls.screenSpacePanning = false;

      quality = LAB.quality.create((spec) => applyQuality(spec));
      const spec = quality.spec;
      const probe = renderer.capabilities.getMaxAnisotropy();
      textures = LAB.textures.create(spec, Math.min(probe, spec.rank >= 2 ? 8 : 2));
      mats = LAB.materials.create(textures, spec);
      const M = mats.m;

      const pm = new THREE.PMREMGenerator(renderer);
      env = pm.fromScene(new THREE.RoomEnvironment(), 0.04).texture;
      pm.dispose();
      scene.environment = env;

      scene.add(new THREE.HemisphereLight(0xcfe3ff, 0x2a303a, 0.35));
      sun = new THREE.DirectionalLight(0xfff0d8, 1.1);
      sun.position.set(-7, 11, 9);
      sun.target.position.set(0, 0, 1);
      sun.shadow.camera.left = -11;
      sun.shadow.camera.right = 11;
      sun.shadow.camera.top = 10;
      sun.shadow.camera.bottom = -10;
      sun.shadow.camera.near = 1;
      sun.shadow.camera.far = 32;
      sun.shadow.bias = -0.0004;
      sun.shadow.normalBias = 0.03;
      scene.add(sun, sun.target);

      const sh = LAB.room.shell(M, spec, R);
      scene.add(sh.group);
      scene.add(LAB.room.pendants(M, spec, R, lights));

      const rug = new THREE.Mesh(new THREE.PlaneGeometry(4.6, 3.8), M.rug);
      rug.rotation.x = -Math.PI / 2;
      rug.position.set(0, 0.006, -3.4);
      rug.receiveShadow = true;
      scene.add(rug);

      holo = LAB.room.holo(M, spec);
      holo.group.position.set(LAB.layout.BRAIN.x, 0, LAB.layout.BRAIN.z);
      holo.group.traverse((o) => { if (o.isMesh && o.geometry.type === "CylinderGeometry") o.userData.pickBrain = true; });
      const brainPick = new THREE.Mesh(new THREE.CylinderGeometry(1.0, 1.0, 2.2, 12), new THREE.MeshBasicMaterial({ visible: false }));
      brainPick.position.y = 1.1;
      brainPick.userData.pick = { kind: "brain", id: "shared_brain" };
      holo.group.add(brainPick);
      scene.add(holo.group);

      racks = LAB.room.racks(M, spec);
      scene.add(racks.group);

      wallTex = document.createElement("canvas");
      wallTex.width = 1024;
      wallTex.height = 448;
      wallCtx = wallTex.getContext("2d");
      const disp = LAB.room.display(wallTex, 4.6, 2.0, M);
      disp.group.position.set(0, 2.15, R.z0 + 0.05);
      scene.add(disp.group);
      rig = { disp };
      boardCanvas = document.createElement("canvas");
      boardCanvas.width = 1024;
      boardCanvas.height = 512;
      const boardDisp = LAB.room.display(boardCanvas, 5.0, 2.5, M);
      boardDisp.group.position.set(R.x0 + 0.05, 1.95, 0.4);
      boardDisp.group.rotation.y = Math.PI / 2;
      scene.add(boardDisp.group);
      rig.board = boardDisp;

      [[-6.4, -5.5, 0], [6.4, 5.4, 0], [-6.4, 5.3, 1.3], [6.4, -2.4, 0.7]].forEach(([x, z, r]) => {
        const p = LAB.furniture.tallPlant(M);
        p.position.set(x, 0, z);
        p.rotation.y = r;
        plants.push(p);
        scene.add(p);
      });

      LAB.layout.SLOTS.forEach((slot, i) => {
        const st = LAB.station.build(M, spec, slot, i);
        S.stations.push(st);
        scene.add(st.group);
      });

      const ringGeo = new THREE.RingGeometry(0.46, 0.52, 40);
      ring = new THREE.Mesh(ringGeo, new THREE.MeshBasicMaterial({ color: SEL, transparent: true, opacity: 0.9, side: THREE.DoubleSide, depthWrite: false }));
      ring.rotation.x = -Math.PI / 2;
      ring.position.y = 0.02;
      ring.visible = false;
      scene.add(ring);

      applyQuality(spec);
      quality.govern();
      resize();
    }

    function slotIndex(agent) {
      const wanted = Number.isInteger(agent.desk_index) && agent.desk_index >= 0 ? agent.desk_index : -1;
      if (wanted >= 0 && wanted < S.stations.length) return wanted;
      return S.slotOf.size % S.stations.length;
    }

    async function ensurePerson(agent, isCeo) {
      if (S.people.has(agent.id)) return S.people.get(agent.id);
      const names = LAB.assets.CHARACTERS;
      const idx = isCeo ? 8 : S.seq % names.length;
      S.seq += isCeo ? 0 : 1;
      const gltf = await LAB.assets.character(names[idx]);
      if (S.disposed || S.people.has(agent.id)) return S.people.get(agent.id);
      const person = LAB.people.create(gltf, agent.id);
      person.data = agent;
      person.isCeo = isCeo;
      const badge = document.createElement("canvas");
      badge.width = 512;
      badge.height = 96;
      const tex = new THREE.CanvasTexture(badge);
      tex.encoding = THREE.sRGBEncoding;
      const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true, depthTest: false, depthWrite: false }));
      sprite.scale.set(1.5, 0.28, 1);
      sprite.position.y = 1.15;
      sprite.renderOrder = 10;
      person.root.add(sprite);
      person.badge = { canvas: badge, tex, sprite, key: "" };
      scene.add(person.root);
      S.people.set(agent.id, person);
      person.hitMeshes = [person.proxy];
      return person;
    }

    function placeAtRest(person, agent, isCeo) {
      if (isCeo) {
        person.root.position.set(LAB.layout.CEO.x, 0, LAB.layout.CEO.z);
        person.root.rotation.y = 0;
        person.heading = person.headingTarget = 0;
        person.setSeated(false);
        person.mix(["idle"]);
        return;
      }
      const slot = S.stations[S.slotOf.get(agent.id)].slot;
      const seat = LAB.layout.seatOf(slot);
      person.root.position.set(seat.x, 0, seat.z);
      person.heading = person.headingTarget = Math.PI;
      person.root.rotation.y = Math.PI;
    }

    async function apply() {
      const data = S.data;
      if (!data || !S.ready) return;
      const agents = (data.agents || []).filter(Boolean);
      agents.forEach((a) => { if (!S.slotOf.has(a.id)) S.slotOf.set(a.id, slotIndex(a)); });
      const plan = LAB.behavior.plan(data);
      S.reviewQueue = agents.filter((a) => plan.get(a.id) && plan.get(a.id).mode === "review").map((a) => a.id);
      const all = [...agents.map((a) => [a, false]), ...(data.ceo ? [[data.ceo, true]] : [])];
      for (const [agent, isCeo] of all) {
        let person = S.people.get(agent.id);
        const fresh = !person;
        try { person = await ensurePerson(agent, isCeo); } catch (err) { console.error("Aula 3D: personaggio non caricato", err); continue; }
        if (!person || S.disposed) continue;
        person.data = agent;
        if (fresh) placeAtRest(person, agent, isCeo);
        let ctrl = S.ctrls.get(agent.id);
        if (!ctrl && !isCeo) {
          const slot = S.stations[S.slotOf.get(agent.id)].slot;
          ctrl = LAB.behavior.controller(person, slot, {
            slotOf: (id) => (S.slotOf.has(id) ? S.stations[S.slotOf.get(id)].slot : null),
            reviewSlot: (id) => Math.max(0, S.reviewQueue.indexOf(id)),
          });
          S.ctrls.set(agent.id, ctrl);
        }
        if (isCeo) {
          person.mix(S.reviewQueue.length ? ["idle", "talk"] : ["idle"]);
          person.face(0);
          person.mode = S.reviewQueue.length ? "review" : "idle";
          continue;
        }
        const next = plan.get(agent.id) || { mode: "idle" };
        person.mode = next.mode;
        person.target = next.target || null;
        if (!ctrl.state.mode || ctrl.state.mode !== next.mode || ctrl.state.target !== (next.target || null) || fresh) ctrl.enter(next.mode, next.target);
      }
      for (const id of [...S.people.keys()]) {
        if (!all.some(([a]) => a.id === id)) removePerson(id);
      }
      S.stations.forEach((st, i) => {
        const owner = [...S.slotOf.entries()].find(([, idx]) => idx === i);
        st.owner = owner ? agents.find((a) => a.id === owner[0]) || null : null;
      });
      S.dirty = true;
    }

    function removePerson(id) {
      const p = S.people.get(id);
      if (!p) return;
      scene.remove(p.root);
      p.badge.tex.dispose();
      p.badge.sprite.material.dispose();
      p.dispose();
      S.people.delete(id);
      S.ctrls.delete(id);
      S.slotOf.delete(id);
    }

    const paint = LAB.painters.create({
      S,
      get quality() { return quality; }, get wallCtx() { return wallCtx; }, get wallTex() { return wallTex; },
      get boardCanvas() { return boardCanvas; }, get rig() { return rig; }, get holo() { return holo; },
      get racks() { return racks; }, get plants() { return plants; }, get links() { return links; },
      get scene() { return scene; }, get camera() { return camera; },
    });

    function frame(now) {
      S.raf = 0;
      if (!S.active || S.disposed) return;
      const spec = quality.spec;
      const step = 1000 / (MOTION() ? spec.fps : 6);
      if (S.last && now - S.last < step - 1) { S.raf = requestAnimationFrame(frame); return; }
      const dt = Math.min(0.1, S.last ? (now - S.last) / 1000 : 0.016);
      if (S.last) quality.frame(now - S.last);
      S.last = now;
      S.t += dt;
      const t = S.t;
      S.ctrls.forEach((c) => c.update(dt));
      S.people.forEach((p) => { p.update(dt, t); paint.paintBadge(p, t); });
      paint.ambient(t);
      paint.paintScreens(t, S.dirty);
      paint.paintWall(t, S.dirty);
      paint.paintBoard(t, S.dirty);
      S.dirty = false;
      paint.updateLinks(t);
      if (S.selected) {
        const target = S.selected === "shared_brain" ? holo.group.position : (S.people.get(S.selected) || {}).root && S.people.get(S.selected).root.position;
        if (target) { ring.visible = true; ring.position.set(target.x, 0.02, target.z); ring.scale.setScalar(S.selected === "shared_brain" ? 2.1 : 1 + Math.sin(t * 4) * 0.05); }
      } else ring.visible = false;
      if (S.focus) {
        const f = S.focus;
        const k = Math.min(1, dt * 3.2);
        const tx = controls.target.x + (f.x - controls.target.x) * k;
        const ty = controls.target.y + (f.y - controls.target.y) * k;
        const tz = controls.target.z + (f.z - controls.target.z) * k;
        const dir = camera.position.clone().sub(controls.target);
        const len = dir.length();
        dir.normalize().multiplyScalar(len + (f.dist - len) * k);
        controls.target.set(tx, ty, tz);
        camera.position.set(tx + dir.x, ty + dir.y, tz + dir.z);
        if (Math.abs(tx - f.x) + Math.abs(tz - f.z) + Math.abs(len - f.dist) < 0.03) S.focus = null;
      }
      controls.update();
      renderer.render(scene, camera);
      S.raf = requestAnimationFrame(frame);
    }

    function start() {
      if (!S.ready || S.disposed || S.active || !S.visible || document.hidden) return;
      S.active = true;
      S.last = 0;
      S.raf = requestAnimationFrame(frame);
    }

    function pause() {
      S.active = false;
      if (S.raf) cancelAnimationFrame(S.raf);
      S.raf = 0;
    }

    function pick(ev) {
      const rect = canvas.getBoundingClientRect();
      const ndc = new THREE.Vector2(((ev.clientX - rect.left) / rect.width) * 2 - 1, -(((ev.clientY - rect.top) / rect.height) * 2 - 1));
      const ray = new THREE.Raycaster();
      ray.setFromCamera(ndc, camera);
      const targets = [...S.people.values()].map((p) => p.proxy);
      targets.push(...holo.group.children.filter((c) => c.userData.pick));
      S.stations.forEach((st) => targets.push(...(st.pickables || [])));
      const hits = ray.intersectObjects(targets, false);
      return hits.length ? hits[0].object.userData.pick : null;
    }

    function describe(hit, x, y) {
      if (!hit) { tip.hidden = true; return; }
      tip.hidden = false;
      tip.style.left = `${Math.min(rectW() - 240, Math.max(12, x + 14))}px`;
      tip.style.top = `${Math.max(12, y - 18)}px`;
      if (hit.kind === "brain") {
        const b = (S.data && S.data.shared_brain) || {};
        tipName.textContent = T("lab_brain_title");
        tipRole.textContent = (S.data && S.data.agency_name) || "";
        tipThought.textContent = T("lab_brain_tip", { decisions: (b.decisions || []).length, questions: (b.open_questions || []).length });
        return;
      }
      const all = [(S.data || {}).ceo, ...((S.data || {}).agents || [])].filter(Boolean);
      const a = all.find((x) => x.id === hit.id) || {};
      tipName.textContent = a.name || a.id || "";
      tipRole.textContent = `${a.department || ""} · ${a.role || ""}`;
      tipThought.textContent = a.thought || "";
    }

    const rectW = () => host.getBoundingClientRect().width;

    canvas.addEventListener("pointerdown", (e) => { S.drag = { x: e.clientX, y: e.clientY, moved: false }; });
    canvas.addEventListener("pointermove", (e) => {
      if (S.drag) { if (Math.hypot(e.clientX - S.drag.x, e.clientY - S.drag.y) > 5) S.drag.moved = true; return; }
      if (e.pointerType === "touch") return;
      const hit = pick(e);
      canvas.style.cursor = hit ? "pointer" : "grab";
      const rect = canvas.getBoundingClientRect();
      describe(hit, e.clientX - rect.left, e.clientY - rect.top);
    });
    canvas.addEventListener("pointerleave", () => { tip.hidden = true; });
    window.addEventListener("pointerup", (e) => {
      if (!S.drag) return;
      const moved = S.drag.moved;
      S.drag = null;
      if (moved || e.target !== canvas) return;
      const hit = pick(e);
      if (!hit) return;
      S.selected = hit.id;
      const all = [(S.data || {}).ceo, ...((S.data || {}).agents || [])].filter(Boolean);
      if (hit.kind === "brain") callbacks.onSelectBrain && callbacks.onSelectBrain((S.data || {}).shared_brain);
      else callbacks.onSelectAgent && callbacks.onSelectAgent(all.find((a) => a.id === hit.id));
    });

    const ro = typeof ResizeObserver === "function" ? new ResizeObserver(() => resize()) : null;
    if (ro) ro.observe(host);
    const io = typeof IntersectionObserver === "function" ? new IntersectionObserver((entries) => {
      S.visible = entries.some((e) => e.isIntersecting);
      if (S.visible) start(); else pause();
    }) : null;
    if (io) io.observe(host);
    document.addEventListener("visibilitychange", () => { if (document.hidden) pause(); else start(); });
    canvas.addEventListener("webglcontextlost", (e) => { e.preventDefault(); pause(); S.failed = true; callbacks.onFail && callbacks.onFail(); });

    function megabytes() {
      if (!renderer) return 0;
      const i = renderer.info;
      return Math.round((i.memory.textures * 2.5 + i.memory.geometries * 0.15) * 10) / 10;
    }

    async function init() {
      try {
        await LAB.assets.libs();
        if (S.disposed) return;
        build();
        S.ready = true;
        if (window.NuxivaResources) {
          S.handle = window.NuxivaResources.register({
            id: "agency-lab", cls: "ambient", coverable: false, mb: megabytes,
            suspend: pause, resume: start,
            release: () => { pause(); },
          });
        }
        await apply();
        start();
      } catch (err) {
        console.error("Aula 3D non avviata", err);
        S.failed = true;
        callbacks.onFail && callbacks.onFail(err);
      }
    }

    function update(office, meta) {
      S.data = office;
      S.meta = meta || S.meta;
      S.dirty = true;
      if (!S.ready) return;
      apply().then(() => { if (!S.active) start(); if (!MOTION() && renderer) renderer.render(scene, camera); });
    }

    function select(id) {
      S.selected = id || null;
      if (!id || !controls) return;
      const target = id === "shared_brain" ? holo.group.position : S.people.get(id) && S.people.get(id).root.position;
      if (target) S.focus = { x: target.x, y: id === "shared_brain" ? 1.2 : 0.8, z: target.z, dist: id === "shared_brain" ? 7 : 5.5 };
    }

    function setView(pos, target) {
      camera.position.set(pos[0], pos[1], pos[2]);
      controls.target.set(target[0], target[1], target[2]);
      controls.update();
    }

    function advance(seconds) {
      const steps = Math.ceil(seconds / 0.05);
      for (let i = 0; i < steps; i += 1) {
        S.t += 0.05;
        S.ctrls.forEach((ctrl) => ctrl.update(0.05));
        S.people.forEach((p) => p.update(0.05, S.t));
      }
    }

    function stop() { pause(); }

    function dispose() {
      S.disposed = true;
      pause();
      if (ro) ro.disconnect();
      if (io) io.disconnect();
      if (S.handle) S.handle.unregister();
      if (!renderer) return;
      S.people.forEach((p) => p.dispose());
      S.stations.forEach((st) => LAB.station.dispose(st));
      textures.dispose();
      mats.dispose();
      renderer.dispose();
      renderer.forceContextLoss();
    }

    init();
    return { update, stop, select, setView, advance, dispose, get failed() { return S.failed; }, get quality() { return quality ? quality.name : ""; } };
  }

  LAB.scene = Object.freeze({ create });
})();
