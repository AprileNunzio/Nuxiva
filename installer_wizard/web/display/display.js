(() => {
  const D = window.NuxivaDisplay, { $, fmt } = D;
  let clientId = "";
  try {
    clientId = sessionStorage.getItem("nuxiva_client_id") || "";
    if (!clientId) {
      clientId = D.local ? "kiosk" : "client_" + Math.random().toString(36).slice(2, 10);
      sessionStorage.setItem("nuxiva_client_id", clientId);
    }
  } catch (_) {
    clientId = D.local ? "kiosk" : "client_fallback";
  }
  D.clientId = clientId;
  D.lastDialogueId = "";
  let homeSent = 0;

  function goHome() {
    D.setPresence("normal");
    D.setMode("face");
    if (Date.now() - homeSent < 5000) return;
    homeSent = Date.now();
    fetch("/api/desk/idle", { method: "POST" }).catch(() => {});
  }

  let privacy = { away: false, voice_s: 0 };

  function closePersonal() {
    D.personalUi = null;
    D.setPresence("normal");
    D.setMode("face");
    rest();
  }

  function guardPersonal() {
    if (!D.personalUi) return;
    if (D.mode !== "focus") { D.personalUi = null; return; }
    const limit = privacy.voice_s * 1000;
    if (privacy.away || (limit > 0 && Date.now() - D.personalUi.at >= limit)) closePersonal();
  }

  function tick() {
    const d = new Date();
    $("clock").textContent = d.toLocaleTimeString(document.documentElement.lang || "it", { hour: "2-digit", minute: "2-digit" });
    $("date").textContent = fmt.date(d);
    const h = d.getHours();
    const g = h < 6 ? "greet_night" : h < 13 ? "greet_morning" : h < 18 ? "greet_afternoon" : "greet_evening";
    if (D.presentNames.length) { D.greetNames = D.presentNames; D.greetSeen = Date.now(); }
    const who = D.greetNames && Date.now() - (D.greetSeen || 0) < 20000 ? new Intl.ListFormat(Nuxiva.fmt.locale(), { type: "conjunction" }).format(D.greetNames) : "";
    if ($("greet")) PageText.bind($("greet"), who ? `${g}_named` : g, who ? { who } : {});
    const quiet = !D.busy && !D.isSpeaking() && Date.now() - D.lastInteraction;
    if (D.mode !== "face" && quiet > (D.mode === "brain" ? 90000 : 60000)) goHome();
    else if (D.mode === "face" && quiet > 60000 && (NuxivaDesk.all || []).some((w) => w.intent)) goHome();
    guardPersonal();
    if (quiet > 60000 && !rested) rest();
    else if (quiet && quiet < 60000) rested = false;
    updateClockMusic(quiet > 60000);
  }

  let rested = false;
  let currentNowPlaying = null;

  function updateClockMusic(isResting) {
    const box = $("clock-music");
    if (!box) return;
    const np = currentNowPlaying;
    const hasSong = np && (np.title || np.artist);
    if (isResting && hasSong) {
      $("clock-music-title").textContent = np.title || "";
      $("clock-music-artist").textContent = np.artist || "";
      const cover = $("clock-music-cover");
      if (np.cover) {
        cover.innerHTML = `<img src="${fmt.esc(np.cover)}" alt="">`;
      } else {
        cover.textContent = "🎵";
      }
      box.classList.add("show");
    } else {
      box.classList.remove("show");
    }
  }

  function rest() {
    rested = true;
    $("you").textContent = "";
    $("focus-say").textContent = "";
    $("stage-body").innerHTML = "";
    PageText.plain($("stage-title"), "");
    PageText.plain($("stage-sub"), "");
    if (!$("greet")) $("say").innerHTML = '<span class="greet" id="greet"></span>';
  }

  let presenceSig = "";
  let familyNearState = false;

  D.isFamilyNear = () => familyNearState;

  function renderPresence(pr) {
    const people = (pr && pr.status === "ok" && pr.people) || [];
    const names = [...new Set(people.filter((p) => p.known).map((p) => p.name))];
    const near = new Set(people.filter((p) => p.known && p.near).map((p) => p.name));
    const strangers = people.filter((p) => !p.known).length;
    familyNearState = people.some((p) => p.known && p.near && ["owner", "family"].includes(p.role));
    document.body.classList.toggle("guest-lock", !familyNearState);
    D.presentNames = names;
    D.Ear.presence(people.length === 1 && people[0].known ? people[0].slug : null);
    const look = people.find((p) => p.known && p.near) || people.find((p) => p.facing) || people[0];
    if (look && look.gaze && D.avatar && D.avatar.setGaze) D.avatar.setGaze(look.gaze.x, look.gaze.y);
    if (D.avatar && D.avatar.express) {
      const prev = D._nearSet || new Set();
      if ([...near].some((n) => !prev.has(n))) D.avatar.express("smile", 2.6);
      D._nearSet = new Set(near);
    }
    const sig = JSON.stringify([names, [...near], strangers]);
    if (sig === presenceSig) return;
    presenceSig = sig;
    const box = $("presence");
    if (!names.length && !strangers) { box.classList.remove("show"); return; }
    box.innerHTML = names.map((n) => `<span class="who ${near.has(n) ? "near" : ""}"><i></i>${fmt.esc(n)}</span>`).join("")
      + (strangers ? `<span class="who unknown"><i></i>${strangers === 1 ? PageText.html("guest_one") : PageText.html("guest_many", { n: strangers })}</span>` : "");
    box.classList.add("show");
  }

  function handleGreeting(g) {
    if (!g || !g.id) return;
    if (D.lastGreeting === null) { D.lastGreeting = g.id; return; }
    if (g.id === D.lastGreeting) return;
    D.lastGreeting = g.id;
    D.lastInteraction = Date.now();
    D.Mood.joy();
    if (g.names && g.names.length) {
      $("welcome-name").textContent = [...new Set(g.names)].join(" · ");
      PageText.bind($("welcome-sub"), "identity_recognized");
      $("welcome").classList.add("show");
      setTimeout(() => $("welcome").classList.remove("show"), 5000);
    }
    if (D.mode !== "brain") D.setMode("face");
    D.typeInto($("say"), g.text);
    if (!D.busy) D.speak(g.text);
  }

  function sendPosition() {
    if (!navigator.geolocation || !D.local) return;
    navigator.geolocation.getCurrentPosition(
      (p) => fetch("/api/location/browser", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lat: p.coords.latitude, lon: p.coords.longitude, accuracy: p.coords.accuracy }) }).catch(() => {}),
      (err) => console.info("Posizione del display non disponibile:", err.message),
      { enableHighAccuracy: true, timeout: 30000, maximumAge: 10 * 60000 });
  }

  function onState(s) {
    D.state = s;
    if (s.display_settings) applyDisplaySettings(s.display_settings);
    if (s.assistant_name) {
      const clean = s.assistant_name.replace(/^(?:hey|hei|ehi|hi|ok|okay)\s+/i, "").trim() || s.assistant_name;
      if ($("brand-name")) $("brand-name").textContent = clean.toUpperCase();
      if (window.NUXIVA_ASSISTANT && window.NUXIVA_ASSISTANT.name !== clean) {
        window.NUXIVA_ASSISTANT.name = clean;
        document.querySelectorAll("[data-i18n-params]").forEach((el) => {
          try {
            const params = JSON.parse(el.getAttribute("data-i18n-params"));
            if ("assistant" in params) el.setAttribute("data-i18n-params", JSON.stringify({ ...params, assistant: clean }));
          } catch (err) {
            console.warn("Parametri di traduzione non validi", err);
          }
        });
      }
      if (D.Ear && D.Ear.setAssistantName) D.Ear.setAssistantName(clean);
    }
    privacy = s.privacy || privacy;
    renderPresence(s.presence);
    if (D.followLanguage) D.followLanguage(s.presence);
    guardPersonal();
    handleGreeting(s.greeting);
    if (D.Enroll) D.Enroll.fromState(s.voice_training, s);
    D.onAudioRev(s.audio_rev);
    D.Ear.resetFrom(s.mic_reset);
    NuxivaDesk.setScreens(s.screens);
    NuxivaDesk.render(s.desk || []);
    if (D.Sounds) { D.Sounds.update(s.sounds); D.Sounds.desk(s.desk); }
    if (!["READY", "DEGRADED"].includes(s.phase)) { location.reload(); return; }
    if (s.asset_version && window.NUXIVA_ASSET_V && s.asset_version !== window.NUXIVA_ASSET_V) {
      D.staleSince = D.staleSince || Date.now();
      if ((!D.busy && !D.isSpeaking()) || Date.now() - D.staleSince > 120000) { location.reload(); return; }
    }
    const node = new URLSearchParams(location.search).get("node");
    const face = (node && s.node_faces && s.node_faces[node]) || s.face;
    if (face && window.NUXIVA_FACE && JSON.stringify(face) !== JSON.stringify(window.NUXIVA_FACE)) { location.reload(); return; }
    D.userName = s.user_name || "";
    $("banner").textContent = s.message;
    $("banner").classList.toggle("show", s.phase === "DEGRADED");
    if (D.avatar) D.avatar.setTint(s.phase === "DEGRADED" ? "#ffb547" : D.busy ? "#b36bff" : (D.currentTint ? D.currentTint() : (D.tint || "#29e0ff")));
    $("chips").innerHTML = Object.values(s.components || {}).filter((c) => c.status && c.status !== "ok")
      .map((c) => `<span><i class="dot ${c.status}"></i>${fmt.esc(c.label)}</span>`).join("");

    currentNowPlaying = s.now_playing || null;
    updateClockMusic(rested);
    if (s.holo_action && D.avatar) holoAction(s.holo_action);
    if (s.live_dialogue && s.live_dialogue.id && s.live_dialogue.id !== D.lastDialogueId) {
      D.lastDialogueId = s.live_dialogue.id;
      const mode = (s.display_settings && s.display_settings.session_mode) || "shared";
      const forMe = mode === "shared" || s.live_dialogue.client_id === D.clientId;
      const fromMe = s.live_dialogue.client_id === D.clientId;
      if (forMe && !fromMe) {
        D.lastInteraction = Date.now();
        if (s.live_dialogue.user_text && $("you")) {
          $("you").textContent = `« ${s.live_dialogue.user_text} »`;
        }
        if (s.live_dialogue.reply && $("say")) {
          if (D.mode !== "brain") D.setMode("face");
          D.typeInto($("say"), s.live_dialogue.reply);
          if (D.avatar && D.avatar.express) D.avatar.express("talk", 2.4);
        }
      }
    }
  }

  function holoAction(a) {
    const av = D.avatar, call = (fn, ...args) => typeof av[fn] === "function" && av[fn](...args);
    if (a.express) call("express", a.express, a.seconds || 3);
    if (a.play) call("play", a.play);
    if (a.stop) call("stop", a.stop);
    if (a.shot) call("shot", a.shot, a.seconds || 12);
    if (a.dance !== undefined) call("dance", a.dance);
    if (a.sing !== undefined) call("sing", a.sing);
    if (a.accessory) call("toggleAccessory", a.accessory.name, a.accessory.state);
    if (a.tint) {
      if (a.tint === "default" || a.tint === "reset") {
        D.tint = null;
        call("setTint", D.currentTint ? D.currentTint() : "#29e0ff");
      } else if (/^#[0-9a-f]{6}$/i.test(a.tint)) {
        D.tint = a.tint;
        call("setTint", a.tint);
      }
    }
  }

  D.startLook();
  D.startAmbient();
  if (D.startSounds) D.startSounds();
  setInterval(tick, 1000); tick();
  ["pointerdown", "keydown", "wheel"].forEach((ev) => addEventListener(ev, () => (D.lastInteraction = Date.now()), { passive: true }));
  D.Ear.start();
  D.startHands();
  D.startAudioPanel();
  D.startVoiceToggle();
  D.startChat();
  setTimeout(sendPosition, 5000);
  setInterval(sendPosition, 30 * 60000);
  NuxivaDesk.mount($("desk"), {
    speak: (text) => { if (!D.busy) { D.typeInto($("say"), text); D.speak(text); } },
    onStage: (zone) => { if (D.cam && D.cam.on) { D.cam.prevZone = zone; return; } D.stageZone = zone; D.applyStage(); },
    screen: 0, x: +(new URLSearchParams(location.search).get("x") || 0),
    clientId: D.clientId,
    sessionMode: (D.state && D.state.display_settings && D.state.display_settings.session_mode) || "shared",
  });
  let linkLostAt = 0;
  const onLink = (ok) => {
    $("link").classList.toggle("show", !ok);
    if (!ok) {
      linkLostAt = linkLostAt || Date.now();
      return;
    }
    if (linkLostAt && Date.now() - linkLostAt > 8000) {
      location.reload();
      return;
    }
    linkLostAt = 0;
  };
  Nuxiva.connectState("/api/stream", (s) => (window.nuxivaPerf ? window.nuxivaPerf.measure("stato", () => onState(s)) : onState(s)), onLink);
  function applyDisplaySettings(cfg) {
    if (!cfg) return;
    const toggle = (el, show) => {
      if (!el) return;
      el.style.display = show === false ? "none" : "";
    };
    const brand = document.querySelector(".brand") || $("brand-name");
    toggle(brand, cfg.show_assistant_name !== false);
    toggle($("clock"), cfg.show_clock !== false);
    toggle($("date"), cfg.show_date !== false);
    toggle($("mind"), cfg.show_thinking !== false);
    toggle(document.querySelector(".dock"), cfg.show_dock !== false);
    toggle($("btn-mic"), cfg.show_mic !== false);
    toggle($("ear"), cfg.show_mic !== false);
    toggle($("chips"), cfg.show_telemetry_chips !== false);
    toggle($("presence"), cfg.show_presence !== false);
    if (D.applyLookVisibility) D.applyLookVisibility(cfg.show_holo_avatar !== false);
    toggle($("desk"), cfg.show_desk_widgets !== false);
  }
  try {
    const cached = localStorage.getItem("nuxiva_display_settings");
    if (cached) applyDisplaySettings(JSON.parse(cached));
  } catch (_) {}
  try {
    const bc = new BroadcastChannel("nuxiva_display_settings");
    bc.onmessage = (ev) => {
      if (ev && ev.data && ev.data.settings) applyDisplaySettings(ev.data.settings);
    };
  } catch (_) {}
  window.addEventListener("storage", (ev) => {
    if (ev.key === "nuxiva_display_settings" && ev.newValue) {
      try { applyDisplaySettings(JSON.parse(ev.newValue)); } catch (_) {}
    }
  });
  fetch("/api/system/display-settings")
    .then((r) => (r.ok ? r.json() : null))
    .then((d) => {
      if (d && d.settings) {
        applyDisplaySettings(d.settings);
        try { localStorage.setItem("nuxiva_display_settings", JSON.stringify(d.settings)); } catch (_) {}
      }
    })
    .catch(() => {});
  D.startBrain();
  D.startMindStream();
  if (D.startFlow) D.startFlow();
  D.startCamera();
})();


const projectWidget = {
  async tick() {
    const res = await fetch("/api/projects/status", { credentials: "same-origin" });
    if (res.status === 404 || res.status === 401 || res.status === 403) return window.nuxivaGovernor ? window.nuxivaGovernor.STOP : undefined;
    if (!res.ok) throw new Error(`stato progetti ${res.status}`);
    const data = await res.json();
    const widget = document.getElementById("project-widget");
    if (!widget) return undefined;
    if (!(data.projects && data.projects.length)) { widget.style.display = "none"; return undefined; }
    const p = data.projects[0];
    widget.style.display = "block";
    const pct = document.getElementById("proj-pct"), bar = document.getElementById("proj-bar"), name = document.getElementById("proj-name");
    if (pct) pct.textContent = p.progress + "%";
    if (bar) bar.style.width = p.progress + "%";
    if (name) {
      const id = String(p.name || "").replace(/^tsk_/, "");
      if (/^tsk_/.test(String(p.name || ""))) PageText.bind(name, "project_n", { id });
      else { name.removeAttribute("data-i18n"); name.textContent = p.name || ""; }
    }
    return undefined;
  },
};
if (window.nuxivaGovernor) window.nuxivaGovernor.poll("progetti", () => projectWidget.tick(), 3000, 60000);
