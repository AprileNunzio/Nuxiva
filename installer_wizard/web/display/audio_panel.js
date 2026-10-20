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

  D.onAudioRev = (rev) => {
    if (audioRev !== null && rev && rev !== audioRev) loadAudio();
    audioRev = rev || audioRev;
  };

  D.startAudioPanel = () => {
    if (navigator.mediaDevices && navigator.mediaDevices.addEventListener) {
      navigator.mediaDevices.addEventListener("devicechange", () => setTimeout(loadAudio, 800));
    }
    loadAudio();
    $("btn-vol").addEventListener("click", () => { const p = $("vol-panel"); p.classList.toggle("show"); if (p.classList.contains("show")) { loadAudio(); showLook(); } });
    $("avatar-pref").addEventListener("change", (e) => { NuxivaAvatar.setDevicePref(e.target.value); location.reload(); });
    $("vol-out").addEventListener("input", (e) => { $("vol-out-v").textContent = `${e.target.value}%`; setAudio({ output: { volume: +e.target.value } }); });
    $("vol-in").addEventListener("input", (e) => { $("vol-in-v").textContent = `${e.target.value}%`; setAudio({ input: { volume: +e.target.value } }); });
    $("vol-out-m").addEventListener("click", (e) => setAudio({ output: { muted: !e.target.classList.contains("on") } }));
    $("vol-in-m").addEventListener("click", (e) => setAudio({ input: { muted: !e.target.classList.contains("on") } }));
    $("vol-out-d").addEventListener("change", (e) => { e.target.blur(); setAudio({ output: { device: e.target.value } }); });
    $("vol-in-d").addEventListener("change", (e) => { e.target.blur(); setAudio({ input: { device: e.target.value } }); });
  };
})();
