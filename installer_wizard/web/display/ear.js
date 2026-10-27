(() => {
  const D = window.NuxivaDisplay, { $ } = D;
  const bars = [], waveBars = [];
  let lastAlone = null, wsFails = 0, restarting = false, lastTry = Date.now(), heardAt = 0;
  const stats = { opens: 0, msgs: 0, sends: 0, mic: 0, made: 0 };
  const PAGE = Math.random().toString(36).slice(2, 8);
  const OPT_IN = "nuxiva-remote-mic";
  const AUTO_AGC = "nuxiva-mic-agc";
  let autoLevel = false, agcOn = false;
  const agcLearned = () => { try { return localStorage.getItem(AUTO_AGC) === "1"; } catch (e) { return false; } };
  const optedIn = () => { try { return localStorage.getItem(OPT_IN) === "1"; } catch (e) { return false; } };
  const secure = () => window.isSecureContext && !!navigator.mediaDevices;
  const micAllowed = () => D.local || (secure() && optedIn());
  const socketUrl = () => `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/ear`;
  let parked = false;
  document.addEventListener("visibilitychange", () => {
    send({ type: "client", page: PAGE, visible: document.visibilityState });
    if (parked && document.visibilityState === "visible") { parked = false; restartMic(); connect(); }
  });
  let ws = null, ctx = null, stream = null, state = "off", history = new Array(28).fill(0);
  const WORKLET = `class Tap extends AudioWorkletProcessor { process(inp) { const c = inp[0] && inp[0][0]; if (c) this.port.postMessage(c.slice(0)); return true; } }
      registerProcessor("nuxiva-tap", Tap);`;
  const TITLES = { idle: ["ear_idle", {}], listening: ["ear_listening", {}], transcribing: ["ear_listening", {}], off: ["ear_off", {}] };
  let assistant = D.assistantName();

  async function report(ok, error) {
    let inputs = 0, label = "";
    try { inputs = (await withTimeout(navigator.mediaDevices.enumerateDevices(), 3000, "enumerate")).filter((d) => d.kind === "audioinput").length; } catch (e) {}
    try { label = stream ? stream.getAudioTracks()[0].label : ""; } catch (e) {}
    fetch("/api/ear/client", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ok, error: error || "", inputs, label }) }).catch(() => {});
  }

  function setState(s, text) {
    const { avatar } = D;
    state = s;
    const [key, params] = text || TITLES[s];
    const full = { assistant, ...params };
    window.dispatchEvent(new CustomEvent("nuxiva-ear", { detail: { state: s, key } }));
    PageText.bind($("ear-text"), key, full);
    PageText.attr($("btn-mic"), { title: key, "aria-label": key }, full);
    $("ear").className = `ear ${s}`;
    $("btn-mic").className = `ibtn mic ${s === "listening" ? "listening" : s === "off" ? "off" : ""}`;
    document.body.classList.toggle("listening", s === "listening");
    document.body.classList.toggle("transcribing", s === "transcribing");
    if (avatar && avatar.face) {
      avatar.face.listening = s === "listening";
      if (!D.busy) avatar.setTint(s === "listening" ? "#3dffa8" : s === "transcribing" ? "#b36bff" : (D.currentTint ? D.currentTint() : (D.tint || "#29e0ff")));
    }
  }

  function level(v) {
    bars.forEach((b, i) => { b.style.height = `${2 + Math.max(0, v * 16 - Math.abs(i - 6) * 1.2 + Math.random() * 3)}px`; });
    history.push(v); history.shift();
    window.dispatchEvent(new CustomEvent("nuxiva-ear-level", { detail: v }));
    if (state === "listening") waveBars.forEach((b, i) => { b.style.height = `${6 + history[i] * 64 * (0.6 + 0.4 * Math.sin(i * 0.9))}px`; });
    const m = $("vol-in-meter"); if (m) m.style.width = `${Math.min(100, v * 100)}%`;
    D.Mood.level(v);
    if (state === "listening" && D.avatar && D.avatar.setInputLevel) D.avatar.setInputLevel(v);
  }

  function send(obj) { if (ws && ws.readyState === 1) ws.send(JSON.stringify(obj)); }

  function withTimeout(promise, ms, why) {
    return Promise.race([promise, new Promise((_, ko) => setTimeout(() => ko(Object.assign(new Error(why), { name: "Timeout" })), ms))]);
  }

  async function micConstraints() {
    let tune = { echoCancellation: true, noiseSuppression: false, autoGainControl: false, autoLevel: true };
    try {
      const r = await withTimeout(fetch("/api/ear/config", { cache: "no-store" }), 3000, "configurazione del microfono");
      if (r.ok) tune = await r.json();
    } catch (e) { console.warn("Configurazione del microfono non letta, uso i valori predefiniti", e); }
    autoLevel = !!tune.autoLevel;
    agcOn = !!tune.autoGainControl || (autoLevel && agcLearned());
    return { deviceId: "default", channelCount: 1, echoCancellation: !!tune.echoCancellation,
      noiseSuppression: !!tune.noiseSuppression, autoGainControl: agcOn };
  }

  async function openMic() {
    try {
      const asked = micConstraints().then((audio) => navigator.mediaDevices.getUserMedia({ audio }));
      try { stream = await withTimeout(asked, 12000, "il browser non risponde alla richiesta del microfono"); }
      catch (err) { asked.then((s) => s.getTracks().forEach((t) => t.stop())).catch(() => {}); throw err; }
      ctx = new AudioContext();
      if (ctx.state === "suspended") ctx.resume().catch(() => {});
      await withTimeout(ctx.audioWorklet.addModule(URL.createObjectURL(new Blob([WORKLET], { type: "application/javascript" }))),
        8000, "il motore audio del browser non si avvia");
      const src = ctx.createMediaStreamSource(stream), tap = new AudioWorkletNode(ctx, "nuxiva-tap");
      src.connect(tap);
      const ratio = ctx.sampleRate / 16000;
      let acc = [], pos = 0;
      tap.port.onmessage = (e) => {
        const input = e.data;
        for (; pos < input.length; pos += ratio) acc.push(input[Math.floor(pos)]);
        pos -= input.length;
        if (acc.length >= 1600) {
          const pcm = new Int16Array(acc.length);
          for (let i = 0; i < acc.length; i++) pcm[i] = Math.max(-32768, Math.min(32767, acc[i] * 32767));
          acc = [];
          if (ws && ws.readyState === 1) { ws.send(pcm.buffer); stats.sends++; }
        }
      };
      stream.getAudioTracks().forEach((t) => { t.onended = () => { report(false, "il microfono si è scollegato"); setTimeout(restartMic, 2000); }; });
      stats.mic++;
      report(true);
      return true;
    } catch (err) {
      console.warn("Microfono non disponibile", err);
      try { stream && stream.getTracks().forEach((t) => t.stop()); } catch (e) {}
      try { ctx && ctx.close(); } catch (e) {}
      stream = null; ctx = null;
      const why = err && err.name === "Timeout" ? ["ear_err_timeout", {}] : err && err.name === "NotFoundError" ? ["ear_err_missing", {}]
        : err && err.name === "NotAllowedError" ? ["ear_err_denied", {}] : err && err.name === "NotReadableError" ? ["ear_err_busy", {}]
        : ["ear_err_other", { detail: err ? `${err.name} ${err.message}` : "" }];
      report(false, why);
      setState("off", ["ear_unavailable", { why: PageText.t("web/display", why[0], why[1]) || why[0] }]);
      return false;
    }
  }

  function micLive() {
    return Date.now() - heardAt < 10000 || (!!stream && stream.getAudioTracks().some((t) => t.readyState === "live"));
  }

  function reconcile() {
    if (parked) return;
    if (!ws || ws.readyState > 1) connect();
    if (!micAllowed()) return;
    const confirmed = Date.now() - heardAt < 10000;
    if (confirmed && state === "off") setState("idle");
    else if (!confirmed && state !== "off" && !(ws && ws.readyState === 1 && micLive())) setState("off");
    if (!confirmed && !restarting && Date.now() - lastTry > 15000) {
      lastTry = Date.now();
      if (!micLive()) restartMic();
    }
  }

  function connect() {
    if (ws && ws.readyState <= 1) return;
    const sock = ws = new WebSocket(socketUrl());
    stats.made++;
    sock.binaryType = "arraybuffer";
    const stuck = setTimeout(() => {
      if (ws !== sock || sock.readyState !== 0) return;
      ws = null;
      try { sock.close(); } catch (e) {}
      report(false, "collegamento all'ascolto bloccato: il servizio non completa la connessione");
      setTimeout(connect, 3000);
    }, 30000);
    sock.onopen = () => {
      stats.opens++;
      clearTimeout(stuck);
      if (ws !== sock) return;
      sock.send(JSON.stringify({ type: "client", page: PAGE, visible: document.visibilityState, href: location.pathname + location.search }));
      if (micLive()) setState("idle");
      else setState("off", offReason());
      lastAlone = null; if (wsFails) report(true); wsFails = 0;
    };
    sock.onclose = (e) => {
      clearTimeout(stuck);
      if (ws !== sock) return;
      if (e.code === 4001) {
        ws = null; parked = true;
        try { stream && stream.getTracks().forEach((t) => t.stop()); } catch (err) {}
        stream = null;
        setState("off", ["ear_parked", {}]);
        return;
      }
      ws = null;
      wsFails++;
      if (wsFails % 5 === 1) report(false, `servizio di ascolto non raggiungibile da ${location.host}/ws/ear (codice ${e.code}, tentativo ${wsFails})`);
      setState("off", ["ear_reconnecting", {}]);
      setTimeout(connect, 3000);
    };
    sock.onmessage = (e) => {
      stats.msgs++;
      if (ws !== sock) {
        if (sock.readyState !== 1) return;
        const old = ws;
        ws = sock;
        if (old && old !== sock) { try { old.close(); } catch (err) {} }
      }
      const ev = JSON.parse(e.data);
      if (D.Captions) D.Captions.event(ev);
      if (ev.type === "level") {
        heardAt = Date.now();
        level(ev.rms);
        if (D.Enroll && D.Enroll.active) D.Enroll.level(ev.rms);
        if (state === "off" && micAllowed()) setState("idle");
      }
      else if (ev.type === "state") { setState(ev.state); document.body.classList.toggle("conversing", !!ev.conversation); }
      else if (ev.type === "wake") { D.lastInteraction = Date.now(); D.pingActivity(true); setState("listening"); if (D.mode === "brain") D.setMode("face"); if (D.wakeDesk) D.wakeDesk(); }
      else if (ev.type === "barge") { if (D.hush) D.hush(); }
      else if (ev.type === "mic_level") micLevelAdvice(ev.advice);
      else if (ev.type === "wake_only") D.greetWake();
      else if (ev.type === "conversation_end") document.body.classList.remove("conversing");
      else if (ev.type === "enroll_progress") D.Enroll.progress(ev);
      else if (ev.type === "enroll_unavailable") D.Enroll.unavailable();
      else if (ev.type === "transcript" && ev.text) {
        D.lastVoice = true;
        if (ev.speaker) D.currentSpeaker = ev.speaker;
        if (ev.origin !== false && micLive()) {
          D.ask(ev.text, ev.lang, { followup: !!ev.followup, speaker: ev.speaker || "", voice_known: ev.voice_known });
        }
      }
    };
  }

  async function start() {
    for (let i = 0; i < 12; i++) { const b = document.createElement("i"); $("ear-bars").appendChild(b); bars.push(b); }
    for (let i = 0; i < 28; i++) { const b = document.createElement("i"); $("listen-wave").appendChild(b); waveBars.push(b); }
    $("btn-mic").addEventListener("click", () => {
      if (D.isFamilyNear && !D.isFamilyNear()) return;
      if (!micAllowed()) return enableRemote();
      Ear.listen();
    });
    setInterval(reconcile, 5000);
    connect();
    if (!micAllowed()) { setState("off", offReason()); return; }
    await activate();
  }

  function offReason() {
    if (secure()) return ["ear_tap_local", {}];
    return ["ear_need_https", {}];
  }

  let activated = false;
  async function activate() {
    if (activated) return;
    activated = true;
    connect();
    if (await openMic() && ws && ws.readyState === 1) setState("idle");
  }

  async function enableRemote() {
    if (!secure()) { setState("off", offReason()); return; }
    try { localStorage.setItem(OPT_IN, "1"); } catch (e) {}
    await activate();
  }

  function micLevelAdvice(advice) {
    if (advice !== "lower" || !autoLevel || agcOn) return;
    try { localStorage.setItem(AUTO_AGC, "1"); } catch (e) { console.warn("Preferenza del livello del microfono non salvata", e); }
    restartMic();
  }

  async function restartMic() {
    if (!micAllowed() || restarting) return;
    restarting = true;
    try {
      try { stream && stream.getTracks().forEach((t) => t.stop()); } catch (e) {}
      try { ctx && ctx.close(); } catch (e) {}
      stream = null; ctx = null;
      if (!(await openMic())) return;
      if (!ws) connect();
      else if (ws.readyState === 1) setState("idle");
    } finally {
      restarting = false;
    }
  }

  let resetSeen = 0;
  if (navigator.mediaDevices) navigator.mediaDevices.addEventListener("devicechange", () => { if (state === "off") restartMic(); });

  const Ear = D.Ear = window.nuxivaEar = {
    resetFrom(t) { if (!t || t === resetSeen) return; if (resetSeen) restartMic(); resetSeen = t; },
    setAssistantName(name) { if (!name || name === assistant) return; assistant = name; setState(state); },
    start, send, restartMic, debugState: setState, debugLevel: level,
    listen() { if (ctx && ctx.state === "suspended") ctx.resume(); D.pingActivity(true); send({ type: "listen" }); setState("listening"); },
    speaking(on) { send({ type: "speaking", on }); },
    followup(seconds = 20) { send({ type: "followup", seconds, conversation: true }); },
    presence(alone) { if (alone !== lastAlone) { lastAlone = alone; send({ type: "presence", alone: alone || "" }); } },
    get state() { return state; },
    get micReady() { return micAllowed() && !!stream && stream.getAudioTracks().some((track) => track.readyState === "live"); },
    get link() { return `pagina=${PAGE} ${document.visibilityState} v=${(window.NUXIVA_ASSET_V || "").slice(0, 7)} ws=${ws ? ["connessione", "aperto", "chiusura", "chiuso"][ws.readyState] : "nessuno"} mic=${micLive() ? "attivo" : "spento"} audio=${heardAt ? Math.round((Date.now() - heardAt) / 1000) + "s" : "mai"} errori=${wsFails} t=${Math.round(performance.now() / 1000)}s ws_creati=${stats.made} aperti=${stats.opens} msg=${stats.msgs} inviati=${stats.sends} mic_ok=${stats.mic}`; },
  };
})();
