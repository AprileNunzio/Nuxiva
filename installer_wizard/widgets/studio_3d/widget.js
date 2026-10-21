(() => {
  const VER = window.NUXIVA_ASSET_V ? `?v=${window.NUXIVA_ASSET_V}` : "";
  const SHAPES = ["box", "cylinder", "cone", "sphere", "torus", "capsule", "wedge"];
  const STEPS = [0.5, 1, 5, 10];
  const AXES = ["x", "y", "z"];
  const scripts = {};
  const rad = (d) => (d * Math.PI) / 180;
  const round = (v) => Math.round(v * 100) / 100;
  const safeColor = (c) => (/^#[0-9a-fA-F]{6}$/.test(String(c)) ? c : "#9aa4b2");

  const script = (name) => scripts[name] || (scripts[name] = new Promise((ok, ko) => {
    const s = document.createElement("script");
    s.src = `/vendor/${name}${VER}`; s.onload = ok; s.onerror = () => ko(new Error("library"));
    document.head.appendChild(s);
  }));

  async function ensure() {
    for (let i = 0; i < 30 && !window.THREE && document.querySelector('script[src*="three.min.js"]'); i++) await new Promise((r) => setTimeout(r, 100));
    if (!window.THREE) await script("three.min.js");
    if (!THREE.OrbitControls) await script("OrbitControls.js");
  }

  const call = (mid, path, body) => fetch(`/api/models3d/${encodeURIComponent(mid)}/studio${path}`, {
    method: body === undefined ? "GET" : "POST", headers: { "Content-Type": "application/json" }, body: body === undefined ? undefined : JSON.stringify(body),
  }).then(async (r) => {
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(typeof data.detail === "string" ? data.detail : "server");
    return data;
  });

  function wedge(w, h, d) {
    const x = w / 2, y = h / 2, z = d / 2, v = [];
    const quad = (a, b, c, e) => v.push(...a, ...b, ...c, ...a, ...c, ...e);
    quad([-x, -y, z], [x, -y, z], [x, y, -z], [-x, y, -z]);
    quad([x, -y, -z], [-x, -y, -z], [-x, y, -z], [x, y, -z]);
    quad([-x, -y, -z], [x, -y, -z], [x, -y, z], [-x, -y, z]);
    v.push(x, -y, z, x, -y, -z, x, y, -z, -x, -y, -z, -x, -y, z, -x, y, -z);
    const g = new THREE.BufferGeometry().setAttribute("position", new THREE.Float32BufferAttribute(v, 3));
    g.computeVertexNormals();
    return g;
  }

  function capsule(r, h) {
    const body = Math.max(0, h - 2 * r) / 2, pts = [];
    for (let i = 0; i <= 8; i++) { const a = -Math.PI / 2 + (Math.PI / 2) * (i / 8); pts.push(new THREE.Vector2(Math.max(0.0001, r * Math.cos(a)), -body + r * Math.sin(a))); }
    for (let i = 0; i <= 8; i++) { const a = (Math.PI / 2) * (i / 8); pts.push(new THREE.Vector2(Math.max(0.0001, r * Math.cos(a)), body + r * Math.sin(a))); }
    return new THREE.LatheGeometry(pts, 32);
  }

  function geometry(p) {
    const s = p.size || [1, 1, 1], r = p.radius ?? Math.max(s[0], s[2]) / 2, h = p.height ?? s[1];
    if (p.shape === "cylinder") return new THREE.CylinderGeometry(p.radius_top ?? r, p.radius_bottom ?? r, h, 32);
    if (p.shape === "cone") return new THREE.CylinderGeometry(p.radius_top ?? 0.0001, p.radius_bottom ?? r, h, 32);
    if (p.shape === "sphere") return new THREE.SphereGeometry(r, 32, 16);
    if (p.shape === "capsule") return capsule(r, h);
    if (p.shape === "torus") return new THREE.TorusGeometry(r, p.tube ?? r * 0.25, 16, 40).rotateX(Math.PI / 2);
    if (p.shape === "wedge") return wedge(s[0], s[1], s[2]);
    return new THREE.BoxGeometry(s[0], s[1], s[2]);
  }

  function mesh(p, index, selected) {
    const metal = !!p.metal;
    const m = new THREE.Mesh(geometry(p), new THREE.MeshStandardMaterial({
      color: safeColor(p.color), metalness: metal ? 0.8 : 0.1, roughness: metal ? 0.3 : 0.6,
      emissive: selected ? 0x29e0ff : 0x000000, emissiveIntensity: selected ? 0.28 : 0,
    }));
    const pos = p.position || [0, 0, 0], rot = p.rotation || [0, 0, 0], k = p.scale || [1, 1, 1];
    m.position.set(pos[0], pos[1], pos[2]);
    m.rotation.set(rad(rot[0]), rad(rot[1]), rad(rot[2]), "XYZ");
    m.scale.set(k[0], k[1], k[2]);
    m.userData.i = index;
    return m;
  }

  const extent = (st, i) => (st.state.measures.parts[i] ? st.state.measures.parts[i].size : [0, 0, 0]);

  function partsHtml(st, ctx) {
    const { parts, selected } = st.state;
    return parts.map((p, i) => `<button type="button" class="s3-part${i === selected ? " on" : ""}" data-a="sel" data-i="${i}"><i style="background:${safeColor(p.color)}"></i><span>${ctx.esc(p.name || p.shape)}</span><small>${extent(st, i).map((v) => round(v)).join("×")}</small></button>`).join("");
  }

  function addHtml(ctx) {
    return SHAPES.map((s) => `<button type="button" class="s3-btn" data-a="add" data-shape="${s}">${ctx.icon("cube")} ${ctx.esc(ctx.t(`shape_${s}`))}</button>`).join("");
  }

  function fieldRow(ctx, label, group, values, attr) {
    return `<div class="s3-field"><span>${ctx.esc(label)}</span>${values.map((v, k) => `<input type="number" step="0.1" inputmode="decimal" data-f="${group}" data-k="${k}" ${attr || ""} value="${round(v)}" aria-label="${ctx.esc(label)} ${AXES[k].toUpperCase()}">`).join("")}</div>`;
  }

  function inspectorHtml(st, ctx) {
    const { parts, selected, colors } = st.state;
    if (selected === null || !parts[selected]) return `<p class="s3-info">${ctx.esc(ctx.t("nothing_selected"))}</p>`;
    const p = parts[selected];
    const swatches = Object.entries(colors).map(([name, hex]) => `<button type="button" class="s3-swatch${hex.toLowerCase() === String(p.color).toLowerCase() ? " on" : ""}" style="--c:${safeColor(hex)}" data-a="color" data-c="${hex}" title="${ctx.esc(name)}" aria-label="${ctx.esc(name)}"></button>`).join("");
    const nudges = AXES.map((a) => `<button type="button" class="s3-btn" data-a="nudge" data-axis="${a}" data-sign="-1">−${a.toUpperCase()}</button><button type="button" class="s3-btn" data-a="nudge" data-axis="${a}" data-sign="1">+${a.toUpperCase()}</button>`).join("");
    const steps = STEPS.map((v) => `<button type="button" class="s3-btn${st.step === v ? " on" : ""}" data-a="step" data-v="${v}">${v}</button>`).join("");
    return `<input class="s3-name" data-f="name" maxlength="40" value="${ctx.esc(p.name || "")}" aria-label="${ctx.esc(ctx.t("name"))}">
      ${fieldRow(ctx, ctx.t("position"), "position", p.position || [0, 0, 0])}
      ${fieldRow(ctx, ctx.t("rotation"), "rotation", p.rotation || [0, 0, 0])}
      ${fieldRow(ctx, ctx.t("size"), "dimension", extent(st, selected))}
      <div class="s3-row">${steps}</div><div class="s3-axes">${nudges}</div>
      <div class="s3-row"><button type="button" class="s3-btn" data-a="scale" data-f="0.9">−10%</button><button type="button" class="s3-btn" data-a="scale" data-f="1.1">+10%</button>
        <button type="button" class="s3-btn" data-a="rotate" data-d="90">${ctx.icon("refresh")} 90°</button></div>
      <div class="s3-row">${swatches}</div>
      <div class="s3-row"><button type="button" class="s3-btn" data-a="dup">${ctx.icon("copy")} ${ctx.esc(ctx.t("duplicate"))}</button>
        <button type="button" class="s3-btn danger" data-a="del">${ctx.icon("close")} ${ctx.esc(ctx.t("remove"))}</button></div>`;
  }

  function shell(st, ctx) {
    const s = st.state, hints = ["hint_move", "hint_color", "hint_add", "hint_size", "hint_undo"].map((k) => `<span>«${ctx.esc(ctx.t(k))}»</span>`).join("");
    const base = /^\/api\/models3d\//.test(String(s.url || "")) ? s.url : "";
    const files = base ? (s.files || []).slice(0, 8).map((f) => `<a class="s3-btn" href="${ctx.esc(base + encodeURIComponent(f))}" download>${ctx.icon("download")} ${ctx.esc(f)}</a>`).join("") : "";
    st.el.innerHTML = `${ctx.head({ icon: "cube", label: ctx.t("label"), title: s.title || "", chip: ctx.count("parts", s.parts.length) })}
      <div class="s3-wrap"><div class="s3"><div class="s3-stage"><canvas tabindex="0"></canvas><div class="s3-msg">${ctx.esc(ctx.t("loading"))}</div>
        <div class="s3-tools"><button class="s3-btn" type="button" data-a="undo" title="${ctx.esc(ctx.t("undo"))}">${ctx.icon("refresh")}</button>
          <button class="s3-btn" type="button" data-a="redo" title="${ctx.esc(ctx.t("redo"))}">${ctx.icon("play")}</button>
          <button class="s3-btn" type="button" data-a="ground" title="${ctx.esc(ctx.t("ground"))}">${ctx.icon("download")}</button>
          <button class="s3-btn" type="button" data-a="fit" title="${ctx.esc(ctx.t("fit"))}">${ctx.icon("expand")}</button>
          <button class="s3-btn" type="button" data-a="wire" title="${ctx.esc(ctx.t("wire"))}">${ctx.icon("cube")}</button>
          <button class="s3-btn" type="button" data-a="close" title="${ctx.esc(ctx.t("close"))}">${ctx.icon("close")}</button></div>
        <span class="s3-dim" data-d="x"></span><span class="s3-dim" data-d="y"></span><span class="s3-dim" data-d="z"></span></div>
        <div class="s3-side"><section class="s3-sec"><h4>${ctx.esc(ctx.t("parts"))}</h4><div class="s3-parts"></div></section>
          <section class="s3-sec"><h4>${ctx.esc(ctx.t("add"))}</h4><div class="s3-row">${addHtml(ctx)}</div></section>
          <section class="s3-sec"><h4>${ctx.esc(ctx.t("inspector"))}</h4><div class="s3-ins"></div></section>
          <section class="s3-sec"><h4>${ctx.esc(ctx.t("hints_title"))}</h4><div class="s3-hints">${hints}</div><p class="s3-info">${ctx.esc(ctx.t("hint_hands"))}</p></section>
          ${files ? `<section class="s3-sec"><h4>${ctx.esc(ctx.t("export"))}</h4><div class="s3-files">${files}</div></section>` : ""}</div></div></div>
      <div class="s3-info"><span class="s3-stats"></span></div>`;
  }

  function refresh(st, ctx) {
    const s = st.state, root = st.el;
    root.querySelector(".s3-parts").innerHTML = partsHtml(st, ctx);
    root.querySelector(".s3-ins").innerHTML = inspectorHtml(st, ctx);
    root.querySelector('[data-a="undo"]').disabled = !s.can_undo;
    root.querySelector('[data-a="redo"]').disabled = !s.can_redo;
    const size = s.measures.overall.size.map((v) => round(v));
    root.querySelector(".s3-stats").textContent = `${ctx.count("parts", s.parts.length)} · ${size.join(" × ")} cm`;
    if (st.group) {
      st.scene.remove(st.group);
      st.group.traverse((o) => { if (o.geometry) o.geometry.dispose(); if (o.material) o.material.dispose(); });
      st.group = new THREE.Group();
      s.parts.forEach((p, i) => st.group.add(mesh(p, i, i === s.selected)));
      st.scene.add(st.group);
      st.wire && st.group.traverse((o) => { if (o.material) o.material.wireframe = true; });
      updateBox(st);
    }
  }

  function updateBox(st) {
    const o = st.state.measures.overall;
    if (st.box) st.scene.remove(st.box);
    st.bounds = new THREE.Box3(new THREE.Vector3(...o.min), new THREE.Vector3(...o.max));
    st.box = new THREE.Box3Helper(st.bounds, 0x29e0ff);
    st.box.material.transparent = true; st.box.material.opacity = 0.45;
    st.scene.add(st.box);
  }

  function labels(st) {
    const b = st.bounds, size = st.state.measures.overall.size, stage = st.stage;
    if (!b || !stage.clientWidth) return;
    const spots = { x: [(b.min.x + b.max.x) / 2, b.min.y, b.max.z], y: [b.max.x, (b.min.y + b.max.y) / 2, b.max.z], z: [b.max.x, b.min.y, (b.min.z + b.max.z) / 2] };
    AXES.forEach((a, k) => {
      const tag = stage.querySelector(`.s3-dim[data-d="${a}"]`), v = new THREE.Vector3(...spots[a]).project(st.camera);
      const visible = v.z < 1 && size[k] > 0;
      tag.style.display = visible ? "" : "none";
      tag.textContent = `${round(size[k])} cm`;
      tag.style.left = `${((v.x + 1) / 2) * stage.clientWidth}px`;
      tag.style.top = `${((1 - v.y) / 2) * stage.clientHeight}px`;
    });
  }

  function fit(st) {
    const o = st.state.measures.overall, c = new THREE.Vector3(...o.min).add(new THREE.Vector3(...o.max)).multiplyScalar(0.5);
    const radius = Math.max(8, new THREE.Vector3(...o.size).length() / 2);
    st.controls.target.copy(c);
    st.camera.position.copy(c).add(new THREE.Vector3(1, 0.7, 1.2).normalize().multiplyScalar(radius * 2.6));
    st.controls.update();
  }

  async function boot(st, ctx) {
    await ensure();
    if (!st.alive) return;
    st.stage = st.el.querySelector(".s3-stage");
    const canvas = st.stage.querySelector("canvas");
    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
    st.renderer = renderer;
    st.scene = new THREE.Scene();
    st.camera = new THREE.PerspectiveCamera(40, 1, 0.1, 5000);
    st.scene.add(new THREE.HemisphereLight(0xdff6ff, 0x0b1a2a, 1.0));
    const sun = new THREE.DirectionalLight(0xffffff, 0.9); sun.position.set(60, 100, 80); st.scene.add(sun);
    const rim = new THREE.DirectionalLight(0x29e0ff, 0.45); rim.position.set(-80, 40, -60); st.scene.add(rim);
    const grid = new THREE.GridHelper(200, 40, 0x29e0ff, 0x123044);
    grid.material.transparent = true; grid.material.opacity = 0.35; st.scene.add(grid);
    st.controls = new THREE.OrbitControls(st.camera, canvas);
    st.controls.enableDamping = true;
    st.group = new THREE.Group(); st.scene.add(st.group);
    refresh(st, ctx);
    fit(st);
    st.stage.querySelector(".s3-msg").remove();
    pick(st, canvas);
    const frame = () => {
      if (!st.alive || !st.el.isConnected) { renderer.dispose(); return; }
      const w = st.stage.clientWidth, h = st.stage.clientHeight;
      if (canvas.width !== Math.floor(w * renderer.getPixelRatio()) || canvas.height !== Math.floor(h * renderer.getPixelRatio())) {
        renderer.setSize(w, h, false); st.camera.aspect = w / Math.max(1, h); st.camera.updateProjectionMatrix();
      }
      st.controls.update();
      renderer.render(st.scene, st.camera);
      labels(st);
      st.raf = requestAnimationFrame(frame);
    };
    frame();
  }

  function pick(st, canvas) {
    let start = null;
    canvas.addEventListener("pointerdown", (e) => { start = { x: e.clientX, y: e.clientY, t: Date.now() }; });
    canvas.addEventListener("pointerup", (e) => {
      if (!start || Math.hypot(e.clientX - start.x, e.clientY - start.y) > 6 || Date.now() - start.t > 600) return;
      const r = canvas.getBoundingClientRect(), ndc = new THREE.Vector2(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
      const ray = new THREE.Raycaster(); ray.setFromCamera(ndc, st.camera);
      const hit = ray.intersectObjects(st.group.children, false)[0];
      send(st, { op: "select", index: hit ? hit.object.userData.i : null });
    });
  }

  function notify(st, text) {
    if (!st.stage) return;
    let m = st.stage.querySelector(".s3-msg");
    if (!m) { m = document.createElement("div"); m.className = "s3-msg err"; st.stage.appendChild(m); }
    m.textContent = text; m.classList.add("err");
    clearTimeout(st.timer);
    st.timer = setTimeout(() => m.remove(), 3500);
  }

  function send(st, body) {
    if (st.busy) return Promise.resolve();
    st.busy = true;
    return call(st.id, "/op", body).then((s) => { st.state = s; refresh(st, st.ctx); }).catch((e) => notify(st, e.message)).finally(() => { st.busy = false; });
  }

  function onClick(st, e) {
    const b = e.target.closest("[data-a]");
    if (!b || !st.el.contains(b)) return;
    const a = b.dataset.a, sel = st.state.selected, d = b.dataset;
    if (a === "sel") return send(st, { op: "select", index: Number(d.i) });
    if (a === "add") return send(st, { op: "add", shape: d.shape, color: "#29e0ff" });
    if (["undo", "redo", "ground"].includes(a)) return send(st, { op: a });
    if (a === "fit") return fit(st);
    if (a === "wire") { st.wire = !st.wire; b.classList.toggle("on", st.wire); st.group.traverse((o) => { if (o.material) o.material.wireframe = st.wire; }); return; }
    if (a === "close") return call(st.id, "/close", {}).catch((err) => notify(st, err.message));
    if (a === "step") { st.step = Number(d.v); return refresh(st, st.ctx); }
    if (sel === null) return;
    if (a === "color") return send(st, { op: "update", index: sel, changes: { color: d.c } });
    if (a === "nudge") return send(st, { op: "move", index: sel, axis: d.axis, delta: Number(d.sign) * st.step });
    if (a === "scale") return send(st, { op: "scale", index: sel, factor: Number(d.f) });
    if (a === "rotate") return send(st, { op: "rotate", index: sel, axis: "y", degrees: Number(d.d) });
    if (a === "dup") return send(st, { op: "duplicate", index: sel });
    if (a === "del") return send(st, { op: "remove", index: sel });
  }

  function onChange(st, e) {
    const f = e.target.dataset && e.target.dataset.f, sel = st.state.selected;
    if (!f || sel === null) return;
    if (f === "name") return send(st, { op: "update", index: sel, changes: { name: e.target.value } });
    const k = Number(e.target.dataset.k), value = Number(e.target.value);
    if (!Number.isFinite(value)) return refresh(st, st.ctx);
    if (f === "dimension") return send(st, { op: "dimension", index: sel, axis: AXES[k], value });
    const current = [...(st.state.parts[sel][f] || [0, 0, 0])];
    current[k] = value;
    send(st, { op: "update", index: sel, changes: { [f]: current } });
  }

  const screenAxes = (st) => ({ right: new THREE.Vector3().setFromMatrixColumn(st.camera.matrixWorld, 0), up: new THREE.Vector3().setFromMatrixColumn(st.camera.matrixWorld, 1) });

  function orbit(st, g) {
    const target = st.controls.target, offset = st.camera.position.clone().sub(target), { right, up } = screenAxes(st);
    offset.applyAxisAngle(new THREE.Vector3(0, 1, 0), -g.rotate);
    offset.setLength(Math.max(5, Math.min(2000, offset.length() / g.scale)));
    target.addScaledVector(right, -g.pan.x * offset.length()).addScaledVector(up, g.pan.y * offset.length());
    st.camera.position.copy(target).add(offset);
    st.controls.update();
  }

  function flush(st) {
    clearTimeout(st.flushTimer);
    st.flushTimer = 0;
    const a = st.acc, sel = st.state.selected;
    if (!a || sel === null || (a.scale === 1 && !a.rot && !a.move.some(Boolean))) return;
    if (st.busy) { st.flushTimer = setTimeout(() => flush(st), 120); return; }
    st.acc = { scale: 1, rot: 0, move: [0, 0, 0] };
    send(st, { op: "transform", index: sel, factor: a.scale, degrees: (a.rot * 180) / Math.PI, delta: a.move.map(round) });
  }

  function gesture(st, e) {
    const g = e.detail;
    if (!st.group || !st.stage || !st.stage.isConnected) return;
    e.preventDefault();
    if (g.phase === "start") { st.acc = { scale: 1, rot: 0, move: [0, 0, 0] }; return; }
    if (g.phase === "end") return flush(st);
    const sel = st.state.selected, part = sel === null ? null : st.state.parts[sel];
    if (!part) return orbit(st, g);
    const size = Math.max(10, ...st.state.measures.overall.size), { right, up } = screenAxes(st);
    st.acc = st.acc || { scale: 1, rot: 0, move: [0, 0, 0] };
    st.acc.scale *= g.scale;
    st.acc.rot += g.rotate;
    const step = right.multiplyScalar(g.pan.x * size * 2).addScaledVector(up, -g.pan.y * size * 2);
    st.acc.move = st.acc.move.map((v, i) => v + [step.x, step.y, step.z][i]);
    const m = st.group.children[sel];
    if (m) { m.scale.multiplyScalar(g.scale); m.rotation.y += g.rotate; m.position.add(step); }
    if (!st.flushTimer) st.flushTimer = setTimeout(() => flush(st), 300);
  }

  function mount(el, d, ctx) {
    const st = { el, id: d.id, ctx, alive: true, state: d, step: 1, wire: false, busy: false };
    el._s3 = st;
    shell(st, ctx);
    refresh(st, ctx);
    el.addEventListener("click", (e) => onClick(st, e));
    el.addEventListener("change", (e) => onChange(st, e));
    el.addEventListener("nuxiva-gesture", (e) => gesture(st, e));
    boot(st, ctx).catch((err) => {
      const m = el.querySelector(".s3-msg");
      if (m) { m.textContent = err.message === "library" ? ctx.t("error_library") : err.message; m.classList.add("err"); }
    });
  }

  NuxivaDesk.register("studio_3d", {
    render(el, d, ctx) { if (el._s3) el._s3.alive = false; mount(el, d, ctx); },
    update(el, d, ctx) {
      const st = el._s3;
      if (!st || st.id !== d.id) { if (st) st.alive = false; return mount(el, d, ctx); }
      if (st.state.rev === d.rev && st.state.selected === d.selected && st.state.can_undo === d.can_undo) return;
      st.state = d;
      refresh(st, ctx);
    },
    destroy(el) { const st = el._s3; if (st) { st.alive = false; cancelAnimationFrame(st.raf); clearTimeout(st.timer); clearTimeout(st.flushTimer); if (st.renderer) st.renderer.dispose(); } },
  });
})();
