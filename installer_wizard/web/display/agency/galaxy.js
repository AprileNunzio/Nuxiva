(() => {
  const STATUS_HUE = { planning: 200, running: 170, waiting_user: 45, paused: 30, completed: 140, failed: 350, cancelled: 220 };
  const TAU = Math.PI * 2;

  function stars(count, w, h) {
    return Array.from({ length: count }, () => ({ x: Math.random() * w, y: Math.random() * h, r: Math.random() * 1.3 + 0.2, p: Math.random() * TAU }));
  }

  function create(canvas, layer, onPick) {
    const ctx = canvas.getContext("2d");
    const st = { projects: [], nodes: new Map(), field: [], raf: 0, t: 0, w: 0, h: 0, dpr: 1, selected: 0, still: false, calm: false };
    const motion = window.matchMedia ? window.matchMedia("(prefers-reduced-motion: reduce)") : null;

    function resize() {
      st.dpr = Math.min(2, window.devicePixelRatio || 1);
      st.w = canvas.clientWidth; st.h = canvas.clientHeight;
      canvas.width = Math.round(st.w * st.dpr); canvas.height = Math.round(st.h * st.dpr);
      ctx.setTransform(st.dpr, 0, 0, st.dpr, 0, 0);
      st.field = stars(Math.round((st.w * st.h) / 5200), st.w, st.h);
    }

    function node(project) {
      let entry = st.nodes.get(project.id);
      if (!entry) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "ag-planet";
        const name = document.createElement("span"); name.className = "ag-planet-name";
        const pct = document.createElement("span"); pct.className = "ag-planet-pct";
        button.append(name, pct);
        button.addEventListener("click", () => onPick(project.id));
        layer.appendChild(button);
        entry = { button, name, pct, angle: 0, sparks: [] };
        st.nodes.set(project.id, entry);
      }
      entry.project = project;
      entry.name.textContent = project.title;
      entry.pct.textContent = `${project.percent}%`;
      entry.button.dataset.status = project.status;
      entry.button.setAttribute("aria-label", `${project.title} ${project.percent}%`);
      const want = Math.min(12, project.counts.running);
      while (entry.sparks.length < want) entry.sparks.push({ a: Math.random() * TAU, s: 0.6 + Math.random() * 0.9, r: 1.25 + Math.random() * 0.5 });
      entry.sparks.length = want;
      return entry;
    }

    function update(projects) {
      st.projects = projects;
      const keep = new Set(projects.map((p) => p.id));
      st.nodes.forEach((entry, id) => { if (!keep.has(id)) { entry.button.remove(); st.nodes.delete(id); } });
      projects.forEach(node);
      st.selected = Math.min(st.selected, Math.max(0, projects.length - 1));
      mark();
    }

    function mark() {
      st.projects.forEach((p, i) => st.nodes.get(p.id).button.classList.toggle("is-selected", i === st.selected));
    }

    function place(i, count) {
      const ring = i % 3, cx = st.w / 2, cy = st.h * 0.52;
      const rx = Math.max(60, Math.min(st.w / 2 - (st.w < 640 ? 44 : 70), 520)) * (0.5 + ring * 0.25);
      const ry = rx * flat();
      const entry = st.nodes.get(st.projects[i].id);
      const speed = st.still ? 0 : 0.00006 / (1 + ring * 0.6);
      entry.angle += speed * 16;
      const a = entry.angle + (i / Math.max(1, count)) * TAU;
      return { x: cx + Math.cos(a) * rx, y: cy + Math.sin(a) * ry, depth: (Math.sin(a) + 1) / 2, rx, ry, cx, cy };
    }

    function flat() {
      return Math.min(1, Math.max(0.38, (st.h / Math.max(1, st.w)) * 0.3));
    }

    function drawCore(cx, cy) {
      const pulse = 1 + Math.sin(st.t / 900) * 0.06;
      const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, 90 * pulse);
      g.addColorStop(0, "rgba(160,240,255,0.95)"); g.addColorStop(0.25, "rgba(60,180,255,0.45)"); g.addColorStop(1, "rgba(0,40,90,0)");
      ctx.fillStyle = g; ctx.beginPath(); ctx.arc(cx, cy, 90 * pulse, 0, TAU); ctx.fill();
    }

    function drawPlanet(entry, at) {
      const p = entry.project, hue = STATUS_HUE[p.status] ?? 200;
      const scale = Math.min(1, Math.max(0.55, st.w / 1100));
      const size = (16 + Math.min(26, Math.sqrt(p.counts.total || 1) * 4)) * (0.75 + at.depth * 0.5) * scale;
      const glow = ctx.createRadialGradient(at.x, at.y, size * 0.2, at.x, at.y, size * 2.4);
      glow.addColorStop(0, `hsla(${hue},90%,70%,0.9)`); glow.addColorStop(0.4, `hsla(${hue},90%,50%,0.25)`); glow.addColorStop(1, `hsla(${hue},90%,40%,0)`);
      ctx.fillStyle = glow; ctx.beginPath(); ctx.arc(at.x, at.y, size * 2.4, 0, TAU); ctx.fill();
      ctx.fillStyle = `hsl(${hue},70%,${32 + at.depth * 20}%)`; ctx.beginPath(); ctx.arc(at.x, at.y, size, 0, TAU); ctx.fill();
      ctx.lineWidth = 3; ctx.strokeStyle = `hsla(${hue},100%,80%,0.25)`;
      ctx.beginPath(); ctx.arc(at.x, at.y, size + 7, 0, TAU); ctx.stroke();
      ctx.strokeStyle = `hsla(${hue},100%,75%,0.95)`;
      ctx.beginPath(); ctx.arc(at.x, at.y, size + 7, -Math.PI / 2, -Math.PI / 2 + (p.percent / 100) * TAU); ctx.stroke();
      entry.sparks.forEach((s) => {
        s.a += st.still ? 0 : 0.002 * s.s * 16;
        const sx = at.x + Math.cos(s.a) * size * s.r * 1.6, sy = at.y + Math.sin(s.a) * size * s.r * 0.7;
        ctx.fillStyle = `hsla(${hue},100%,85%,0.95)`; ctx.beginPath(); ctx.arc(sx, sy, 2.2, 0, TAU); ctx.fill();
      });
      entry.button.style.transform = `translate(${at.x}px, ${at.y}px) translate(-50%, -50%)`;
      entry.button.style.setProperty("--size", `${Math.round(size * 2 + 14)}px`);
      entry.button.style.zIndex = String(Math.round(at.depth * 100));
    }

    function frame(now) {
      st.raf = requestAnimationFrame(frame);
      st.t = now;
      st.still = Boolean(motion && motion.matches) || document.body.classList.contains("tier-minimal");
      ctx.clearRect(0, 0, st.w, st.h);
      st.field.forEach((s) => {
        ctx.globalAlpha = 0.35 + Math.sin(now / 1400 + s.p) * 0.25;
        ctx.fillStyle = "#cfe9ff"; ctx.fillRect(s.x, s.y, s.r, s.r);
      });
      ctx.globalAlpha = 1;
      const count = st.projects.length;
      const cx = st.w / 2, cy = st.h * 0.52;
      if (st.calm) { drawCore(cx, cy); return; }
      const placed = st.projects.map((_, i) => place(i, count));
      ctx.strokeStyle = "rgba(120,200,255,0.12)"; ctx.lineWidth = 1;
      [...new Set(placed.map((a) => a.rx))].forEach((rx) => { ctx.beginPath(); ctx.ellipse(cx, cy, rx, rx * flat(), 0, 0, TAU); ctx.stroke(); });
      const order = placed.map((at, i) => ({ at, i })).sort((a, b) => a.at.depth - b.at.depth);
      order.filter((o) => o.at.depth < 0.5).forEach((o) => drawPlanet(st.nodes.get(st.projects[o.i].id), o.at));
      drawCore(cx, cy);
      order.filter((o) => o.at.depth >= 0.5).forEach((o) => drawPlanet(st.nodes.get(st.projects[o.i].id), o.at));
    }

    function step(delta) {
      if (!st.projects.length) return null;
      st.selected = (st.selected + delta + st.projects.length) % st.projects.length;
      mark();
      return st.projects[st.selected].id;
    }

    function start() { if (!st.raf) { resize(); st.raf = requestAnimationFrame(frame); } }
    function stop() { cancelAnimationFrame(st.raf); st.raf = 0; }

    window.addEventListener("resize", () => { if (st.raf) resize(); });
    function calm(on) { st.calm = Boolean(on); }

    return { update, start, stop, step, calm, get selected() { return st.projects[st.selected] ? st.projects[st.selected].id : null; } };
  }

  window.NuxivaAgencyGalaxy = { create };
})();
