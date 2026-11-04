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
      this.initialized = false;
    }

    t(key) {
      const lang = window.SetupStorage.get("lang") || "it";
      const dict = (window.SetupStepVoiceI18n && window.SetupStepVoiceI18n.dict[lang]) || {};
      return dict[key] || "";
    }

    async acquireAudioStream(deviceId) {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        const legacy = navigator.getUserMedia || navigator.webkitGetUserMedia || navigator.mozGetUserMedia;
        if (legacy) {
          return new Promise((resolve, reject) => {
            legacy.call(navigator, { audio: true }, resolve, reject);
          });
        }
        throw new Error("SECURE_CONTEXT_REQUIRED");
      }

      const constraints = {
        audio: deviceId && deviceId !== "default" ? { deviceId: { exact: deviceId } } : true
      };
      return await navigator.mediaDevices.getUserMedia(constraints);
    }

    async requestMicPermission(deviceId) {
      const permBar = document.getElementById("voice-perm-bar");
      const btn = document.getElementById("btn-req-voice-perm");

      this.stopMonitoring();
      if (btn) btn.textContent = "Accesso microfono...";

      try {
        this.micStream = await this.acquireAudioStream(deviceId);
        if (permBar) permBar.classList.add("is-hidden");
        this.hasRequestedPermission = true;

        this.startAudioContext();
        await this.populateClientDevices();
      } catch (err) {
        if (permBar) {
          permBar.classList.remove("is-hidden");
          if (btn) {
            if (err.message === "SECURE_CONTEXT_REQUIRED" || !window.isSecureContext) {
              btn.textContent = "Passa a Microfoni Server";
              btn.onclick = () => this.setSource("server");
            } else {
              btn.textContent = this.t("btn_req_perm");
            }
          }
        }
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
          opt.textContent = "Microfono Predefinito";
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

    async populateServerDevices() {
      const select = document.getElementById("voice-mic-select");
      const permBar = document.getElementById("voice-perm-bar");
      if (permBar) permBar.classList.add("is-hidden");
      if (!select) return;
      select.innerHTML = "";

      try {
        const res = await fetch("/api/setup/hardware");
        if (res.ok) {
          const data = await res.json();
          const mics = data.audio_devices || [];
          if (mics.length === 0) {
            const opt = document.createElement("option");
            opt.value = "default";
            opt.textContent = "Microfono Server (Alsa/Pulse)";
            select.appendChild(opt);
          } else {
            mics.forEach((d) => {
              const opt = document.createElement("option");
              opt.value = d.id || d.name;
              opt.textContent = `${d.name || d.id}`;
              select.appendChild(opt);
            });
          }
        }
      } catch (e) {
        const opt = document.createElement("option");
        opt.value = "default";
        opt.textContent = "Microfono Server";
        select.appendChild(opt);
      }
      this.startSimulatedMonitoring();
    }

    setSource(source) {
      this.activeSource = source;
      window.SetupStorage.set("voiceSource", source);

      const tabClient = document.getElementById("voice-tab-client");
      const tabServer = document.getElementById("voice-tab-server");
      const permBar = document.getElementById("voice-perm-bar");

      if (tabClient) tabClient.classList.toggle("is-active", source === "client");
      if (tabServer) tabServer.classList.toggle("is-active", source === "server");

      if (source === "client") {
        if (this.hasRequestedPermission) {
          this.requestMicPermission();
        } else {
          if (permBar) permBar.classList.remove("is-hidden");
          this.startSimulatedMonitoring();
        }
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
      if (!this.initialized) {
        this.initialized = true;
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
      }

      this.setSource(window.SetupStorage.get("voiceSource") || "client");
    }
  }

  window.SetupStepVoice = new StepVoice();
})();