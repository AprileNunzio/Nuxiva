(() => {
  const BONES = [
    [0, 1], [1, 2], [2, 3], [3, 4],
    [0, 5], [5, 6], [6, 7], [7, 8],
    [5, 9], [9, 10], [10, 11], [11, 12],
    [9, 13], [13, 14], [14, 15], [15, 16],
    [13, 17], [0, 17], [17, 18], [18, 19], [19, 20],
  ];
  const FOCUS_ORDER = ["sphere", "torus", "cube", "helix", "procedural"];
  const FIDELITY_ORDER = ["particles", "mesh_3d", "photoreal_pbr"];
  const DEBOUNCE_FRAMES = 3;

  const st = {
    open: false,
    cameraActive: false,
    autoCloseMs: 4000,
    lastPresenceAt: 0,
    shape: "sphere",
    subject: "",
    fidelity: "particles",
    gesture: "idle",
    candidate: "idle",
    streak: 0,
    focusLatched: false,
    baseSpan: 0,
    scale: 1.0,
    handsCount: 0,
    dict: {},
    holo: null,
    els: null,
    lastIntentSent: "",
    lastSentAt: 0,
  };

  async function loadI18n() {
    const lang = (document.documentElement.lang || "it").slice(0, 2).toLowerCase();
    const code = ["it", "en", "fr", "es"].includes(lang) ? lang : "it";
    try {
      const res = await fetch(`/static/display/spatial_hud/language/${code}.json`, { cache: "no-store" });
      if (res.ok) {
        const data = await res.json();
        st.dict = data.dictionary || {};
      }
    } catch (err) {
      console.warn("Spatial HUD i18n load warning", err);
    }
  }

  function t(key) {
    return st.dict[key] || key;
  }

  function dist(a, b) {
    return Math.hypot((a.x || 0) - (b.x || 0), (a.y || 0) - (b.y || 0));
  }

  function classifyHand(lm) {
    if (!lm || lm.length < 21) return "idle";
    const wrist = lm[0];
    const palm = Math.max(0.05, dist(wrist, lm[9]));
    const tips = [8, 12, 16, 20];
    const pips = [6, 10, 14, 18];
    let extended = 0;
    for (let i = 0; i < 4; i++) {
      if (dist(wrist, lm[tips[i]]) > dist(wrist, lm[pips[i]]) * 1.12) extended++;
    }
    const pinchRatio = dist(lm[4], lm[8]) / palm;
    if (extended >= 4 && pinchRatio > 0.45) return "open_palm_disperse";
    if (extended <= 1 || pinchRatio < 0.34) return "single_hand_focus_morph";
    return "wrist_rotation_tilt";
  }

  function drawWireframe(ctx, w, h, hands) {
    ctx.clearRect(0, 0, w, h);
    if (!st.cameraActive || !hands || !hands.length) return;
    ctx.strokeStyle = "rgba(34, 211, 238, 0.82)";
    ctx.lineWidth = 2;
    for (const lm of hands) {
      if (!lm || lm.length < 21) continue;
      ctx.beginPath();
      for (const [a, b] of BONES) {
        ctx.moveTo((1 - lm[a].x) * w, lm[a].y * h);
        ctx.lineTo((1 - lm[b].x) * w, lm[b].y * h);
      }
      ctx.stroke();
      ctx.fillStyle = "#5eead4";
      for (let i = 0; i < 21; i++) {
        ctx.beginPath();
        ctx.arc((1 - lm[i].x) * w, lm[i].y * h, i % 4 === 0 ? 4 : 2.6, 0, Math.PI * 2);
        ctx.fill();
      }
    }
  }

  function sendSemanticIntent(gesture, shape, handsCount) {
    const now = performance.now();
    const key = `${gesture}:${shape}:${st.fidelity}:${handsCount}`;
    if (key === st.lastIntentSent && now - st.lastSentAt < 1200) return;
    st.lastIntentSent = key;
    st.lastSentAt = now;
    fetch("/api/hands/display/spatial_hud", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        camera_active: st.cameraActive,
        person_present: handsCount > 0,
        shape,
        subject: st.subject,
        fidelity: st.fidelity,
        active_gesture: gesture,
        hands_count: handsCount,
        confidence: handsCount > 0 ? 0.94 : 0.0,
        gesture_intent: { type: "gesture", gesture, action: shape },
      }),
    }).catch(() => {});
  }

  function processHands(hands) {
    const now = performance.now();
    const list = Array.isArray(hands) ? hands : [];
    st.handsCount = list.length;
    const audience = document.body.dataset.audience || "";
    const personPresent = list.length > 0 || (audience !== "" && audience !== "empty");

    if (!st.cameraActive) return;
    if (personPresent) {
      st.lastPresenceAt = now;
    } else if (now - st.lastPresenceAt >= st.autoCloseMs) {
      setCameraActive(false, true);
      return;
    }

    let detected = "idle";
    if (list.length >= 2) {
      detected = "two_hand_pinch_stretch";
    } else if (list.length === 1) {
      detected = classifyHand(list[0]);
    }

    if (detected === st.candidate) st.streak++;
    else { st.candidate = detected; st.streak = 1; }

    if (st.streak >= DEBOUNCE_FRAMES) {
      st.gesture = detected;
      if (detected === "open_palm_disperse") {
        st.shape = "dispersed";
        st.fidelity = "particles";
        if (st.holo) st.holo.setFidelity("particles");
        st.focusLatched = false;
        st.baseSpan = 0;
      } else if (detected === "single_hand_focus_morph") {
        if (!st.focusLatched) {
          const idx = FOCUS_ORDER.indexOf(st.shape);
          st.shape = FOCUS_ORDER[(idx + 1) % FOCUS_ORDER.length];
          st.focusLatched = true;
        }
        st.baseSpan = 0;
      } else if (detected !== "two_hand_pinch_stretch") {
        st.focusLatched = false;
        st.baseSpan = 0;
      }
      if (st.holo) st.holo.setShape(st.shape);
      sendSemanticIntent(st.gesture, st.shape, list.length);
    }

    if (st.holo && list.length >= 2) {
      const span = Math.max(0.06, dist(list[0][9], list[1][9]));
      if (!st.baseSpan) st.baseSpan = span;
      const ratio = Math.max(0.45, Math.min(2.6, span / st.baseSpan));
      st.scale = st.scale * 0.72 + ratio * 0.28;
      st.holo.setTransform({ scale: st.scale });
    } else if (st.holo && list.length === 1) {
      const lm = list[0];
      const yaw = (lm[5].x - lm[17].x) * 3.2;
      const pitch = (lm[9].y - lm[0].y) * 3.2;
      const tx = (0.5 - lm[0].x) * 0.9;
      const ty = (lm[0].y - 0.5) * 0.9;
      st.holo.setTransform({ yaw, pitch, tx, ty });
    }
    updateHudBar();
  }

  function setCameraActive(enable, autoClosed = false) {
    st.cameraActive = Boolean(enable);
    st.lastPresenceAt = performance.now();
    if (!st.els) return;
    if (st.cameraActive) {
      st.els.video.src = `/api/vision/hands.mjpg?r=${Date.now()}`;
      st.els.video.classList.remove("off");
      st.els.dot.classList.add("live");
      st.els.camBtn.textContent = t("shud_cam_disable");
    } else {
      st.els.video.src = "";
      st.els.video.classList.add("off");
      st.els.dot.classList.remove("live");
      st.els.camBtn.textContent = t("shud_cam_enable");
      st.gesture = "idle";
      st.handsCount = 0;
    }
    updateHudBar(autoClosed);
    sendSemanticIntent(st.gesture, st.shape, st.handsCount);
  }

  function updateHudBar(autoClosed = false) {
    if (!st.els) return;
    const shapeLabel = st.shape === "procedural" && st.subject
      ? `${st.subject.toUpperCase()}`
      : t(`shud_shape_${st.shape}`);
    st.els.valShape.textContent = shapeLabel;
    st.els.valGesture.textContent = t(`shud_gesture_${st.gesture}`);
    if (autoClosed) st.els.valPrivacy.textContent = t("shud_privacy_autoclose");
    else st.els.valPrivacy.textContent = st.cameraActive ? t("shud_privacy_live") : t("shud_privacy_off");
    const fidLabel = t(`shud_fidelity_${st.fidelity}`);
    st.els.valEngine.textContent = `${fidLabel} · ${st.handsCount}H`;
    if (st.els.pbrBtn) {
      st.els.pbrBtn.textContent = fidLabel;
    }
  }

  async function requestGenerateSubject(subjectText, fidelityTier) {
    try {
      const res = await fetch("/api/hands/display/spatial_hud", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          camera_active: st.cameraActive,
          shape: "procedural",
          subject: subjectText,
          fidelity: fidelityTier,
        }),
      });
      if (res.ok) await pollMcpState();
    } catch (err) {}
  }

  function mountDom() {
    const root = document.createElement("section");
    root.className = "shud-layer";
    root.id = "spatial-hud-layer";
    root.hidden = true;
    root.innerHTML = `
      <img class="shud-video off" id="shud-video" alt="">
      <canvas class="shud-holo-canvas" id="shud-holo"></canvas>
      <canvas class="shud-wire-canvas" id="shud-wire"></canvas>
      <div class="shud-top">
        <div class="shud-brand"><span class="shud-dot" id="shud-dot"></span><b id="shud-title"></b></div>
        <div class="shud-actions">
          <button type="button" class="shud-btn" id="shud-cam-btn"></button>
          <button type="button" class="shud-btn" id="shud-morph-btn">3D</button>
          <button type="button" class="shud-btn" id="shud-pbr-btn"></button>
          <button type="button" class="shud-btn" id="shud-close-btn"></button>
        </div>
      </div>
      <div class="shud-bar" role="status" aria-live="polite">
        <div class="shud-cell"><span class="shud-label" id="shud-l-shape"></span><span class="shud-val" id="shud-v-shape"></span></div>
        <div class="shud-cell"><span class="shud-label" id="shud-l-gesture"></span><span class="shud-val" id="shud-v-gesture"></span></div>
        <div class="shud-cell"><span class="shud-label" id="shud-l-privacy"></span><span class="shud-val" id="shud-v-privacy"></span></div>
        <div class="shud-cell"><span class="shud-label" id="shud-l-engine"></span><span class="shud-val" id="shud-v-engine"></span></div>
      </div>
    `;
    document.body.appendChild(root);
    st.els = {
      root,
      video: root.querySelector("#shud-video"),
      holoCanvas: root.querySelector("#shud-holo"),
      wireCanvas: root.querySelector("#shud-wire"),
      dot: root.querySelector("#shud-dot"),
      title: root.querySelector("#shud-title"),
      camBtn: root.querySelector("#shud-cam-btn"),
      morphBtn: root.querySelector("#shud-morph-btn"),
      pbrBtn: root.querySelector("#shud-pbr-btn"),
      closeBtn: root.querySelector("#shud-close-btn"),
      valShape: root.querySelector("#shud-v-shape"),
      valGesture: root.querySelector("#shud-v-gesture"),
      valPrivacy: root.querySelector("#shud-v-privacy"),
      valEngine: root.querySelector("#shud-v-engine"),
    };
    root.querySelector("#shud-l-shape").textContent = t("shud_lbl_shape");
    root.querySelector("#shud-l-gesture").textContent = t("shud_lbl_gesture");
    root.querySelector("#shud-l-privacy").textContent = t("shud_lbl_privacy");
    root.querySelector("#shud-l-engine").textContent = t("shud_lbl_engine");
    st.els.title.textContent = t("shud_title");
    st.els.camBtn.textContent = t("shud_cam_enable");
    st.els.closeBtn.textContent = t("shud_close");

    st.els.camBtn.addEventListener("click", () => setCameraActive(!st.cameraActive));
    st.els.morphBtn.addEventListener("click", () => {
      const idx = FOCUS_ORDER.indexOf(st.shape);
      st.shape = FOCUS_ORDER[(idx + 1) % FOCUS_ORDER.length];
      if (st.holo) st.holo.setShape(st.shape);
      updateHudBar();
    });
    st.els.pbrBtn.addEventListener("click", () => {
      const idx = FIDELITY_ORDER.indexOf(st.fidelity);
      st.fidelity = FIDELITY_ORDER[(idx + 1) % FIDELITY_ORDER.length];
      if (st.holo) st.holo.setFidelity(st.fidelity);
      updateHudBar();
      sendSemanticIntent(st.gesture, st.shape, st.handsCount);
    });
    st.els.closeBtn.addEventListener("click", () => toggleHud(false));
    st.holo = window.NuxivaSpatialHologram.createEngine(st.els.holoCanvas);
    updateHudBar();
  }

  function toggleHud(show) {
    st.open = typeof show === "boolean" ? show : !st.open;
    if (!st.els) return;
    st.els.root.hidden = !st.open;
    if (!st.open && st.cameraActive) setCameraActive(false);
  }

  function renderLoop() {
    requestAnimationFrame(renderLoop);
    if (!st.open || !st.els) return;
    if (st.holo) st.holo.stepAndRender();
    const wire = st.els.wireCanvas;
    const w = wire.clientWidth || window.innerWidth;
    const h = wire.clientHeight || window.innerHeight;
    if (wire.width !== w || wire.height !== h) { wire.width = w; wire.height = h; }
    const ctx = wire.getContext("2d");
    if (ctx) drawWireframe(ctx, w, h, window.__nuxivaLastHands || []);
    processHands(window.__nuxivaLastHands || []);
  }

  async function pollMcpState() {
    try {
      const res = await fetch("/api/hands/display/spatial_hud", { cache: "no-store" });
      if (!res.ok) return;
      const remote = await res.json();
      if (Array.isArray(remote.csg_nodes) && remote.csg_nodes.length && st.holo) {
        st.holo.setProceduralNodes(remote.csg_nodes);
      }
      if (remote.subject) st.subject = remote.subject;
      if (remote.shape && remote.shape !== st.shape) {
        st.shape = remote.shape;
        if (st.holo) st.holo.setShape(st.shape);
      }
      if (remote.fidelity && remote.fidelity !== st.fidelity) {
        st.fidelity = remote.fidelity;
        if (st.holo) st.holo.setFidelity(st.fidelity);
      }
      if (typeof remote.auto_close_timeout_s === "number") {
        st.autoCloseMs = Math.max(1000, remote.auto_close_timeout_s * 1000);
      }
      if (remote.enabled && !st.open) toggleHud(true);
      updateHudBar();
    } catch (err) {}
  }

  async function init() {
    await loadI18n();
    mountDom();
    const dock = document.getElementById("dock-tools");
    if (dock) {
      const btn = document.createElement("button");
      btn.className = "ibtn";
      btn.id = "btn-spatial-hud";
      btn.type = "button";
      btn.title = t("shud_title");
      btn.setAttribute("aria-label", t("shud_title"));
      btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><polygon points="12 2 21 7 21 17 12 22 3 17 3 7"/><line x1="12" y1="22" x2="12" y2="12"/><polyline points="21 7 12 12 3 7"/></svg>';
      btn.addEventListener("click", () => toggleHud());
      dock.appendChild(btn);
    }
    requestAnimationFrame(renderLoop);
    setInterval(pollMcpState, 3000);
  }

  window.NuxivaSpatialHud = {
    toggle: toggleHud,
    setCameraActive,
    generateObject: requestGenerateSubject,
    setFidelity: (f) => { st.fidelity = f; if (st.holo) st.holo.setFidelity(f); updateHudBar(); },
    feedHands: (h) => { window.__nuxivaLastHands = h; },
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
