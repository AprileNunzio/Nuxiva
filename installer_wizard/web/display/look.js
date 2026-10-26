(() => {
  const D = window.NuxivaDisplay, { $ } = D;
  const V = window.NUXIVA_ASSET_V ? `?v=${window.NUXIVA_ASSET_V}` : "";
  const loadScript = (src) => new Promise((ok, ko) => {
    const el = document.createElement("script");
    el.src = src + V; el.onload = ok; el.onerror = () => ko(new Error(`${src} non caricato`));
    document.head.appendChild(el);
  });
  window.Nuxiva3D = window.Nuxiva3D || {};
  window.Nuxiva3D.loadScript = D.loadScript = loadScript;
  let lib3d = null;
  const LIB_3D = [
    "/vendor/three.min.js", "/vendor/OrbitControls.js", "/vendor/GLTFLoader.js", "/vendor/RoomEnvironment.js",
    ...["common", "brain"].map((m) => `/static/display/scene/${m}.js`),
    ...[
      "rig/Landmarks", "rig/Shapes", "rig/MeshRig", "rig/NativeRig", "rig/Visemes",
      "anim/Library", "anim/Animator", "anim/Gaze", "camera/Framing",
      "body/Face", "body/Eyes",
      "accessories/Accessory", "accessories/Hat", "accessories/Glasses", "accessories/Headphones",
      "Director", "HoloAvatar",
    ].map((m) => `/static/display/scene/holo/${m}.js`),
    ...["Bones", "Retarget", "Motion", "Poses", "Gestures", "Umbrella", "Rain", "Life", "Actions", "CharacterAvatar"]
      .map((m) => `/static/display/scene/character/` + m + ".js"),
    "/static/display/scene/scene.js"
  ];
  const load3D = () => lib3d || (lib3d = LIB_3D.reduce((p, src) => p.then(() => loadScript(src)), Promise.resolve()));

  function startLight() {
    $("scene").style.display = "none"; $("core").style.display = "block";
    if (window.nuxivaPerf) window.nuxivaPerf.lite(D.look.reason ? D.look.reason[0] : "light");
    D.avatar = window.nuxivaAvatar = new NuxivaAvatar.ThoughtCore($("core"), { color: D.currentTint ? D.currentTint() : (D.FACE && D.FACE.color) || "#29e0ff" });
    D.avatar.setMode(D.mode);
  }

  async function startFull() {
    const { FACE, look } = D;
    try {
      await load3D();
      const scene = D.scene = new Nuxiva3D.NuxivaScene($("scene"), { onSelect: D.showNode, onHover: D.hoverNode,
        faceOptions: {
          color: FACE.color,
          style: FACE.style,
          model: FACE.model || "/static/shared/models/head.glb",
          character: (FACE.style || "character") === "character"
            ? (FACE.character || FACE.custom_model || (FACE.model && !FACE.model.endsWith("/models/head.glb") ? FACE.model : "/vendor/Michelle.glb"))
            : undefined,
          customModel: FACE.custom_model || (FACE.model && FACE.model.startsWith("/api/avatars/") ? FACE.model : null),
        },
        onFaceReady: () => look.auto && NuxivaAvatar.watchFps(() => scene.frames, look.info, (fps) => {
          console.warn(`3D a ${fps} fps: passo al nucleo leggero`);
          const swap = () => (D.busy || D.isSpeaking() ? setTimeout(swap, 3000) : location.reload());
          swap();
        }) });
      $("scene").style.display = "block";
      D.avatar = window.nuxivaAvatar = scene;
      window.nuxivaScene = scene;
      scene.setMode(D.mode);
      if (D.weather) scene.setWeather(D.weather);
      D.applyStage();
      D.refreshBrain(false);
    } catch (err) {
      console.warn("3D non disponibile, uso il nucleo leggero", err);
      look.mode = "light"; look.reason = ["why_no_3d", {}];
      startLight();
    }
  }

  async function ensureBrain() {
    if (D.scene) return D.scene;
    await load3D();
    D.scene = D.scene || new Nuxiva3D.NuxivaScene($("scene"), { face: false, onSelect: D.showNode, onHover: D.hoverNode });
    window.nuxivaScene = D.scene;
    $("scene").style.display = "block";
    await D.refreshBrain(false);
    return D.scene;
  }

  D.startLook = () => {
    const look = D.look = window.nuxivaLook = NuxivaAvatar.choose(D.FACE.avatar);
    console.info(`Aspetto: ${look.mode} (${look.reason[0]})`, look.info);
    if (look.mode === "full") startFull(); else startLight();
  };

  D.applyLookVisibility = (enabled = true) => {
    D.holoVisible = enabled;
    if (!enabled && D.avatar === D.scene) startLight();
    if (enabled && D.scene && D.look.mode === "full") {
      if (D.avatar && D.avatar !== D.scene && D.avatar.destroy) D.avatar.destroy();
      D.avatar = D.scene;
      D.scene.setMode(D.mode);
    }
    $("core").style.display = D.avatar && D.avatar !== D.scene && D.mode !== "brain" ? "block" : "none";
    $("scene").style.display = D.scene && (D.avatar === D.scene || D.mode === "brain") ? "block" : "none";
  };

  D.setMode = (m) => {
    const { avatar, scene } = D;
    D.mode = m;
    document.body.classList.remove("face", "focus", "brain");
    document.body.classList.add(m);
    if (avatar && avatar !== scene) avatar.setMode(m);
    if (scene) scene.setMode(m);
    else if (m === "brain" && D.look.mode === "light") ensureBrain().then((s) => s.setMode(D.mode)).catch((err) => { console.warn(err); D.setMode("face"); });
    if (m === "brain") D.refreshBrain(false);
    else { $("inspector").classList.remove("show"); D.selectedId = null; if (scene) scene.brain.select(null); }
    D.applyLookVisibility(D.holoVisible !== false);
  };

  const PRESENCE = { large: 1.15, normal: 1, small: 0.82, mini: 0.22 };
  D.setPresence = (name) => {
    const k = PRESENCE[name] || 1;
    D.presence = name;
    document.body.classList.toggle("presence-mini", name === "mini");
    for (const target of new Set([D.avatar, D.scene])) if (target && target.setPresence) target.setPresence(k);
  };

  D.applyStage = () => {
    const { avatar, scene, stageZone } = D;
    if (avatar && avatar.setStage) avatar.setStage(stageZone);
    if (scene && scene !== avatar && scene.setStage) scene.setStage(stageZone);
    const root = document.documentElement.style;
    if (stageZone) {
      root.setProperty("--av-x", `${stageZone.cx}px`);
      root.setProperty("--av-w", `${Math.max(260, stageZone.w)}px`);
      root.setProperty("--av-bottom", `${Math.max(96, window.innerHeight - (stageZone.y + stageZone.h) - 58)}px`);
    } else { ["--av-x", "--av-w", "--av-bottom"].forEach((k) => root.removeProperty(k)); }
  };
})();
