(() => {
  const D = window.NuxivaDisplay, { $, fmt } = D;
  const LOOK_KEYS = { full: "look_full", light: "look_light", auto: "look_auto_short" };
  let volTimer = null, lastInput = null, audioRev = null;

  const options = (list, cur) => list.length
    ? list.map((d) => `<option value="${fmt.esc(d.name)}" ${d.name === cur ? "selected" : ""}>${fmt.esc(d.label)}</option>`).join("")
    : '<option value="" data-i18n="no_devices"></option>';

  async function loadAudio() {
    try {
      const a = await fetch("/api/audio").then((r) => r.json());
      if (!a.available) { PageText.bind($("vol-note"), "audio_unavailable", { error: a.error || "" }); return; }
      $("vol-out").value = a.output.volume; $("vol-out-v").textContent = `${a.output.volume}%`;
      $("vol-in").value = a.input.volume; $("vol-in-v").textContent = `${a.input.volume}%`;
      $("vol-out-m").classList.toggle("on", a.output.muted); $("vol-in-m").classList.toggle("on", a.input.muted);
      if (document.activeElement !== $("vol-out-d")) $("vol-out-d").innerHTML = options(a.outputs || [], a.output.device);
      if (document.activeElement !== $("vol-in-d")) $("vol-in-d").innerHTML = options(a.inputs || [], a.input.device);
      PageText.bind($("vol-note"), "audio_devices", { outputs: (a.outputs || []).length, inputs: (a.inputs || []).length });
      if (lastInput !== null && a.input.device !== lastInput) D.Ear.restartMic();
      lastInput = a.input.device;
    } catch (e) {
      console.warn("Audio non raggiungibile", e);
      PageText.bind($("vol-note"), "audio_unreachable");
    }
  }

  function setAudio(changes) {
    clearTimeout(volTimer);
    volTimer = setTimeout(() => fetch("/api/audio", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(changes) }).then(loadAudio), 180);
  }

  function showLook() {
    const { look, FACE } = D;
    $("avatar-pref").value = look.devicePref;
    PageText.bind($("avatar-pref").options[0], "look_system_value", { value: PageText.t("web/display", LOOK_KEYS[FACE.avatar] || LOOK_KEYS.auto) });
    const [why, params] = look.reason || ["why_average", {}];
    $("avatar-why").innerHTML = `${PageText.html("look_in_use")} ${PageText.html(LOOK_KEYS[look.mode] || LOOK_KEYS.auto)} — ${PageText.html(why, params)}.`;
  }

  const NUDGE = { lower: -8, raise: 8 };
  const INPUT_RANGE = [20, 130];
  let lastNudge = 0;

  D.nudgeMicInput = async (advice) => {
    const step = NUDGE[advice];
    if (!step || Date.now() - lastNudge < 8000) return false;
    lastNudge = Date.now();
    try {
      const a = await fetch("/api/audio", { credentials: "same-origin" }).then((r) => (r.ok ? r.json() : null));
      if (!a || !a.available || a.input.muted) return false;
      const next = Math.max(INPUT_RANGE[0], Math.min(INPUT_RANGE[1], Math.round(a.input.volume + step)));
      if (next === a.input.volume) return false;
      const r = await fetch("/api/audio", { method: "PUT", credentials: "same-origin", headers: { "Content-Type": "application/json", "X-Nuxiva-Request": "1" },
        body: JSON.stringify({ input: { volume: next } }) });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      if ($("vol-panel").classList.contains("show")) loadAudio();
      return true;
    } catch (err) {
      console.warn("Calibrazione del microfono non applicata", err);
      return false;
    }
  };

  const CAL_NOTES = { ok: "mic_cal_ok", lower: "mic_cal_lower", raise: "mic_cal_raise", browser: "mic_cal_browser" };

  function showCalibration() {
    const on = !D.Surfaces || D.Surfaces.settings.mic_autocalibrate !== false;
    $("mic-autocal").checked = on;
    PageText.bind($("mic-autocal-note"), on ? CAL_NOTES[D.micAdvice] || "mic_autocal_hint" : "mic_cal_off");
  }

  function failed(err) {
    console.warn("Impostazione del display non salvata", err);
    PageText.bind($("surf-error"), "settings_error");
  }

  D.onAudioRev = (rev) => {
    if (audioRev !== null && rev && rev !== audioRev) loadAudio();
    audioRev = rev || audioRev;
  };

  D.startAudioPanel = () => {
    if (navigator.mediaDevices && navigator.mediaDevices.addEventListener) {
      navigator.mediaDevices.addEventListener("devicechange", () => setTimeout(loadAudio, 800));
    }
    loadAudio();
    const panel = $("vol-panel"), button = $("btn-vol");
    const isOpen = () => panel.classList.contains("show");
    const setOpen = (open) => {
      panel.classList.toggle("show", open);
      button.classList.toggle("on", open);
      button.setAttribute("aria-expanded", String(open));
      if (open) { loadAudio(); showLook(); showCalibration(); $("voice-replies").checked = D.voiceOn; PageText.plain($("surf-error"), ""); }
    };
    D.closeAudioPanel = () => { if (isOpen()) setOpen(false); };
    button.addEventListener("click", () => {
      if (D.isFamilyNear && !D.isFamilyNear()) return;
      setOpen(!isOpen());
    });
    document.addEventListener("pointerdown", (e) => {
      if (isOpen() && !panel.contains(e.target) && !button.contains(e.target)) setOpen(false);
    }, { capture: true, passive: true });
    document.addEventListener("keydown", (e) => {
      if (e.key !== "Escape" || !isOpen()) return;
      setOpen(false);
      button.focus({ preventScroll: true });
    });
    let shownMode = D.mode;
    new MutationObserver(() => {
      if (D.mode === shownMode) return;
      shownMode = D.mode;
      D.closeAudioPanel();
    }).observe(document.body, { attributes: true, attributeFilter: ["class"] });
    $("mic-autocal").addEventListener("change", async (e) => {
      const want = e.target.checked;
      PageText.plain($("surf-error"), "");
      try { await D.Surfaces.save({ mic_autocalibrate: want }); } catch (err) { e.target.checked = !want; failed(err); }
      showCalibration();
    });
    $("voice-replies").addEventListener("change", (e) => D.setVoiceOn(e.target.checked));
    window.addEventListener("nuxiva-mic-advice", () => { if (isOpen()) showCalibration(); });
    $("avatar-pref").addEventListener("change", (e) => { NuxivaAvatar.setDevicePref(e.target.value); location.reload(); });
    $("vol-out").addEventListener("input", (e) => { $("vol-out-v").textContent = `${e.target.value}%`; setAudio({ output: { volume: +e.target.value } }); });
    $("vol-in").addEventListener("input", (e) => { $("vol-in-v").textContent = `${e.target.value}%`; setAudio({ input: { volume: +e.target.value } }); });
    $("vol-out-m").addEventListener("click", (e) => setAudio({ output: { muted: !e.target.classList.contains("on") } }));
    $("vol-in-m").addEventListener("click", (e) => setAudio({ input: { muted: !e.target.classList.contains("on") } }));
    $("vol-out-d").addEventListener("change", (e) => { e.target.blur(); setAudio({ output: { device: e.target.value } }); });
    $("vol-in-d").addEventListener("change", (e) => { e.target.blur(); setAudio({ input: { device: e.target.value } }); });
  };
})();
