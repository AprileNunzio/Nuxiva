(() => {
  "use strict";

  const HEADERS = { "X-Nuxiva-Request": "1" };
  const SHOTS = 3;
  const TAKE_MS = 2400;
  const READY_MS = 600;
  const $ = (id) => document.getElementById(id);
  const sleep = (ms) => new Promise((resolve) => window.setTimeout(resolve, ms));

  class StepAssistant {
    constructor() {
      this.selectedGender = "female";
      this.takes = new Map();
      this.urls = new Map();
      this.busy = false;
      this.player = null;
      this.initialized = false;
    }

    t(key, vars) {
      const lang = window.SetupStorage.get("lang") || "it";
      const all = (window.SetupStepAssistantI18n && window.SetupStepAssistantI18n.dict) || {};
      const text = (all[lang] && all[lang][key]) || (all.it && all.it[key]) || "";
      return vars ? text.replace(/\{(\w+)\}/g, (_, k) => (k in vars ? String(vars[k]) : "")) : text;
    }

    name() {
      return (window.SetupStorage.get("assistantName") || "Nuxiva").trim();
    }

    setGender(gender) {
      this.selectedGender = gender;
      window.SetupStorage.set("assistantGender", gender);
      document.querySelectorAll(".os-card-voice").forEach((card) => {
        card.classList.toggle("is-selected", card.getAttribute("data-voice-gender") === gender);
      });
    }

    async playPreview(gender, btn) {
      const lang = encodeURIComponent(window.SetupStorage.get("lang") || "it");
      try {
        const res = await fetch(`/api/setup/preview/voice?lang=${lang}&gender=${encodeURIComponent(gender)}&t=${Date.now()}`, { headers: HEADERS });
        if (!res.ok) throw new Error(String(res.status));
        this.play(URL.createObjectURL(await res.blob()), true);
      } catch (err) {
        if (btn) btn.title = this.t("err_preview");
        btn?.classList.add("is-error");
      }
    }

    play(url, revoke) {
      if (this.player) this.player.pause();
      this.player = new Audio(url);
      if (revoke) this.player.addEventListener("ended", () => URL.revokeObjectURL(url), { once: true });
      this.player.play().catch(() => this.player && this.player.pause());
    }

    setStatus(index, text, tone) {
      const box = $(`wake-metrics-${index}`);
      if (!box) return;
      const line = document.createElement("span");
      line.className = `os-wake-status${tone ? ` is-${tone}` : ""}`;
      line.textContent = text;
      box.replaceChildren(line);
    }

    renderTake(index, take) {
      const box = $(`wake-metrics-${index}`);
      const shot = $(`wake-shot-box-${index}`);
      const rec = $(`btn-wake-rec-${index}`);
      const play = $(`btn-wake-play-${index}`);
      if (!box || !shot || !rec) return;
      const num = (v, digits = 1) => (Number.isFinite(Number(v)) ? Number(v).toFixed(digits) : "–");
      const rows = [
        ["m_score", Number.isFinite(Number(take.score)) ? `${Math.round(take.score)}/100` : null],
        ["m_speech", `${num(take.speech_db)} dBFS`],
        ["m_noise", `${num(take.noise_db)} dBFS`],
        ["m_snr", `${num(take.snr_db)} dB`],
        ["m_peak", `${num(take.peak_db)} dBFS`],
        ["m_clip", `${num(take.clipped_pct, 2)}%`],
        ["m_voiced", Number.isFinite(Number(take.voiced_seconds)) ? `${num(take.voiced_seconds, 2)} s` : null],
        ["m_lead", Number.isFinite(Number(take.lead_s)) ? `${num(take.lead_s, 2)} / ${num(take.tail_s, 2)} s` : null],
        ["m_gain", Number.isFinite(Number(take.gain_db)) ? `${take.gain_db > 0 ? "+" : ""}${num(take.gain_db)} dB` : null],
        ["m_engine", take.engine ? String(take.engine) : null],
      ].filter(([, value]) => value !== null);
      const grid = document.createElement("dl");
      grid.className = "os-wake-grid";
      rows.forEach(([key, value]) => {
        const dt = document.createElement("dt");
        const dd = document.createElement("dd");
        dt.textContent = this.t(key);
        dd.textContent = value;
        grid.append(dt, dd);
      });
      const reasons = Array.isArray(take.reasons) ? take.reasons.filter((r) => typeof r === "string") : [];
      const verdict = document.createElement("span");
      verdict.className = `os-wake-status is-${take.usable ? "ok" : "error"}`;
      verdict.textContent = take.usable && !reasons.length ? this.t("ok_take")
        : reasons.map((r) => this.t(`reason_${r}`) || r).join(" · ") || this.t("ok_take");
      box.replaceChildren(verdict, grid);
      shot.classList.remove("is-recording");
      shot.classList.toggle("is-done", Boolean(take.usable));
      shot.classList.toggle("is-bad", !take.usable);
      rec.textContent = this.t("btn_redo");
      rec.disabled = false;
      if (play) {
        play.hidden = !this.urls.has(index);
        play.textContent = this.t("btn_play");
      }
    }

    async saveName() {
      const res = await fetch("/api/setup/assistant", {
        method: "POST",
        headers: { ...HEADERS, "Content-Type": "application/json" },
        body: JSON.stringify({ name: this.name() }),
      });
      if (!res.ok) throw new Error("name");
    }

    async micFor() {
      const opts = {
        deviceId: window.SetupStorage.get("micDevice") || "",
        echo: Boolean(window.SetupStorage.get("voice-opt-echo")),
        noise: Boolean(window.SetupStorage.get("voice-opt-noise")),
      };
      const mic = await window.SetupAudio.open(opts);
      window.SetupAudio.setGain(mic, Number(window.SetupStorage.get("micGain") || 0));
      return mic;
    }

    async detail(res) {
      try {
        const body = await res.json();
        return typeof body.detail === "string" ? body.detail.slice(0, 160) : String(res.status);
      } catch (err) {
        return String(res.status);
      }
    }

    async recordWakeShot(index) {
      if (this.busy) return;
      const shot = $(`wake-shot-box-${index}`);
      const rec = $(`btn-wake-rec-${index}`);
      if (!shot || !rec) return;
      this.busy = true;
      rec.disabled = true;
      rec.textContent = this.t("btn_recording");
      shot.classList.remove("is-done", "is-bad");
      try {
        try {
          await this.saveName();
        } catch (err) {
          this.setStatus(index, this.t("err_name"), "error");
          return;
        }
        let mic;
        try {
          mic = await this.micFor();
        } catch (err) {
          this.setStatus(index, this.t("err_mic"), "error");
          return;
        }
        this.setStatus(index, this.t("get_ready"));
        await sleep(READY_MS);
        shot.classList.add("is-recording");
        this.setStatus(index, this.t("speak_now", { name: this.name() }), "live");
        const blob = await window.SetupAudio.record(mic, TAKE_MS);
        shot.classList.remove("is-recording");
        this.setStatus(index, this.t("checking"));
        const res = await fetch(`/api/setup/wake-sample?index=${index}`, {
          method: "POST",
          headers: { ...HEADERS, "Content-Type": "audio/wav" },
          body: blob,
        });
        if (!res.ok) {
          this.setStatus(index, this.t("err_upload", { msg: await this.detail(res) }), "error");
          return;
        }
        const take = await res.json();
        if (this.urls.has(index)) URL.revokeObjectURL(this.urls.get(index));
        this.urls.set(index, URL.createObjectURL(blob));
        this.takes.set(index, take);
        window.SetupStorage.set("wakeShotsCompleted", [...this.takes.values()].filter((t) => t.usable).length);
        this.renderTake(index, take);
      } catch (err) {
        this.setStatus(index, this.t("err_upload", { msg: err && err.message ? err.message : "?" }), "error");
      } finally {
        this.busy = false;
        shot.classList.remove("is-recording");
        rec.disabled = false;
        if (!this.takes.has(index)) rec.textContent = this.t("btn_record");
      }
    }

    async loadTakes() {
      try {
        const res = await fetch(`/api/setup/session?t=${Date.now()}`, { headers: HEADERS, cache: "no-store" });
        if (!res.ok) return;
        const samples = ((await res.json()).config || {}).wake_samples || {};
        Object.entries(samples).forEach(([key, take]) => {
          const index = Number(key);
          if (Number.isInteger(index) && index >= 1 && index <= SHOTS && take && typeof take === "object") {
            this.takes.set(index, take);
            this.renderTake(index, take);
          }
        });
      } catch (err) {
        this.takes.clear();
      }
    }

    applyTexts() {
      document.querySelectorAll("#screen-assistant [data-wake-label]").forEach((el) => {
        el.textContent = this.t("shot_n", { n: el.dataset.wakeLabel });
      });
      for (let i = 1; i <= SHOTS; i++) {
        const rec = $(`btn-wake-rec-${i}`);
        const play = $(`btn-wake-play-${i}`);
        if (rec && !this.busy) rec.textContent = this.t(this.takes.has(i) ? "btn_redo" : "btn_record");
        if (play) play.textContent = this.t("btn_play");
      }
      const span = $("wake-assistant-name");
      if (span) span.textContent = this.name();
    }

    bind() {
      const input = $("assistant-name-input");
      if (input) {
        input.addEventListener("input", (e) => {
          window.SetupStorage.set("assistantName", e.target.value.trim() || "Nuxiva");
          const span = $("wake-assistant-name");
          if (span) span.textContent = this.name();
        });
      }
      document.querySelectorAll(".os-card-voice").forEach((card) => {
        card.addEventListener("click", (e) => {
          if (e.target.closest(".os-btn-voice-preview")) return;
          const g = card.getAttribute("data-voice-gender");
          if (g) this.setGender(g);
        });
      });
      document.querySelectorAll(".os-btn-voice-preview").forEach((btn) => {
        btn.addEventListener("click", (e) => {
          e.stopPropagation();
          const g = btn.getAttribute("data-preview-gender");
          if (g) this.playPreview(g, btn);
        });
      });
      for (let i = 1; i <= SHOTS; i++) {
        $(`btn-wake-rec-${i}`)?.addEventListener("click", () => this.recordWakeShot(i));
        $(`btn-wake-play-${i}`)?.addEventListener("click", () => {
          if (this.urls.has(i)) this.play(this.urls.get(i), false);
        });
      }
    }

    async init() {
      if (!this.initialized) {
        this.initialized = true;
        this.bind();
      }
      const input = $("assistant-name-input");
      if (input) input.value = this.name();
      this.setGender(window.SetupStorage.get("assistantGender") || "female");
      this.applyTexts();
      await this.loadTakes();
    }
  }

  window.SetupStepAssistant = new StepAssistant();
})();
