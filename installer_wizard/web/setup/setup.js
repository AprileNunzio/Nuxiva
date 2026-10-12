(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const FLOW = ["lang_select", "mic_calibration", "assistant_naming", "owner_config", "done"];

  const choice = {
    lang: "it",
    micCalibrated: false,
    assistantName: "Hey NUXIVA",
    gender: "female",
    sampleIndex: 0,
    samplesRecorded: [false, false, false],
    ownerFirst: "",
    ownerLast: "",
    faceEnrolled: false,
    brain: "local",
    cloudProvider: "gemini",
    cloudKey: "",
    ollamaUrl: "",
    voice: "if_sara"
  };

  let info = null;
  let at = 0;
  let code = "";
  let busy = false;
  let currentAudio = null;

  // Web Audio Context & Analyser
  let audioCtx = null;
  let analyserNode = null;
  let micStream = null;
  let animId = null;

  const error = (msg) => { $("error").textContent = msg || ""; };

  async function call(path, { body, file, raw } = {}) {
    const headers = { "X-Nuxiva-Request": "1" };
    if (code) headers["X-Nuxiva-Setup-Code"] = code;
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (file) headers["Content-Type"] = "application/octet-stream";
    const r = await fetch(path, {
      method: "POST", headers, credentials: "same-origin", cache: "no-store",
      body: file || (body !== undefined ? JSON.stringify(body) : undefined),
    });
    if (r.status === 410) { location.replace("/"); throw new Error(""); }
    if (!r.ok) {
      let detail = "Operazione non riuscita, riprova";
      try { detail = (await r.json()).detail || detail; } catch {}
      throw new Error(detail);
    }
    return raw ? r : r.json();
  }

  function setLanguage(lang) {
    choice.lang = lang;
    if (window.SetupI18n && typeof window.SetupI18n.applyLanguage === "function") {
      window.SetupI18n.applyLanguage(lang);
    }
    if (window.NuxivaI18n && typeof window.NuxivaI18n.switchTo === "function") {
      window.NuxivaI18n.switchTo(lang);
    }
    document.querySelectorAll(".lang-card").forEach((card) => {
      card.setAttribute("aria-checked", String(card.dataset.lang === lang));
    });
    updateStepCounter();
  }

  function updateStepCounter() {
    const total = FLOW.length - 1;
    const current = at + 1;
    if ($("step-of") && at < total) {
      if (window.SetupI18n && typeof window.SetupI18n.getStepText === "function") {
        $("step-of").textContent = window.SetupI18n.getStepText(choice.lang, current, total);
      } else {
        $("step-of").textContent = `Passo ${current} di ${total}`;
      }
    } else if ($("step-of")) {
      $("step-of").textContent = "";
    }

    const dots = $("dots");
    if (dots) {
      dots.replaceChildren();
      for (let i = 0; i < total; i++) {
        const li = document.createElement("li");
        if (i === at) li.className = "on";
        dots.append(li);
      }
    }
  }

  function showScreen(name) {
    document.querySelectorAll(".screen").forEach((s) => {
      s.hidden = s.dataset.screen !== name;
    });
    updateStepCounter();
    window.scrollTo({ top: 0, behavior: "smooth" });

    const isDone = name === "done";
    const isCode = name === "code";
    $("nav").hidden = isDone || isCode;
    $("back").hidden = at === 0;
    $("skip").hidden = name !== "owner_config" && name !== "assistant_naming";

    if (name === "mic_calibration" && !micStream) {
      initMicCalibration();
    }
    if (name === "assistant_naming") {
      initAudioVisualizer();
    }
  }

  // --- AUDIO CALIBRATION (STEP 2) ---
  async function initMicCalibration() {
    try {
      if (!micStream) {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
          throw new Error("MEDIA_UNAVAILABLE");
        }
        micStream = await navigator.mediaDevices.getUserMedia({
          audio: { echoCancellation: true, noiseSuppression: true, sampleRate: 48000 }
        });
      }
      audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const source = audioCtx.createMediaStreamSource(micStream);
      analyserNode = audioCtx.createAnalyser();
      analyserNode.fftSize = 256;
      source.connect(analyserNode);

      choice.micCalibrated = true;
      if ($("t-btn-mic")) $("t-btn-mic").textContent = "Microfono Calibrato & Attivo";
      if ($("hud-circle")) $("hud-circle").classList.add("active");
      if ($("hud-status")) $("hud-status").textContent = "Attivo";

      const pcmData = new Float32Array(analyserNode.fftSize);
      const updateMeter = () => {
        if (!analyserNode) return;
        analyserNode.getFloatTimeDomainData(pcmData);
        let sum = 0;
        for (let i = 0; i < pcmData.length; i++) sum += pcmData[i] * pcmData[i];
        const rms = Math.sqrt(sum / pcmData.length);
        const db = Math.max(-60, Math.round(20 * Math.log10(rms || 0.0001)));
        if ($("hud-db")) $("hud-db").textContent = `${db} dB`;
        if (at === 1) requestAnimationFrame(updateMeter);
      };
      updateMeter();
    } catch (e) {
      if ($("hud-status")) $("hud-status").textContent = "Microfono non rilevato";
    }
  }

  // --- VISUALIZER & WAKE-WORD STUDIO (STEP 3) ---
  function initAudioVisualizer() {
    const canvas = $("audio-visualizer");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (animId) cancelAnimationFrame(animId);

    const freqData = new Uint8Array(64);
    const timeData = new Uint8Array(128);

    function draw() {
      if (at !== 2) return;
      animId = requestAnimationFrame(draw);

      ctx.fillStyle = "rgba(2,6,16,0.4)";
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      if (analyserNode) {
        analyserNode.getByteFrequencyData(freqData);
        analyserNode.getByteTimeDomainData(timeData);

        const barWidth = (canvas.width / freqData.length) * 1.5;
        for (let i = 0; i < freqData.length; i++) {
          const v = freqData[i] / 255;
          const barHeight = v * canvas.height * 0.7;
          ctx.fillStyle = `rgba(41,224,255,${0.15 + v * 0.7})`;
          ctx.fillRect(i * (barWidth + 1), canvas.height - barHeight, barWidth, barHeight);
        }

        ctx.lineWidth = 2.5;
        ctx.strokeStyle = "#3dffa8";
        ctx.beginPath();
        const sliceWidth = canvas.width / timeData.length;
        let x = 0;
        for (let i = 0; i < timeData.length; i++) {
          const v = timeData[i] / 128.0;
          const y = (v * canvas.height) / 2;
          if (i === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
          x += sliceWidth;
        }
        ctx.stroke();

        const energy = freqData.reduce((a, b) => a + b, 0) / freqData.length;
        if ($("pitch-tag") && energy > 10) {
          const f0 = 120 + Math.round(energy * 1.8);
          $("pitch-tag").textContent = `F0: ${f0} Hz | RMS: ${(energy / 255).toFixed(2)}`;
        }
      } else {
        ctx.lineWidth = 2;
        ctx.strokeStyle = "rgba(41,224,255,0.4)";
        ctx.beginPath();
        const t = performance.now() / 600;
        for (let x = 0; x < canvas.width; x += 4) {
          const y = canvas.height / 2 + Math.sin(x * 0.03 + t) * 12;
          if (x === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();
      }
    }
    draw();
  }

  async function recordSample() {
    if (choice.samplesRecorded.every(Boolean)) return;
    const nextIdx = choice.samplesRecorded.indexOf(false);
    const slotEl = $(`slot-${nextIdx + 1}`);
    const label = $("btn-record-label");

    if (slotEl) {
      slotEl.classList.add("recording");
      slotEl.querySelector(".slot-status").textContent = "Acquisizione...";
    }
    if (label) label.textContent = "Ascolto in corso...";

    await new Promise((r) => setTimeout(r, 1600));

    try {
      await call("/api/setup/custom_wake_sample", {
        body: { index: nextIdx + 1, name: choice.assistantName }
      });
    } catch (e) {
      // Ignorato se backend offline durante test
    }

    choice.samplesRecorded[nextIdx] = true;
    if (slotEl) {
      slotEl.classList.remove("recording");
      slotEl.classList.add("done");
      slotEl.querySelector(".slot-status").textContent = "Confermato";
    }

    if (choice.samplesRecorded.every(Boolean)) {
      if (label) label.textContent = "Acquisizione completata!";
    } else {
      if (label) label.textContent = "Premi e pronuncia il nome";
    }
    error("");
  }

  async function playVoicePreview(gender) {
    if (currentAudio) {
      currentAudio.pause();
      currentAudio = null;
    }
    const name = choice.assistantName || "NUXIVA";
    try {
      const resp = await call("/api/setup/voice_preview", {
        body: { lang: choice.lang, gender, name },
        raw: true,
      });
      if (resp.headers.get("content-type")?.includes("audio")) {
        const blob = await resp.blob();
        currentAudio = new Audio(URL.createObjectURL(blob));
        currentAudio.play();
      } else if ("speechSynthesis" in window) {
        const u = new SpeechSynthesisUtterance(name);
        u.lang = choice.lang;
        window.speechSynthesis.speak(u);
      }
    } catch (e) {
      // Non bloccante
    }
  }

  // --- ATTACH LISTENERS ---
  function initListeners() {
    document.querySelectorAll(".lang-card").forEach((card) => {
      card.addEventListener("click", () => {
        setLanguage(card.dataset.lang);
      });
    });

    if ($("btn-request-mic")) {
      $("btn-request-mic").addEventListener("click", initMicCalibration);
    }

    if ($("assistant-name")) {
      $("assistant-name").addEventListener("input", (e) => {
        choice.assistantName = e.target.value.trim() || "Hey NUXIVA";
      });
    }

    document.querySelectorAll(".gender-card").forEach((card) => {
      card.addEventListener("click", (e) => {
        if (e.target.closest(".preview-sound-btn")) return;
        document.querySelectorAll(".gender-card").forEach((c) => c.classList.remove("active"));
        card.classList.add("active");
        choice.gender = card.dataset.gender;
      });
    });

    if ($("btn-play-female")) {
      $("btn-play-female").addEventListener("click", (e) => {
        e.stopPropagation();
        playVoicePreview("female");
      });
    }
    if ($("btn-play-male")) {
      $("btn-play-male").addEventListener("click", (e) => {
        e.stopPropagation();
        playVoicePreview("male");
      });
    }

    if ($("btn-record-sample")) {
      $("btn-record-sample").addEventListener("click", recordSample);
    }

    if ($("btn-enroll-face")) {
      $("btn-enroll-face").addEventListener("click", async () => {
        const fname = $("owner-name")?.value.trim() || "Nunzio";
        const lname = $("owner-last")?.value.trim() || "";
        $("btn-enroll-face").textContent = "Scansione...";
        let photoBase64 = "";
        try {
          if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
            const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user", width: { ideal: 640 }, height: { ideal: 480 } } });
            const video = document.createElement("video");
            video.srcObject = stream;
            video.playsInline = true;
            await video.play();
            const canvas = document.createElement("canvas");
            canvas.width = video.videoWidth || 640;
            canvas.height = video.videoHeight || 480;
            const ctx = canvas.getContext("2d");
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
            photoBase64 = canvas.toDataURL("image/jpeg", 0.85);
            stream.getTracks().forEach((track) => track.stop());
          }
        } catch (camErr) {}
        try {
          await call("/api/setup/face", { body: { name: fname, last_name: lname, photo_base64: photoBase64 } });
          choice.faceEnrolled = true;
          $("btn-enroll-face").textContent = "Registrato";
          $("face-feedback").textContent = "Completato";
        } catch (e) {
          $("btn-enroll-face").textContent = "Scansiona il mio viso";
          error(e.message);
        }
      });
    }

    document.querySelectorAll("#brains>.choice").forEach((b) => {
      b.addEventListener("click", () => {
        document.querySelectorAll("#brains>.choice").forEach((c) => c.setAttribute("aria-checked", "false"));
        b.setAttribute("aria-checked", "true");
        choice.brain = b.dataset.brain;
        if ($("brain-remote-input")) $("brain-remote-input").hidden = choice.brain !== "remote";
        if ($("brain-cloud-input")) $("brain-cloud-input").hidden = choice.brain !== "cloud";
      });
    });

    $("next").addEventListener("click", onNext);
    $("back").addEventListener("click", onBack);
    $("skip").addEventListener("click", () => {
      at++;
      showScreen(FLOW[at]);
    });
  }

  async function onNext() {
    error("");
    const currentScreen = FLOW[at];

    if (currentScreen === "assistant_naming") {
      choice.assistantName = $("assistant-name")?.value.trim() || "Hey NUXIVA";
      try {
        await call("/api/setup/assistant", {
          body: { name: choice.assistantName, gender: choice.gender, lang: choice.lang }
        });
      } catch (e) {
        // Ignorato
      }
    }

    if (currentScreen === "owner_config") {
      choice.ownerFirst = $("owner-name")?.value.trim();
      choice.ownerLast = $("owner-last")?.value.trim() || "";
      if (!choice.ownerFirst) {
        error("Scrivi il tuo nome: serve per riconoscerti e salutarti");
        return;
      }

      busy = true;
      $("next").disabled = true;
      try {
        await call("/api/setup", {
          body: {
            name: choice.ownerFirst,
            last_name: choice.ownerLast,
            lang: choice.lang,
            voice_lang: choice.lang,
            brain: choice.brain,
            ollama_url: $("ollama-url")?.value.trim() || "",
            cloud_provider: choice.cloudProvider,
            cloud_key: $("cloud-key")?.value.trim() || "",
            packages: ["voice", "vision", "ear", "documents"],
            commercial: false,
          }
        });

        if ($("sum-assist")) $("sum-assist").textContent = `${choice.assistantName} (${choice.gender === "female" ? "Donna" : "Uomo"})`;
        if ($("sum-owner")) $("sum-owner").textContent = `${choice.ownerFirst} ${choice.ownerLast}`.trim();
        if ($("sum-lang")) $("sum-lang").textContent = choice.lang.toUpperCase();

        at++;
        showScreen(FLOW[at]);
        playVoicePreview(choice.gender);
      } catch (e) {
        error(e.message);
      } finally {
        busy = false;
        $("next").disabled = false;
      }
      return;
    }

    if (at < FLOW.length - 1) {
      at++;
      showScreen(FLOW[at]);
    }
  }

  function onBack() {
    if (at > 0) {
      at--;
      showScreen(FLOW[at]);
    }
  }

  async function init() {
    initListeners();
    try {
      const r = await fetch("/api/setup", { cache: "no-store", headers: { "X-Nuxiva-Request": "1" } });
      if (r.ok) {
        info = await r.json();
        if (!info.needed) {
          location.replace("/");
          return;
        }
        if (info.code) code = info.code;
        if (info.current?.lang) choice.lang = info.current.lang;
        if (info.hardware && $("hw-desc")) {
          const hw = info.hardware;
          $("hw-desc").textContent = `${hw.cpu} CPU · ${hw.ram_gb} GB RAM · ${hw.disk_free_gb} GB liberi sul disco`;
        }
      }
    } catch (e) {
      // Ignorato
    }

    setLanguage(choice.lang);
    showScreen(FLOW[0]);
  }

  window.addEventListener("DOMContentLoaded", init);
})();
