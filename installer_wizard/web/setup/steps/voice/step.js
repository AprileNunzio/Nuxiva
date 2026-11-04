(() => {
  "use strict";

  class StepVoice {
    constructor() {
      this.audioCtx = null;
      this.analyser = null;
      this.micStream = null;
      this.animId = null;
      this.activeSource = "client";
      this.hasRequestedPermission = false;
    }

    t(key) {
      const lang = window.SetupStorage.get("lang") || "it";
      const dict = (window.SetupStepVoiceI18n && window.SetupStepVoiceI18n.dict[lang]) || {};
      return dict[key] || "";
    }

    async requestMicPermission(deviceId) {
      const permBar = document.getElementById("voice-perm-bar");

      this.stopMonitoring();

      if (!navigator.mediaDevices?.getUserMedia) {
        this.startSimulatedMonitoring();
        return;
      }

      const constraints = {
        audio: deviceId && deviceId !== "default" ? { deviceId: { exact: deviceId } } : true
      };

      try {
        this.micStream = await navigator.mediaDevices.getUserMedia(constraints);
        if (permBar) permBar.classList.add("is-hidden");
        this.hasRequestedPermission = true;

        this.startAudioContext();
        await this.populateClientDevices();
      } catch (err) {
        if (permBar) permBar.classList.remove("is-hidden");
        this.startSimulatedMonitoring();
      }
    }

    startAudioContext() {
      if (!this.micStream) return;
      try {
        this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        this.analyser = this.audioCtx.createAnalyser();
        this.analyser.fftSize = 256;
        const source = this.audioCtx.createMediaStreamSource(this.micStream);
        source.connect(this.analyser);

        const vuFill = document.getElementById("voice-vu-fill");
        const vuVal = document.getElementById("voice-vu-val");
        const dataArray = new Uint8Array(this.analyser.frequencyBinCount);

        const update = () => {
          if (!this.analyser) return;
          this.analyser.getByteFrequencyData(dataArray);
          let sum = 0;
          for (let i = 0; i < dataArray.length; i++) sum += dataArray[i];
          const avg = sum / dataArray.length;
          const pct = Math.min(100, Math.round((avg / 128) * 100));
          const db = -60 + Math.round((pct / 100) * 55);

          if (vuFill) vuFill.style.width = `${pct}%`;
          if (vuVal) vuVal.textContent = `${db} dBFS`;
          this.animId = requestAnimationFrame(update);
        };
        update();
      } catch (e) {
        this.startSimulatedMonitoring();
      }
    }

    startSimulatedMonitoring() {
      this.stopMonitoring();
      const vuFill = document.getElementById("voice-vu-fill");
      const vuVal = document.getElementById("voice-vu-val");
      let simVal = 16;
      const simUpdate = () => {
        simVal = 12 + Math.random() * 20;
        if (vuFill) vuFill.style.width = `${simVal}%`;
        if (vuVal) vuVal.textContent = `-${Math.round(55 - simVal)} dBFS`;
        this.animId = setTimeout(simUpdate, 120);
      };
      simUpdate();
    }

    async populateClientDevices() {
      const select = document.getElementById("voice-mic-select");
      if (!select || !navigator.mediaDevices?.enumerateDevices) return;
      select.innerHTML = "";

      try {
        const devs = await navigator.mediaDevices.enumerateDevices();
        const mics = devs.filter((d) => d.kind === "audioinput");
        if (mics.length === 0) {
          const opt = document.createElement("option");
          opt.value = "default";
          opt.textContent = "Microfono PC Client (Auto-Detect)";
          select.appendChild(opt);
        } else {
          mics.forEach((dev, idx) => {
            const opt = document.createElement("option");
            opt.value = dev.deviceId || `mic-${idx}`;
            opt.textContent = dev.label || `Microfono ${idx + 1}`;
            select.appendChild(opt);
          });
        }
      } catch (e) {}
    }

    populateServerDevices() {
      const select = document.getElementById("voice-mic-select");
      const permBar = document.getElementById("voice-perm-bar");
      if (permBar) permBar.classList.add("is-hidden");
      if (!select) return;
      select.innerHTML = "";

      const opt = document.createElement("option");
      opt.value = "server_default";
      opt.textContent = "Microfono Server Fisico (ALSA / Pulse)";
      select.appendChild(opt);

      const optUsb = document.createElement("option");
      optUsb.value = "server_usb";
      optUsb.textContent = "Microfono USB Server (Array / Far-Field)";
      select.appendChild(optUsb);

      this.startSimulatedMonitoring();
    }

    setSource(source) {
      this.activeSource = source;
      window.SetupStorage.set("voiceSource", source);

      const tabClient = document.getElementById("voice-tab-client");
      const tabServer = document.getElementById("voice-tab-server");
      if (tabClient) tabClient.classList.toggle("is-active", source === "client");
      if (tabServer) tabServer.classList.toggle("is-active", source === "server");

      if (source === "client") {
        this.requestMicPermission();
      } else {
        this.populateServerDevices();
      }
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

    init() {
      const tabClient = document.getElementById("voice-tab-client");
      const tabServer = document.getElementById("voice-tab-server");
      const micSelect = document.getElementById("voice-mic-select");
      const btnReqPerm = document.getElementById("btn-req-voice-perm");

      if (tabClient) tabClient.addEventListener("click", () => this.setSource("client"));
      if (tabServer) tabServer.addEventListener("click", () => this.setSource("server"));
      if (btnReqPerm) btnReqPerm.addEventListener("click", () => this.requestMicPermission());

      if (micSelect) {
        micSelect.addEventListener("change", (e) => {
          window.SetupStorage.set("micDevice", e.target.value);
          if (this.activeSource === "client") {
            this.requestMicPermission(e.target.value);
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
