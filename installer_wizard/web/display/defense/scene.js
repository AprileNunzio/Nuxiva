(() => {
  "use strict";
  const NS = (window.NuxivaDefense = window.NuxivaDefense || {});
  const TONES = { calm: 0x34d399, watch: 0xfbbf24, alert: 0xf87171, attack: 0xef4444 };
  const LEVEL_TONE = { low: 0x7dd3fc, medium: 0xfbbf24, high: 0xfb923c, critical: 0xef4444 };
  const BLOCKING = new Set(["block", "country_block", "quarantine", "sinkhole", "tarpit", "rate_limit"]);
  const HOME = { lat: 42, lon: 12.5 };
  const MAX_DEVICES = 24;
  const MAX_ATTACKERS = 12;
  const FRAME_MS = 1000 / 30;
  const PULSES = 3;

  function toVector(THREE, lat, lon, radius) {
    const phi = ((90 - lat) * Math.PI) / 180;
    const theta = ((lon + 180) * Math.PI) / 180;
    return new THREE.Vector3(-radius * Math.sin(phi) * Math.cos(theta), radius * Math.cos(phi), radius * Math.sin(phi) * Math.sin(theta));
  }

  function graticule(THREE) {
    const points = [];
    for (let lat = -60; lat <= 60; lat += 30) {
      for (let lon = 0; lon < 360; lon += 6) points.push(toVector(THREE, lat, lon, 1.002), toVector(THREE, lat, lon + 6, 1.002));
    }
    for (let lon = 0; lon < 360; lon += 30) {
      for (let lat = -90; lat < 90; lat += 6) points.push(toVector(THREE, lat, lon, 1.002), toVector(THREE, lat + 6, lon, 1.002));
    }
    return new THREE.BufferGeometry().setFromPoints(points);
  }

  function disposeTree(root) {
    root.traverse((node) => {
      if (node.geometry) node.geometry.dispose();
      const mats = Array.isArray(node.material) ? node.material : node.material ? [node.material] : [];
      mats.forEach((m) => m.dispose());
    });
  }

  function seeded(text) {
    let h = 2166136261;
    for (const c of String(text)) h = Math.imul(h ^ c.charCodeAt(0), 16777619) >>> 0;
    return (h % 10000) / 10000;
  }

  function defended(incident, defenses) {
    const hit = defenses.filter((d) => d.target === incident.src || (d.kind === "country_block" && d.target === incident.country));
    if (hit.some((d) => d.kind === "honeypot")) return "decoy";
    return hit.some((d) => BLOCKING.has(d.kind)) ? "blocked" : "open";
  }

  function create(host, options) {
    const THREE = window.THREE;
    if (!THREE) throw new Error("three");
    const reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "low-power" });
    renderer.setPixelRatio(1);
    renderer.setClearColor(0x000000, 0);
    host.appendChild(renderer.domElement);
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100);
    camera.position.set(0, 0.9, 3.1);
    const controls = THREE.OrbitControls || window.OrbitControls ? new (THREE.OrbitControls || window.OrbitControls)(camera, renderer.domElement) : null;
    if (controls) {
      controls.enableDamping = true;
      controls.enablePan = false;
      controls.minDistance = 2.4;
      controls.maxDistance = 7;
      controls.autoRotate = !reduced;
      controls.autoRotateSpeed = 0.45;
    }
    const world = new THREE.Group();
    scene.add(world);
    const globe = new THREE.Mesh(new THREE.SphereGeometry(1, 48, 32), new THREE.MeshBasicMaterial({ color: 0x0b1220, transparent: true, opacity: 0.75 }));
    const grid = new THREE.LineSegments(graticule(THREE), new THREE.LineBasicMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.3 }));
    const shield = new THREE.Mesh(new THREE.SphereGeometry(1.2, 40, 28), new THREE.MeshBasicMaterial({ color: TONES.calm, transparent: true, opacity: 0.07, side: THREE.BackSide, depthWrite: false }));
    const home = new THREE.Mesh(new THREE.SphereGeometry(0.035, 16, 12), new THREE.MeshBasicMaterial({ color: 0x34d399 }));
    home.position.copy(toVector(THREE, HOME.lat, HOME.lon, 1.01));
    world.add(globe, grid, shield, home);
    const dots = [];
    NS.countries && NS.countries().forEach((place) => dots.push(toVector(THREE, place.lat, place.lon, 1.004)));
    const land = new THREE.Points(new THREE.BufferGeometry().setFromPoints(dots), new THREE.PointsMaterial({ color: 0x7dd3fc, size: 0.016, transparent: true, opacity: 0.55, sizeAttenuation: true }));
    const halo = new THREE.Mesh(new THREE.RingGeometry(0.05, 0.062, 40), new THREE.MeshBasicMaterial({ color: TONES.calm, transparent: true, opacity: 0.8, side: THREE.DoubleSide }));
    halo.position.copy(home.position.clone().multiplyScalar(1.004));
    halo.lookAt(home.position.clone().multiplyScalar(2));
    world.add(land, halo);
    const shared = {
      device: new THREE.OctahedronGeometry(0.028),
      dot: new THREE.SphereGeometry(0.03, 12, 8),
      bead: new THREE.SphereGeometry(0.014, 8, 6),
      trap: new THREE.OctahedronGeometry(0.05),
    };
    const dynamic = new THREE.Group();
    world.add(dynamic);
    const picks = [];
    const arcs = [];
    const ray = new THREE.Raycaster();
    const pointer = new THREE.Vector2();
    let frame = 0;
    let last = 0;
    let posture = "calm";

    function clear() {
      picks.length = 0;
      arcs.length = 0;
      dynamic.traverse((node) => {
        if (node.material) node.material.dispose();
        if (node.geometry && !Object.values(shared).includes(node.geometry)) node.geometry.dispose();
      });
      dynamic.clear();
    }

    function ring(devices) {
      const count = Math.min(devices, MAX_DEVICES);
      const anchor = home.position.clone().normalize();
      for (let i = 0; i < count; i += 1) {
        const angle = (i / Math.max(count, 1)) * Math.PI * 2;
        const node = new THREE.Mesh(shared.device, new THREE.MeshBasicMaterial({ color: 0x7dd3fc }));
        const side = new THREE.Vector3(0, 1, 0).cross(anchor).normalize();
        const up = anchor.clone().cross(side).normalize();
        node.position.copy(anchor.clone().multiplyScalar(1.12).add(side.multiplyScalar(Math.cos(angle) * 0.13)).add(up.multiplyScalar(Math.sin(angle) * 0.13)));
        dynamic.add(node);
      }
    }

    function attacker(incident, state, index) {
      const place = NS.centroid && NS.centroid(incident.country);
      const lat = place ? place.lat : (seeded(incident.src || incident.id) - 0.5) * 120;
      const lon = place ? place.lon : seeded(`${incident.id}${index}`) * 360 - 180;
      const jitter = place ? 3 : 0;
      const start = toVector(THREE, lat + (seeded(incident.id) - 0.5) * jitter, lon + (seeded(incident.src) - 0.5) * jitter, 1.012);
      const tone = state === "blocked" ? 0x94a3b8 : state === "decoy" ? 0xa78bfa : LEVEL_TONE[incident.level] || LEVEL_TONE.low;
      const dot = new THREE.Mesh(shared.dot, new THREE.MeshBasicMaterial({ color: tone }));
      dot.position.copy(start);
      dot.userData.id = incident.id;
      dynamic.add(dot);
      picks.push(dot);
      const decoy = toVector(THREE, HOME.lat - 18, HOME.lon + 28, 1.3);
      const target = state === "decoy" ? decoy : home.position.clone();
      const stop = state === "blocked" ? 0.55 : 1;
      const mid = start.clone().add(target).multiplyScalar(0.5).normalize().multiplyScalar(1.0 + start.distanceTo(target) * 0.45);
      const curve = new THREE.QuadraticBezierCurve3(start, mid, target);
      const points = curve.getPoints(48).slice(0, Math.max(2, Math.round(48 * stop)));
      const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints(points), new THREE.LineBasicMaterial({ color: tone, transparent: true, opacity: state === "blocked" ? 0.4 : 0.95 }));
      dynamic.add(line);
      const pulses = [];
      for (let p = 0; p < PULSES; p += 1) {
        const bead = new THREE.Mesh(shared.bead, new THREE.MeshBasicMaterial({ color: tone }));
        dynamic.add(bead);
        pulses.push({ bead, offset: p / PULSES });
      }
      arcs.push({ points, pulses, speed: state === "blocked" ? 0.12 : 0.22 });
      if (state === "decoy") {
        const trap = new THREE.Mesh(shared.trap, new THREE.MeshBasicMaterial({ color: 0xa78bfa, wireframe: true }));
        trap.position.copy(decoy);
        dynamic.add(trap);
      }
    }

    function update(data) {
      clear();
      posture = TONES[data.posture] ? data.posture : "calm";
      shield.material.color.setHex(TONES[posture]);
      home.material.color.setHex(TONES[posture]);
      halo.material.color.setHex(TONES[posture]);
      ring(data.lan);
      data.incidents.slice(0, MAX_ATTACKERS).forEach((incident, index) => attacker(incident, defended(incident, data.defenses), index));
    }

    function resize() {
      const w = Math.max(host.clientWidth, 1);
      const h = Math.max(host.clientHeight, 1);
      renderer.setSize(w, h, false);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    }

    function render(now) {
      frame = requestAnimationFrame(render);
      if (document.hidden || now - last < FRAME_MS) return;
      const dt = Math.min((now - last) / 1000, 0.1);
      last = now;
      const beat = reduced ? 0 : Math.sin(now / 520) * 0.5 + 0.5;
      halo.scale.setScalar(1 + beat * 0.5);
      shield.material.opacity = 0.05 + (posture === "calm" ? 0.02 : 0.08) * beat;
      arcs.forEach((arc) => arc.pulses.forEach((pulse) => {
        pulse.offset = reduced ? pulse.offset : (pulse.offset + dt * arc.speed) % 1;
        const point = arc.points[Math.min(arc.points.length - 1, Math.floor(pulse.offset * arc.points.length))];
        if (point) pulse.bead.position.copy(point);
      }));
      if (controls) controls.update();
      renderer.render(scene, camera);
    }

    function pick(event) {
      const box = renderer.domElement.getBoundingClientRect();
      pointer.set(((event.clientX - box.left) / box.width) * 2 - 1, -((event.clientY - box.top) / box.height) * 2 + 1);
      ray.setFromCamera(pointer, camera);
      const hit = ray.intersectObjects(picks, false)[0];
      if (hit && options.onPick) options.onPick(hit.object.userData.id);
    }

    renderer.domElement.addEventListener("click", pick);
    const observer = typeof ResizeObserver === "function" ? new ResizeObserver(resize) : null;
    if (observer) observer.observe(host);
    resize();
    frame = requestAnimationFrame(render);

    return {
      update,
      resize,
      dispose() {
        cancelAnimationFrame(frame);
        Object.values(shared).forEach((g) => g.dispose());
        renderer.forceContextLoss();
        if (observer) observer.disconnect();
        renderer.domElement.removeEventListener("click", pick);
        if (controls) controls.dispose();
        disposeTree(scene);
        renderer.dispose();
        renderer.domElement.remove();
      },
    };
  }

  NS.createScene = create;
})();
