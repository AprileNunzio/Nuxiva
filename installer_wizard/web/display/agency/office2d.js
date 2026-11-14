(() => {
  const DPR = () => Math.min(2, window.devicePixelRatio || 1);
  const MOTION = () => !window.matchMedia || !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const PLANTS = [
    { x: -5.4, z: -3.3, s: 1.0 },
    { x: 5.4, z: -3.3, s: 1.0 },
    { x: -5.4, z: 3.1, s: 1.1 },
    { x: 5.4, z: 3.1, s: 1.1 },
    { x: -2.2, z: -3.4, s: 0.85 },
    { x: 2.2, z: -3.4, s: 0.85 },
  ];

  function create(host, callbacks = {}) {
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

    const ctx = canvas.getContext("2d");
    const st = {
      w: 0, h: 0, dpr: 1, raf: 0, running: false,
      yaw: 0.72, pitch: 0.56, zoom: 1.0, panX: 0, panY: -18,
      drag: null, hovered: null, selected: null,
      office: null, hits: [],
    };

    function resize() {
      const rect = host.getBoundingClientRect();
      st.w = Math.max(320, rect.width || window.innerWidth);
      st.h = Math.max(260, rect.height || window.innerHeight);
      st.dpr = DPR();
      canvas.width = Math.round(st.w * st.dpr);
      canvas.height = Math.round(st.h * st.dpr);
    }

    function project(x, y, z) {
      const cy = Math.cos(st.yaw), sy = Math.sin(st.yaw);
      const cp = Math.cos(st.pitch), sp = Math.sin(st.pitch);
      const rx = x * cy - z * sy;
      const rz = x * sy + z * cy;
      const ry = y * cp - rz * sp;
      const depth = y * sp + rz * cp;
      const scale = Math.min(st.w, st.h) * 0.078 * st.zoom;
      return {
        x: st.w * 0.5 + st.panX + rx * scale,
        y: st.h * 0.44 + st.panY - ry * scale,
        depth,
        scale,
      };
    }

    function poly(pts, fill, stroke, lineWidth = 1) {
      if (!pts.length) return;
      ctx.beginPath();
      ctx.moveTo(pts[0].x, pts[0].y);
      for (let i = 1; i < pts.length; i += 1) ctx.lineTo(pts[i].x, pts[i].y);
      ctx.closePath();
      if (fill) { ctx.fillStyle = fill; ctx.fill(); }
      if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = lineWidth; ctx.stroke(); }
    }

    function box3d(cx, cy, cz, wx, wy, wz, colors) {
      const hx = wx * 0.5, hz = wz * 0.5;
      const p000 = project(cx - hx, cy, cz - hz);
      const p100 = project(cx + hx, cy, cz - hz);
      const p101 = project(cx + hx, cy, cz + hz);
      const p001 = project(cx - hx, cy, cz + hz);
      const p010 = project(cx - hx, cy + wy, cz - hz);
      const p110 = project(cx + hx, cy + wy, cz - hz);
      const p111 = project(cx + hx, cy + wy, cz + hz);
      const p011 = project(cx - hx, cy + wy, cz + hz);
      poly([p001, p101, p111, p011], colors.front, colors.stroke, 0.9);
      poly([p100, p101, p111, p110], colors.side, colors.stroke, 0.9);
      poly([p000, p001, p011, p010], colors.sideAlt || colors.side, colors.stroke, 0.9);
      poly([p010, p110, p111, p011], colors.top, colors.stroke, 1.0);
    }

    function drawFloor() {
      const hw = 6.2, hd = 4.2;
      const c0 = project(-hw, 0, -hd);
      const c1 = project(hw, 0, -hd);
      const c2 = project(hw, 0, hd);
      const c3 = project(-hw, 0, hd);
      const b2 = project(hw, -0.18, hd);
      const b3 = project(-hw, -0.18, hd);
      const b1 = project(hw, -0.18, -hd);
      poly([c3, c2, b2, b3], "#d5d2ca", "#b8b4aa", 1);
      poly([c2, c1, b1, b2], "#c7c3ba", "#b8b4aa", 1);
      poly([c0, c1, c2, c3], "#f3f1ec", "#dedad0", 1.5);

      ctx.strokeStyle = "rgba(150, 146, 136, 0.26)";
      ctx.lineWidth = 1;
      for (let x = -5; x <= 5; x += 1) {
        const a = project(x, 0.005, -hd + 0.2);
        const b = project(x, 0.005, hd - 0.2);
        ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
      }
      for (let z = -3; z <= 3; z += 1) {
        const a = project(-hw + 0.2, 0.005, z);
        const b = project(hw - 0.2, 0.005, z);
        ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
      }

      const rug0 = project(-2.3, 0.01, -3.7);
      const rug1 = project(2.3, 0.01, -3.7);
      const rug2 = project(2.3, 0.01, -1.1);
      const rug3 = project(-2.3, 0.01, -1.1);
      poly([rug0, rug1, rug2, rug3], "rgba(18, 42, 68, 0.08)", "rgba(41, 224, 255, 0.35)", 1.2);
    }

    function drawPlant(p, t) {
      const sway = Math.sin(t * 1.4 + p.x) * 0.04;
      box3d(p.x, 0, p.z, 0.42 * p.s, 0.36 * p.s, 0.42 * p.s, {
        top: "#e8e4dc", front: "#d6d1c7", side: "#c2bdb2", stroke: "#aba59a",
      });
      const base = project(p.x, 0.36 * p.s, p.z);
      const top = project(p.x + sway, 1.05 * p.s, p.z);
      const r = Math.max(8, base.scale * 0.28 * p.s);
      ctx.fillStyle = "#2d8a61";
      ctx.beginPath(); ctx.arc(top.x, top.y, r, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = "#3ca879";
      ctx.beginPath(); ctx.arc(top.x - r * 0.35, top.y + r * 0.15, r * 0.72, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = "#52c491";
      ctx.beginPath(); ctx.arc(top.x + r * 0.3, top.y - r * 0.2, r * 0.58, 0, Math.PI * 2); ctx.fill();
    }

    function drawDesk(desk) {
      const w = desk.kind === "double" ? 1.72 : 1.15;
      const d = 0.74;
      const occupied = Boolean(desk.occupied);
      box3d(desk.x, 0, desk.z, w - 0.12, 0.42, d - 0.12, {
        top: "#cfd5dd", front: "#b8c0cb", side: "#9fa8b5", stroke: "#8c96a4",
      });
      box3d(desk.x, 0.42, desk.z, w, 0.07, d, {
        top: occupied ? "#ffffff" : "#f5f4f0",
        front: "#dfe3e8",
        side: "#cfd5dc",
        stroke: occupied ? "#29e0ff" : "#b8c0cc",
      });
      const monX = desk.kind === "double" ? [-0.34, 0.34] : [0];
      monX.forEach((dx) => {
        box3d(desk.x + dx, 0.49, desk.z - 0.14, 0.42, 0.28, 0.05, {
          top: "#1e293b",
          front: occupied ? "#0ea5e9" : "#334155",
          side: "#0f172a",
          stroke: occupied ? "#38bdf8" : "#1e293b",
        });
      });
      box3d(desk.x, 0.02, desk.z + 0.46, 0.42, 0.36, 0.42, {
        top: occupied ? "#334155" : "#cbd5e1",
        front: occupied ? "#1e293b" : "#94a3b8",
        side: "#0f172a",
        stroke: "#475569",
      });
    }

    function drawPodium(ceo, t) {
      const x = ceo ? ceo.x : 0;
      const z = ceo ? ceo.z : -3.2;
      box3d(x, 0, z, 2.2, 0.14, 1.25, {
        top: "#1e293b", front: "#0f172a", side: "#090f1d", stroke: "#29e0ff",
      });
      box3d(x, 0.14, z + 0.18, 1.55, 0.48, 0.62, {
        top: "#f8fafc", front: "#1e293b", side: "#0f172a", stroke: "#29e0ff",
      });
      box3d(x, 0.62, z + 0.12, 0.56, 0.34, 0.06, {
        top: "#0ea5e9", front: "#29e0ff", side: "#0284c7", stroke: "#bae6fd",
      });
      if (ceo) drawAvatar(ceo, t, true);
    }

    function drawSharedBrain(brain, t) {
      const x = 0, z = -1.78;
      box3d(x, 0, z, 0.72, 0.68, 0.72, {
        top: "#0f172a", front: "#1e293b", side: "#090d16", stroke: "#29e0ff",
      });
      const bob = Math.sin(t * 2.2) * 0.08;
      const center = project(x, 1.22 + bob, z);
      const r = Math.max(18, center.scale * 0.48);
      const isHit = (st.hovered && st.hovered.kind === "brain") || (st.selected && st.selected.kind === "brain");

      const grad = ctx.createRadialGradient(center.x, center.y, r * 0.1, center.x, center.y, r * 1.65);
      grad.addColorStop(0, "rgba(41, 224, 255, 0.92)");
      grad.addColorStop(0.55, "rgba(14, 165, 233, 0.34)");
      grad.addColorStop(1, "rgba(14, 165, 233, 0)");
      ctx.fillStyle = grad;
      ctx.beginPath(); ctx.arc(center.x, center.y, r * 1.65, 0, Math.PI * 2); ctx.fill();

      ctx.strokeStyle = isHit ? "#ffffff" : "#29e0ff";
      ctx.lineWidth = isHit ? 2.2 : 1.4;
      ctx.beginPath(); ctx.arc(center.x, center.y, r, 0, Math.PI * 2); ctx.stroke();

      for (let i = 0; i < 3; i += 1) {
        const a = t * 0.9 + (i * Math.PI) / 3;
        ctx.beginPath();
        ctx.ellipse(center.x, center.y, r, Math.max(4, Math.abs(Math.sin(a)) * r), a * 0.5, 0, Math.PI * 2);
        ctx.strokeStyle = "rgba(125, 211, 252, 0.78)";
        ctx.lineWidth = 1.1;
        ctx.stroke();
      }

      const labelPos = project(x, 1.82 + bob, z);
      ctx.font = "600 11px system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.fillStyle = "#0f172a";
      const rules = brain ? brain.rules_count : 1687;
      const badge = `CERVELLO · ${rules}`;
      const tw = ctx.measureText(badge).width + 16;
      ctx.fillStyle = "rgba(9, 18, 34, 0.88)";
      ctx.strokeStyle = "#29e0ff";
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.roundRect(labelPos.x - tw * 0.5, labelPos.y - 11, tw, 22, 11);
      ctx.fill(); ctx.stroke();
      ctx.fillStyle = "#e0f2fe";
      ctx.fillText(badge, labelPos.x, labelPos.y + 4);

      st.hits.push({
        kind: "brain",
        id: "shared_brain",
        x: center.x,
        y: center.y,
        r: r * 1.35,
        data: brain,
      });
    }

    function drawAvatar(agent, t, isCeo = false) {
      const bob = agent.status === "running" ? Math.sin(t * 5 + (agent.desk_index || 0)) * 0.04 : 0;
      const x = agent.x || 0;
      const z = isCeo ? (agent.z || -3.2) - 0.18 : (agent.z || 0) + 0.38;
      const yBase = isCeo ? 0.18 : 0.22;
      const hoodie = isCeo ? "#0284c7" : (agent.hoodie_color || "#ff6b1a");
      const hoodieSide = isCeo ? "#0369a1" : "#d9530f";
      const hoodieTop = isCeo ? "#38bdf8" : "#ff853d";

      box3d(x, yBase, z, 0.38, 0.44 + bob, 0.28, {
        top: hoodieTop, front: hoodie, side: hoodieSide, stroke: "#1e293b",
      });

      const headP = project(x, yBase + 0.62 + bob, z);
      const hr = Math.max(7, headP.scale * 0.16);
      ctx.fillStyle = hoodie;
      ctx.beginPath(); ctx.arc(headP.x, headP.y, hr * 1.18, Math.PI * 0.85, Math.PI * 2.15); ctx.fill();
      ctx.fillStyle = "#fde68a";
      ctx.beginPath(); ctx.arc(headP.x, headP.y + 1, hr * 0.88, 0, Math.PI * 2); ctx.fill();

      const selected = st.selected && st.selected.id === agent.id;
      const hovered = st.hovered && st.hovered.id === agent.id;
      if (selected || hovered || agent.status === "running" || agent.status === "review") {
        const ringP = project(x, 0.03, z);
        ctx.strokeStyle = selected ? "#29e0ff" : hovered ? "#ff6b1a" : agent.status === "review" ? "#a855f7" : "#10b981";
        ctx.lineWidth = selected || hovered ? 2.5 : 1.6;
        ctx.beginPath();
        ctx.ellipse(ringP.x, ringP.y, hr * 1.9, hr * 0.95, 0, 0, Math.PI * 2);
        ctx.stroke();
      }

      const tagP = project(x, yBase + 0.98 + bob, z);
      ctx.font = "600 11px system-ui, sans-serif";
      const text = isCeo ? `CEO · ${agent.name}` : agent.name;
      const tw = ctx.measureText(text).width + 14;
      ctx.fillStyle = isCeo ? "rgba(8, 47, 73, 0.92)" : "rgba(24, 24, 27, 0.88)";
      ctx.strokeStyle = isCeo ? "#29e0ff" : "#ff6b1a";
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.roundRect(tagP.x - tw * 0.5, tagP.y - 10, tw, 20, 10);
      ctx.fill(); ctx.stroke();
      ctx.fillStyle = "#ffffff";
      ctx.textAlign = "center";
      ctx.fillText(text, tagP.x, tagP.y + 4);

      const torsoP = project(x, yBase + 0.36, z);
      st.hits.push({
        kind: isCeo ? "ceo" : "agent",
        id: agent.id,
        x: torsoP.x,
        y: (headP.y + torsoP.y) * 0.5,
        r: Math.max(22, hr * 2.4),
        data: agent,
      });
    }

    function drawFrame(now) {
      const t = (now || 0) * 0.001;
      ctx.setTransform(st.dpr, 0, 0, st.dpr, 0, 0);
      ctx.clearRect(0, 0, st.w, st.h);

      const bg = ctx.createLinearGradient(0, 0, 0, st.h);
      bg.addColorStop(0, "#e7e5df");
      bg.addColorStop(0.55, "#dedad2");
      bg.addColorStop(1, "#cfd2d6");
      ctx.fillStyle = bg;
      ctx.fillRect(0, 0, st.w, st.h);

      st.hits = [];
      drawFloor();

      const office = st.office || {};
      const items = [];
      PLANTS.forEach((p) => items.push({ z: project(p.x, 0, p.z).depth, fn: () => drawPlant(p, t) }));
      (office.desks || []).forEach((d) => items.push({ z: project(d.x, 0, d.z).depth, fn: () => drawDesk(d) }));
      if (office.ceo) items.push({ z: project(office.ceo.x, 0, office.ceo.z).depth, fn: () => drawPodium(office.ceo, t) });
      items.push({ z: project(0, 0, -1.78).depth, fn: () => drawSharedBrain(office.shared_brain, t) });
      (office.agents || []).filter((a) => a.seated).forEach((a) => {
        items.push({ z: project(a.x, 0, a.z + 0.35).depth, fn: () => drawAvatar(a, t, false) });
      });

      items.sort((a, b) => a.z - b.z).forEach((item) => item.fn());

      if (st.running && MOTION()) st.raf = requestAnimationFrame(drawFrame);
    }

    function hitAt(clientX, clientY) {
      const rect = canvas.getBoundingClientRect();
      const x = clientX - rect.left;
      const y = clientY - rect.top;
      for (let i = st.hits.length - 1; i >= 0; i -= 1) {
        const h = st.hits[i];
        if (Math.hypot(x - h.x, y - h.y) <= h.r) return { hit: h, x, y };
      }
      return { hit: null, x, y };
    }

    function showTip(hit, x, y) {
      if (!hit) { tip.hidden = true; return; }
      tip.hidden = false;
      tip.style.left = `${Math.min(st.w - 220, Math.max(16, x + 14))}px`;
      tip.style.top = `${Math.max(16, y - 18)}px`;
      if (hit.kind === "brain") {
        const b = hit.data || {};
        tipName.textContent = "Cervello Condiviso";
        tipRole.textContent = "NunzioTech Agency";
        tipThought.textContent = `${b.rules_count || 1687} regole · ${b.reviews_count || 943} revisioni`;
      } else {
        const a = hit.data || {};
        tipName.textContent = a.name || a.id;
        tipRole.textContent = `${a.department || ""} · ${a.role || ""}`;
        tipThought.textContent = a.thought || "";
      }
    }

    canvas.addEventListener("pointerdown", (e) => {
      st.drag = { x: e.clientX, y: e.clientY, yaw: st.yaw, panX: st.panX, panY: st.panY, moved: false };
    });

    window.addEventListener("pointermove", (e) => {
      if (st.drag) {
        const dx = e.clientX - st.drag.x;
        const dy = e.clientY - st.drag.y;
        if (Math.hypot(dx, dy) > 5) st.drag.moved = true;
        if (e.shiftKey) {
          st.panX = st.drag.panX + dx;
          st.panY = st.drag.panY + dy;
        } else {
          st.yaw = Math.max(0.25, Math.min(1.25, st.drag.yaw + dx * 0.0045));
          st.panY = Math.max(-90, Math.min(60, st.drag.panY + dy * 0.45));
        }
        if (!MOTION()) drawFrame(performance.now());
        return;
      }
      const { hit, x, y } = hitAt(e.clientX, e.clientY);
      st.hovered = hit;
      canvas.style.cursor = hit ? "pointer" : "grab";
      showTip(hit, x, y);
    });

    window.addEventListener("pointerup", (e) => {
      if (!st.drag) return;
      const moved = st.drag.moved;
      st.drag = null;
      if (!moved) {
        const { hit } = hitAt(e.clientX, e.clientY);
        if (hit) {
          st.selected = hit;
          if (hit.kind === "brain" && callbacks.onSelectBrain) callbacks.onSelectBrain(hit.data);
          else if (callbacks.onSelectAgent) callbacks.onSelectAgent(hit.data);
          if (!MOTION()) drawFrame(performance.now());
        }
      }
    });

    canvas.addEventListener("wheel", (e) => {
      e.preventDefault();
      st.zoom = Math.max(0.68, Math.min(1.55, st.zoom - e.deltaY * 0.0008));
      if (!MOTION()) drawFrame(performance.now());
    }, { passive: false });

    window.addEventListener("resize", () => { if (st.running) { resize(); drawFrame(performance.now()); } });

    function update(office) {
      st.office = office;
      if (!st.running) {
        st.running = true;
        resize();
        drawFrame(performance.now());
      } else if (!MOTION()) {
        drawFrame(performance.now());
      }
    }

    function stop() {
      st.running = false;
      cancelAnimationFrame(st.raf);
    }

    return { update, stop, select(id) { st.selected = id ? { id } : null; } };
  }

  window.NuxivaAgencyOffice2D = { create };
})();
