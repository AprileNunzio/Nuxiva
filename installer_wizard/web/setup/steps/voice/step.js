(() => {
  "use strict";

  class StepVoice {
    constructor() {
      this.audioCtx = null;
      this.analyser = null;
      this.micStream = null;
      this.animId = null;
      this.activeSource = "client";
    }

    t(key) {
      const lang = window.SetupStorage.get("lang") || "it";
      const dict = (window.SetupStepVoiceI18n && window.SetupStepVoiceI18n.dict[lang]) || {};
      return dict[key] || "";
    }

    async populateDevices() {
      const select = document.getElementById("voice-mic-select");
      if (!select) return;
      select.innerHTML = "";

      if (this.activeSource === "client") {
        let found = [];
        if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
          try {
            const devs = await navigator.mediaDevices.enumerateDevices();
            found = devs.filter((d) => d.kind === "audioinput");
          } catch (e) {}
        }

        if (found.length === 0) {
          const opt = document.createElement("option");
          opt.value = "default";
          opt.textContent = "Microfono PC Client (Auto-Detect)";
          select.appendChild(opt);
        } else {
          found.forEach((dev, idx) => {
            const opt = document.createElement("option");
            opt.value = dev.deviceId || `mic-${idx}`;
            opt.textContent = dev.label || `Microfono PC ${idx + 1}`;
            select.appendChild(opt);
          });
        }
        this.startMonitoring(select.value);
      } else {
        this.stopMonitoring();
        const opt = document.createElement("option");
        opt.value = "server_default";
        opt.textContent = "Microfono Server Fisico (ALSA / Default Pulse)";
        select.appendChild(opt);

        const optUsb = document.createElement("option");
        optUsb.value = "server_usb";
        optUsb.textContent = "Microfono USB Server (Array / Far-Field)";
        select.appendChild(optUsb);

        this.startSimulatedMonitoring();
      }
    }

    setSource(source) {
      this.activeSource = source;
      window.SetupStorage.set("voiceSource", source);

      const tabClient = document.getElementById("voice-tab-client");
      const tabServer = document.getElementById("voice-tab-server");
      if (tabClient) tabClient.classList.toggle("is-active", source === "client");
      if (tabServer) tabServer.classList.toggle("is-active", source === "server");

      this.populateDevices();
    }

    async startMonitoring(deviceId) {
      this.stopMonitoring();
      const vuFill = document.getElementById("voice-vu-fill");
      const vuVal = document.getElementById("voice-vu-val");

      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        try {
          const constraints = {
            audio: deviceId && deviceId !== "default" ? { deviceId: { exact: deviceId } } : true
          };
          this.micStream = await navigator.mediaDevices.getUserMedia(constraints);
          this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
          this.analyser = this.audioCtx.createAnalyser();
          this.analyser.fftSize = 256;
          const source = this.audioCtx.createMediaStreamSource(this.micStream);
          source.connect(this.analyser);

          const dataArray = new Uint8Array(this.analyser.frequencyBinCount);
          const update = () => {
            if (!this.analyser) return;
            this.analyser.getByteFrequencyData(dataArray);
            let sum = 0;
            for (let i = 0; i < dataArray.length; i++) {
              sum += dataArray[i];
            }
            const avg = sum / dataArray.length;
            const pct = Math.min(100, Math.round((avg / 128) * 100));
            const db = -60 + Math.round((pct / 100) * 55);

            if (vuFill) vuFill.style.width = `${pct}%`;
            if (vuVal) vuVal.textContent = `${db} dBFS`;
            this.animId = requestAnimationFrame(update);
          };
          update();
          return;
        } catch (e) {}
      }

      this.startSimulatedMonitoring();
    }

    startSimulatedMonitoring() {
      this.stopMonitoring();
      const vuFill = document.getElementById("voice-vu-fill");
      const vuVal = document.getElementById("voice-vu-val");
      let simVal = 18;
      const simUpdate = () => {
        simVal = 14 + Math.random() * 22;
        if (vuFill) vuFill.style.width = `${simVal}%`;
        if (vuVal) vuVal.textContent = `-${Math.round(55 - simVal)} dBFS`;
        this.animId = setTimeout(simUpdate, 120);
      };
      simUpdate();
    }

    stopMonitoring() {
      if (this.animId) {
        cancelAnimationFrame(this.animId);
        clearTimeout(this.animId);
        this.animId = null;
      }
      if (this.micStream) {
        this.micStream.getTracks().forEach((t) => t.stop());
        this.micStream = null;
      }
      if (this.audioCtx) {
        this.audioCtx.close().catch(() => {});
        this.audioCtx = null;
      }
    }

    async init() {
      const tabClient = document.getElementById("voice-tab-client");
      const tabServer = document.getElementById("voice-tab-server");
      const micSelect = document.getElementById("voice-mic-select");

      if (tabClient) tabClient.addEventListener("click", () => this.setSource("client"));
      if (tabServer) tabServer.addEventListener("click", () => this.setSource("server"));
      if (micSelect) {
        micSelect.addEventListener("change", (e) => {
          window.SetupStorage.set("micDevice", e.target.value);
          if (this.activeSource === "client") {
            this.startMonitoring(e.target.value);
          }
        });
      }

      const gainSlider = document.getElementById("voice-gain-slider");
      const gainVal = document.getElementById("voice-gain-val");
      if (gainSlider && gainVal) {
        gainSlider.addEventListener("input", (e) => {
          gainVal.textContent = `${e.target.value} dB`;
          window.SetupStorage.set("micGain", e.target.value);
        });
      }

      this.setSource(window.SetupStorage.get("voiceSource") || "client");
    }
  }

  window.SetupStepVoice = new StepVoice();
})();
