(() => {
  "use strict";

  const HEADERS = { "X-Nuxiva-Request": "1", "Content-Type": "application/json" };
  const FLOOR_DB = -70;
  const TARGET_DB = -20;
  const WINDOW = 75;
  const $ = (id) => document.getElementById(id);

  class StepVoice {
    constructor() {
      this.mic = null;
      this.timer = 0;
      this.buffer = null;
      this.history = [];
      this.peakHold = FLOOR_DB;
      this.calibrating = false;
      this.initialized = false;
    }

    t(key, vars) {
      const lang = window.SetupStorage.get("lang") || "it";
      const all = (window.SetupStepVoiceI18n && window.SetupStepVoiceI18n.dict) || {};
      const text = (all[lang] && all[lang][key]) || (all.it && all.it[key]) || "";
      return vars ? text.replace(/\{(\w+)\}/g, (_, k) => (k in vars ? String(vars[k]) : "")) : text;
    }

    applyTexts() {
      document.querySelectorAll("#screen-voice [data-voice-i18n]").forEach((el) => {
        el.textContent = this.t(el.dataset.voiceI18n);
      });
    }

    setText(id, text) {
      const el = $(id);
      if (el) el.textContent = text;
    }

    active() {
      const screen = $("screen-voice");
      return Boolean(screen && screen.classList.contains("active"));
    }

    options() {
      return {
        deviceId: $("voice-mic-select")?.value || window.SetupStorage.get("micDevice") || "",
        echo: Boolean($("voice-opt-echo")?.checked),
        noise: Boolean($("voice-opt-noise")?.checked),
      };
    }

    async openMic() {
      const bar = $("voice-perm-bar");
      if (!window.SetupAudio || !window.SetupAudio.available()) {
        if (bar) bar.classList.remove("is-hidden");
        this.setText("voice-perm-text", this.t("err_insecure"));
        return;
      }
      try {
        this.mic = await window.SetupAudio.open(this.options());
        window.SetupAudio.setGain(this.mic, Number(window.SetupStorage.get("micGain") || 0));
        this.buffer = new Float32Array(this.mic.analyser.fftSize);
        if (bar) bar.classList.add("is-hidden");
        this.setText("voice-val-rate", `${(this.mic.rate / 1000).toFixed(1)} kHz`);
        this.showGain(this.mic.gainDb);
        await this.listMics();
        this.loop();
      } catch (err) {
        if (bar) bar.classList.remove("is-hidden");
        const name = err && err.name;
        this.setText("voice-perm-text", this.t(name === "NotFoundError" ? "err_missing" : name === "NotReadableError" ? "err_busy" : "err_denied"));
      }
    }

    async listMics() {
      const select = $("voice-mic-select");
      if (!select || !navigator.mediaDevices?.enumerateDevices) return;
      const current = this.mic?.stream.getAudioTracks()[0]?.getSettings().deviceId || "";
      const mics = (await navigator.mediaDevices.enumerateDevices()).filter((d) => d.kind === "audioinput");
      select.replaceChildren(...mics.map((d, i) => {
        const opt = document.createElement("option");
        opt.value = d.deviceId || "default";
        opt.textContent = d.label || this.t("mic_n", { n: i + 1 });
        opt.selected = d.deviceId === current;
        return opt;
      }));
    }

    showGain(db) {
      const slider = $("voice-gain-slider");
      if (slider) slider.value = String(Math.round(db));
      this.setText("voice-gain-val", `${db > 0 ? "+" : ""}${Math.round(db)} dB`);
    }

    setGain(db) {
      if (!this.mic) return;
      const applied = window.SetupAudio.setGain(this.mic, db);
      window.SetupStorage.set("micGain", applied);
      this.showGain(applied);
    }

    render(m) {
      const pct = (db) => Math.max(0, Math.min(100, ((db - FLOOR_DB) / -FLOOR_DB) * 100));
      this.history.push(m);
      if (this.history.length > WINDOW) this.history.shift();
      this.peakHold = Math.max(m.peak, this.peakHold - 0.6);
      const fill = $("voice-vu-fill");
      const peak = $("voice-vu-peak");
      if (fill) {
        fill.style.width = `${pct(m.rms)}%`;
        fill.classList.toggle("is-hot", m.peak > -3);
      }
      if (peak) peak.style.left = `${pct(this.peakHold)}%`;
      this.setText("voice-vu-val", `${Math.max(FLOOR_DB, m.rms).toFixed(1)} dBFS · ${this.t("peak")} ${Math.max(FLOOR_DB, this.peakHold).toFixed(1)}`);
      const levels = this.history.map((h) => h.rms).sort((a, b) => a - b);
      const noise = levels[Math.floor(levels.length * 0.1)];
      const voice = levels[Math.min(levels.length - 1, Math.floor(levels.length * 0.95))];
      const clipped = this.history.reduce((n, h) => n + h.clipped, 0) / this.history.length;
      this.setText("voice-val-noise", `${noise.toFixed(1)} dBFS`);
      this.setText("voice-val-snr", `${Math.max(0, voice - noise).toFixed(1)} dB`);
      this.setText("voice-val-clip", `${(clipped * 100).toFixed(2)}%`);
      if (!this.calibrating) {
        const hint = clipped > 0.001 ? "hint_clip" : voice - noise > 12 && voice < TARGET_DB - 12 ? "hint_low" : "";
        this.setText("voice-hint", hint ? this.t(hint) : "");
      }
    }

    loop() {
      window.clearTimeout(this.timer);
      const tick = () => {
        if (!this.active() || !this.mic) {
          this.stop();
          return;
        }
        this.render(window.SetupAudio.meter(this.mic, this.buffer));
        this.timer = window.setTimeout(tick, 40);
      };
      tick();
    }

    async autoTune() {
      if (!this.mic || this.calibrating) return;
      this.calibrating = true;
      const btn = $("btn-voice-auto");
      if (btn) btn.disabled = true;
      try {
        const result = await window.SetupAudio.calibrate(this.mic, null, (phase) => {
          if (phase !== "done") this.setText("voice-hint", this.t(`calib_${phase}`));
        });
        window.SetupStorage.set("micGain", result.gain_db);
        this.showGain(result.gain_db);
        this.setText("voice-hint", this.t(result.snr_db < 10 ? "calib_noisy" : "calib_done",
          { gain: result.gain_db.toFixed(0), snr: result.snr_db.toFixed(1), voice: (result.voice_db + result.gain_db).toFixed(1) }));
        await this.save(result);
      } catch (err) {
        this.setText("voice-hint", this.t("calib_failed"));
      } finally {
        this.calibrating = false;
        if (btn) btn.disabled = false;
      }
    }

    async save(result) {
      const track = this.mic.stream.getAudioTracks()[0];
      const opts = this.options();
      const round = (v) => Math.round(v * 10) / 10;
      const mic = { noise_db: round(Math.max(-140, result.noise_db)), voice_db: round(Math.max(-140, result.voice_db)),
        snr_db: round(Math.max(-60, Math.min(140, result.snr_db))), sample_rate: result.sample_rate,
        device: ((track && track.label) || "").replace(/[^\p{L}\p{N} ()._:-]/gu, "").slice(0, 120), gain_db: result.gain_db,
        echo: opts.echo, noise: opts.noise };
      const res = await fetch("/api/setup/mic", { method: "POST", headers: HEADERS, body: JSON.stringify(mic) });
      if (!res.ok) throw new Error("mic-save");
    }

    stop() {
      window.clearTimeout(this.timer);
      this.timer = 0;
    }

    bind() {
      $("btn-req-voice-perm")?.addEventListener("click", () => this.openMic());
      $("btn-voice-auto")?.addEventListener("click", () => this.autoTune());
      $("voice-gain-slider")?.addEventListener("input", (e) => this.setGain(Number(e.target.value)));
      $("voice-mic-select")?.addEventListener("change", (e) => {
        window.SetupStorage.set("micDevice", e.target.value);
        this.openMic();
      });
      ["voice-opt-echo", "voice-opt-noise"].forEach((id) => $(id)?.addEventListener("change", (e) => {
        window.SetupStorage.set(id, e.target.checked);
        this.openMic();
      }));
    }

    async init() {
      if (!this.initialized) {
        this.initialized = true;
        this.bind();
      }
      this.applyTexts();
      const echo = $("voice-opt-echo");
      const noise = $("voice-opt-noise");
      if (echo) echo.checked = Boolean(window.SetupStorage.get("voice-opt-echo"));
      if (noise) noise.checked = Boolean(window.SetupStorage.get("voice-opt-noise"));
      let mode = "server";
      try {
        const res = await fetch("/api/setup/face/context", { headers: { "X-Nuxiva-Request": "1" }, cache: "no-store" });
        if (res.ok) mode = (await res.json()).mode === "remote" ? "remote" : "server";
      } catch (err) {
        mode = "server";
      }
      this.setText("voice-mode", this.t(mode === "server" ? "mode_server" : "mode_remote"));
      this.history = [];
      await this.openMic();
    }
  }

  window.SetupStepVoice = new StepVoice();
})();
