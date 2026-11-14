(() => {
  const LAB = (window.NuxivaLab = window.NuxivaLab || {});
  const T = (key, params) => LAB.screen.T(key, params);

  function create(x) {
    const S = x.S;

    function paintScreens(t, force) {
      const spec = x.quality.spec;
      S.stations.forEach((st, i) => {
        const agent = st.owner;
        const person = agent && S.people.get(agent.id);
        const mode = person ? person.mode || "idle" : "empty";
        const interval = mode === "work" ? 1 / spec.screens : 1.2;
        if (!force && t - st.painted < interval) return;
        st.painted = t;
        const label = agent ? T(LAB.behavior.LABEL[mode] || "lab_state_idle", { name: person && person.target ? (S.data.agents.find((a) => a.id === person.target) || {}).name || "" : "" }) : "";
        const view = { mode, name: agent ? agent.name : "", label, tasks: agent ? (agent.tasks || []).map((x) => ({ title: x.title || "", status: x.status, attempts: x.attempts || 0 })) : [] };
        const sig = `${mode}|${label}|${view.tasks.map((x) => x.status + x.title).join(",")}`;
        if (!agent) {
          if (st.key === "empty") return;
          st.key = "empty";
          st.ctx.fillStyle = "#04070c";
          st.ctx.fillRect(0, 0, st.canvas.width, st.canvas.height);
          st.tex.needsUpdate = true;
        } else if (mode === "work" || sig !== st.key) {
          st.key = sig;
          LAB.screen.monitor(st.ctx, st.canvas.width, st.canvas.height, view, t);
          st.tex.needsUpdate = true;
        }
        if (agent && st.plate.key !== agent.name) {
          st.plate.key = agent.name;
          const c = st.plate.getContext("2d");
          c.fillStyle = "#e8ecf1";
          c.fillRect(0, 0, 256, 64);
          c.fillStyle = "#16202e";
          c.font = "700 26px Inter, system-ui, sans-serif";
          c.textBaseline = "middle";
          c.fillText(String(agent.name).split("·")[0].trim().slice(0, 14), 14, 33);
          st.plateTex.needsUpdate = true;
        }
        const alarm = person && person.mode === "error";
        st.alarm.material.emissiveIntensity = alarm ? 1.4 + Math.sin(t * 9) * 1.2 : 0;
        st.alarm.material.emissive.setHex(alarm ? 0xff1a3c : 0x000000);
        if (st.glow) st.glow.intensity = mode === "work" ? 0.55 : mode === "error" ? 0.5 + Math.sin(t * 9) * 0.3 : 0;
        if (st.glow) st.glow.color.setHex(mode === "error" ? 0xff2e4d : 0x29e0ff);
      });
    }

    function paintWall(t, force) {
      if (!S.meta) return;
      if (!force && t - (S.wallAt || 0) < 0.5) return;
      S.wallAt = t;
      const m = S.meta;
      LAB.screen.wall(x.wallCtx, x.wallTex.width, x.wallTex.height, {
        kicker: T("lab_wall_kicker"), title: m.title || "", goal: m.goal || "", percent: m.percent || 0, status: m.status,
        statusLabel: T(`agency_status_${/^[a-z_]{1,24}$/.test(m.status || "") ? m.status : "running"}`), failed: (m.counts && m.counts.failed) || 0,
      }, t);
      x.rig.disp.tex.needsUpdate = true;
    }

    function paintBoard(t, force) {
      if (!S.data || (!force && t - (S.boardAt || 0) < 1.5)) return;
      S.boardAt = t;
      const tasks = [];
      (S.data.agents || []).forEach((a) => (a.tasks || []).forEach((x) => tasks.push({ title: x.title || "", status: x.status })));
      LAB.screen.board(x.boardCanvas.getContext("2d"), x.boardCanvas.width, x.boardCanvas.height, tasks);
      x.rig.board.tex.needsUpdate = true;
    }

    function paintBadge(person, t) {
      const mode = person.isCeo ? "idle" : person.mode || "idle";
      let label;
      if (person.isCeo) label = T("lab_ceo_title");
      else if (mode === "consult") label = T("lab_state_consulting", { name: ((S.data.agents || []).find((a) => a.id === person.target) || {}).name || "" });
      else label = T(LAB.behavior.LABEL[mode] || "lab_state_idle");
      const key = `${mode}|${label}`;
      if (person.badge.key === key) return;
      person.badge.key = key;
      const tone = person.isCeo ? "#29e0ff" : LAB.screen.TONE[mode] || "#7aa2c8";
      const c = person.badge.canvas.getContext("2d");
      LAB.screen.badge(c, person.badge.canvas.width, person.badge.canvas.height, tone, label);
      person.badge.tex.needsUpdate = true;
    }

    function updateLinks(t) {
      let n = 0;
      S.people.forEach((p) => {
        if (p.mode !== "consult" || !p.target) return;
        const other = S.people.get(p.target);
        const ctrl = S.ctrls.get(p.id);
        if (!other || !ctrl || ctrl.state.phase !== "talk") return;
        let line = x.links[n];
        if (!line) {
          const geo = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(), new THREE.Vector3()]);
          line = new THREE.Line(geo, new THREE.LineBasicMaterial({ color: 0xc084fc, transparent: true, opacity: 0.8 }));
          line.frustumCulled = false;
          x.scene.add(line);
          x.links.push(line);
        }
        const a = p.root.position;
        const b = other.root.position;
        const pos = line.geometry.attributes.position;
        pos.setXYZ(0, a.x, 1.25, a.z);
        pos.setXYZ(1, b.x, 1.0 + Math.sin(t * 6) * 0.05, b.z);
        pos.needsUpdate = true;
        line.visible = true;
        n += 1;
      });
      for (let i = n; i < x.links.length; i += 1) x.links[i].visible = false;
    }

    function ambient(t) {
      x.holo.field.rotation.y = t * 0.45;
      x.holo.field.rotation.x = Math.sin(t * 0.3) * 0.15;
      x.holo.rings.forEach((r, i) => { r.rotation.z = t * (0.4 + i * 0.2); });
      x.holo.points.rotation.y = -t * 0.2;
      const busy = [...S.people.values()].some((p) => p.mode === "work");
      x.holo.ring.material.opacity = busy ? 0.6 + Math.sin(t * 3) * 0.3 : 0.5;
      x.plants.forEach((p, i) => { const l = p.getObjectByName("leaves"); if (l) l.rotation.z = Math.sin(t * 1.1 + i) * 0.03; });
      if (x.racks && Math.floor(t * 4) !== S.ledTick) {
        S.ledTick = Math.floor(t * 4);
        const color = new THREE.Color();
        const active = [...S.people.values()].filter((p) => p.mode === "work").length;
        x.racks.leds.forEach((idx, k) => {
          const on = ((idx * 7 + S.ledTick * (3 + (k % 3))) % 11) < 2 + active;
          x.racks.mesh.setColorAt(idx, color.set(on ? (idx % 5 === 0 ? 0xffb547 : 0x35f2a0) : 0x16261e));
        });
        x.racks.mesh.instanceColor.needsUpdate = true;
      }
      S.stations.forEach((st, i) => {
        if (st.steam) { st.steam.lookAt(x.camera.position); st.steam.position.y = 0.93 + ((t * 0.12 + i * 0.3) % 0.25); st.steam.material.opacity = 0.14 * (1 - ((t * 0.12 + i * 0.3) % 0.25) / 0.25); }
      });
    }

    return { paintScreens, paintWall, paintBoard, paintBadge, updateLinks, ambient };
  }

  LAB.painters = Object.freeze({ create });
})();
