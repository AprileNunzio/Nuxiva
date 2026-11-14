(() => {
  const LAB = (window.NuxivaLab = window.NuxivaLab || {});
  const ARMS = ["arm-left", "arm-right"];
  const HEAD_HEIGHT = 0.66;
  const SIT_LIFT = 0.0;

  const trackBone = (track) => track.name.split(".")[0];

  function subset(clip, name, keep) {
    const tracks = clip.tracks.filter((t) => keep(trackBone(t))).map((t) => t.clone());
    return new THREE.AnimationClip(name, clip.duration, tracks);
  }

  function create(gltf, id) {
    const root = new THREE.Group();
    root.name = id;
    const model = gltf.scene;
    root.add(model);
    model.updateMatrixWorld(true);
    let headY = 0;
    model.traverse((o) => { if (o.isBone && o.name === "head") headY = o.getWorldPosition(new THREE.Vector3()).y; });
    const scale = HEAD_HEIGHT / Math.max(0.05, headY);
    model.scale.setScalar(scale);
    model.traverse((o) => {
      if (o.isMesh || o.isSkinnedMesh) {
        o.castShadow = true;
        o.receiveShadow = true;
        o.frustumCulled = false;
        if (o.material) {
          o.material = o.material.clone();
          o.material.roughness = Math.min(1, (o.material.roughness || 0.8) + 0.05);
        }
      }
    });

    const bones = {};
    model.traverse((o) => { if (o.isBone) bones[o.name] = o; });
    const clips = {};
    gltf.animations.forEach((c) => { clips[c.name] = c; });
    const mixer = new THREE.AnimationMixer(model);
    const sit = clips.sit;
    const defs = {
      idle: clips.idle,
      walk: clips.walk,
      sitLegs: sit && subset(sit, "sitLegs", (b) => !ARMS.includes(b)),
      sitArms: sit && subset(sit, "sitArms", (b) => ARMS.includes(b)),
      hold: clips["holding-both"],
      yes: clips["emote-yes"],
      no: clips["emote-no"],
      talk: clips["interact-right"],
      talkL: clips["interact-left"],
      pick: clips["pick-up"],
    };
    const layers = new Map();
    Object.entries(defs).forEach(([name, clip]) => {
      if (!clip) return;
      const action = mixer.clipAction(clip);
      action.setEffectiveWeight(0);
      action.play();
      layers.set(name, { action, w: 0, target: 0 });
    });

    const proxy = new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.42, 1.5, 8), new THREE.MeshBasicMaterial({ visible: false }));
    proxy.position.y = 0.75;
    proxy.userData.pick = { kind: "agent", id };
    root.add(proxy);

    const q = new THREE.Quaternion();
    const e = new THREE.Euler();
    const st = {
      id, root, model, mixer, layers, bones, proxy,
      heading: 0, headingTarget: 0, speed: 0, path: [], onArrive: null, seated: false, typing: false, phase: Math.random() * 6.28,
      sitBlend: 0, lift: 0, sitHeight: 0.46,
    };

    function mix(names) {
      layers.forEach((l, name) => { l.target = names.includes(name) ? 1 : 0; });
    }

    function walk(points, speed, done) {
      st.path = points.map((p) => ({ x: p.x, z: p.z }));
      st.speed = speed;
      st.onArrive = done || null;
    }

    function face(angle) { st.headingTarget = angle; }

    function setSeated(on, height) {
      st.seated = on;
      if (height !== undefined) st.sitHeight = height;
    }

    function update(dt, t) {
      let moving = false;
      if (st.path.length) {
        const next = st.path[0];
        const dx = next.x - root.position.x;
        const dz = next.z - root.position.z;
        const dist = Math.hypot(dx, dz);
        const step = st.speed * dt;
        if (dist <= step + 0.001) {
          root.position.x = next.x;
          root.position.z = next.z;
          st.path.shift();
          if (!st.path.length) {
            const cb = st.onArrive;
            st.onArrive = null;
            if (cb) cb();
          }
        } else {
          root.position.x += (dx / dist) * step;
          root.position.z += (dz / dist) * step;
          st.headingTarget = Math.atan2(dx, dz);
          moving = true;
        }
      }
      let diff = st.headingTarget - st.heading;
      diff = Math.atan2(Math.sin(diff), Math.cos(diff));
      st.heading += diff * Math.min(1, dt * (moving ? 10 : 6));
      root.rotation.y = st.heading;

      const lerp = Math.min(1, dt * 7);
      st.sitBlend += ((st.seated ? 1 : 0) - st.sitBlend) * lerp;
      root.position.y = st.sitBlend * (st.sitHeight + SIT_LIFT);

      layers.forEach((l) => {
        l.w += (l.target - l.w) * Math.min(1, dt * 9);
        if (l.w < 0.002 && l.target === 0) l.w = 0;
        l.action.setEffectiveWeight(l.w);
        if (l.w > 0 && moving) l.action.timeScale = l === layers.get("walk") ? Math.max(0.6, st.speed / 0.95) : 1;
      });
      mixer.update(dt);

      if (st.typing && st.sitBlend > 0.8) {
        for (const [i, name] of ARMS.entries()) {
          const bone = bones[name];
          if (!bone) continue;
          const k = t * 13 + st.phase + i * 1.9;
          e.set(Math.sin(k) * 0.07, Math.sin(k * 0.7 + i) * 0.05, Math.sin(k * 1.3) * 0.04);
          q.setFromEuler(e);
          bone.quaternion.multiply(q);
        }
      }
    }

    function dispose() {
      mixer.stopAllAction();
      model.traverse((o) => {
        if (o.geometry) o.geometry.dispose();
        if (o.material) {
          Object.values(o.material).forEach((v) => v && v.isTexture && v.dispose());
          o.material.dispose();
        }
      });
    }

    return Object.assign(st, { mix, walk, face, setSeated, update, dispose, has: (n) => layers.has(n) });
  }

  LAB.people = Object.freeze({ create });
})();
