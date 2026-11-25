(() => {
  const T = window.PageText ? PageText.scope("web/display") : (k) => k;
  const POLL_MS = 1500;
  const STEP = Math.PI / 6;
  const ZOOM_STEP = 1.3;
  const COMMANDS = {
    zoom_in: { zoom: ZOOM_STEP }, zoom_out: { zoom: 1 / ZOOM_STEP }, rotate_left: { yaw: -STEP }, rotate_right: { yaw: STEP },
    rotate_up: { pitch: -STEP }, rotate_down: { pitch: STEP },
  };
  const st = { els: null, engine: null, creating: null, gestures: null, key: "", seq: -1, mode: "particles", visible: false, gesture: "idle" };

  function mount() {
    const root = document.createElement("section");
    root.className = "holo-layer";
    root.hidden = true;
    const canvas = document.createElement("canvas");
    canvas.className = "holo-canvas";
    const labels = document.createElement("div");
    labels.className = "holo-labels";
    const bar = document.createElement("div");
    bar.className = "holo-bar";
    bar.setAttribute("role", "status");
    bar.setAttribute("aria-live", "polite");
    const cells = {};
    for (const key of ["subject", "mode", "status", "gesture"]) {
      cells[key] = document.createElement("span");
      cells[key].className = `holo-chip holo-chip-${key}`;
      bar.appendChild(cells[key]);
    }
    const hint = document.createElement("p");
    hint.className = "holo-hint";
    hint.textContent = T("holo_hint");
    const privacy = document.createElement("p");
    privacy.className = "holo-privacy";
    privacy.textContent = T("holo_camera_local");
    const credit = document.createElement("a");
    credit.className = "holo-credit";
    credit.target = "_blank";
    credit.rel = "noopener noreferrer";
    credit.hidden = true;
    const progress = document.createElement("p");
    progress.className = "holo-progress";
    progress.setAttribute("role", "status");
    progress.setAttribute("aria-live", "polite");
    progress.hidden = true;
    root.append(canvas, labels, bar, hint, privacy, credit);
    document.body.append(root, progress);
    st.els = { root, canvas, labels, cells, hint, credit, progress };
  }

  async function engine() {
    if (st.engine) return st.engine;
    if (!st.creating) {
      st.creating = window.NuxivaHoloScene.create(st.els.canvas, st.els.labels).then((made) => {
        st.engine = made;
        return made;
      });
    }
    return st.creating;
  }

  function show(on) {
    st.visible = on;
    st.els.root.hidden = !on;
    document.body.classList.toggle("holo-solid", on);
    if (!on && st.engine) st.engine.stop();
  }

  function paint(snap) {
    const { cells } = st.els;
    cells.subject.textContent = snap.subject || "";
    cells.mode.textContent = T(`holo_mode_${snap.mode}`);
    const asset = snap.scene && snap.scene.asset;
    const parts = asset ? T("holo_asset_score", { s: asset.score }) : (snap.scene ? T("holo_parts", { n: snap.scene.parts.length, l: snap.scene.layers }) : "");
    cells.status.textContent = [T(`holo_status_${snap.status}`), parts].filter(Boolean).join(" · ");
    cells.gesture.textContent = T(`holo_gesture_${st.gesture}`);
    paintCredit(asset || (snap.scene && snap.scene.credit));
    paintProgress(snap);
  }

  function safePage(url) {
    try {
      const u = new URL(String(url || ""));
      return u.protocol === "https:" ? u.href : "";
    } catch {
      return "";
    }
  }

  function paintCredit(asset) {
    const { credit } = st.els;
    credit.hidden = !asset;
    if (!asset) return;
    const license = String(asset.license || "");
    const shown = license.startsWith("forge_") ? T(`holo_license_${license}`) : license;
    credit.textContent = T("holo_credit", { name: asset.name || "", author: asset.author || "", license: shown });
    const page = safePage(asset.page);
    if (page) credit.href = page;
    else credit.removeAttribute("href");
  }

  function paintProgress(snap) {
    const { progress } = st.els;
    const key = snap.active && snap.progress ? snap.progress.key : "";
    const busy = key && (snap.status === "building" || snap.status === "refining" || key === "none" || key === "rejected");
    progress.hidden = !busy;
    if (!busy) return;
    const params = { ...(snap.progress.params || {}) };
    if (params.stage) params.stage = T(`holo_stage_${params.stage}`);
    progress.textContent = T(`holo_progress_${key}`, params);
  }

  function apply(name) {
    const target = st.visible ? st.engine : window.NuxivaParticles;
    if (!target || !target.adjust) return;
    if (COMMANDS[name]) target.adjust(COMMANDS[name]);
    else if (name === "reset" && target.reset) target.reset();
    else if (st.visible && name === "explode") st.engine.setExplode(0.7);
    else if (st.visible && name === "collapse") st.engine.setExplode(0);
  }

  async function sync(snap) {
    st.mode = snap.active ? snap.mode : "particles";
    if (!snap.active) {
      show(false);
      st.key = "";
      st.seq = snap.command ? snap.command.seq : st.seq;
      st.els.progress.hidden = true;
      return;
    }
    const scene = snap.scene;
    const solid = Boolean(scene && (scene.asset || (st.mode !== "particles" && Array.isArray(scene.parts) && scene.parts.length)));
    if (solid) {
      const made = await engine();
      const key = `${snap.id}:${snap.source}`;
      if (key !== st.key) {
        st.key = key;
        made.load(snap.scene).catch((err) => console.info("Modello 3D non caricato:", err.message));
      }
      made.setAnatomy(st.mode === "anatomy");
      made.setAnimate(snap.animate !== false);
      show(true);
      made.play();
    } else {
      show(false);
    }
    const seq = snap.command ? snap.command.seq : 0;
    if (st.seq >= 0 && seq !== st.seq && snap.command.name) apply(snap.command.name);
    st.seq = seq;
    paint(snap);
  }

  async function poll() {
    if (document.hidden) return;
    try {
      const r = await fetch("/api/hands/display/holo", { cache: "no-store", credentials: "same-origin" });
      if (!r.ok) return;
      await sync(await r.json());
    } catch (err) {
      console.info("Vista olografica non aggiornata:", err.message);
    }
  }

  function tick(now) {
    requestAnimationFrame(tick);
    const particles = window.NuxivaParticles;
    const target = st.visible ? st.engine : (particles && particles.showing ? particles : null);
    document.body.classList.toggle("holo-gestures", Boolean(target));
    if (!target || !target.adjust) {
      st.gestures.reset();
      return;
    }
    const out = st.gestures.feed(window.__nuxivaLastHands || [], now);
    if (out.gesture !== st.gesture) {
      st.gesture = out.gesture;
      if (st.visible) st.els.cells.gesture.textContent = T(`holo_gesture_${st.gesture}`);
    }
    if (out.yaw || out.pitch || out.zoom !== 1 || out.px || out.py || out.explode !== null) target.adjust(out);
    if (out.toggle && st.visible) st.engine.toggleExplode();
  }

  function init() {
    mount();
    st.gestures = window.NuxivaHoloGestures.create();
    requestAnimationFrame(tick);
    poll();
    setInterval(poll, POLL_MS);
    document.addEventListener("visibilitychange", () => { if (!document.hidden && st.visible && st.engine) st.engine.play(); });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
